"""
Inspection Database Repository (ADR-0007, ADR-0009, ADR-0013).

Manages CRUD and atomic state transitions on `app.inspection`:
- Idempotency key lookup (409 conflict vs replay return).
- Enqueuing in QUEUED status.
- Stage checkpoints.
- Terminal persistence (COMPLETE / FAILED).
- Querying for history and polling fallback.
- Startup reaping of stale worker leases.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import asyncpg


async def find_by_idempotency_key(
    conn: Optional[asyncpg.Connection],
    idempotency_key: str,
) -> Optional[Dict[str, Any]]:
    """Checks if an inspection with this idempotency key already exists."""
    if conn is None:
        return None
    row = await conn.fetchrow(
        """
        SELECT id, status, request_hash, overall, overall_ui_bucket, created_at
        FROM app.inspection
        WHERE idempotency_key = $1;
        """,
        idempotency_key,
    )
    return dict(row) if row else None


async def create_queued_inspection(
    conn: Optional[asyncpg.Connection],
    inspection_id: str,
    context_dict: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    request_hash: Optional[str] = None,
    lease_timeout: Optional[datetime] = None,
) -> None:
    """Inserts a new inspection in QUEUED status."""
    if conn is None:
        return
    await conn.execute(
        """
        INSERT INTO app.inspection (
            id, status, context, idempotency_key, request_hash, lease_timeout, created_at
        )
        VALUES ($1, 'QUEUED', $2::jsonb, $3, $4, $5, now());
        """,
        inspection_id,
        json.dumps(context_dict, default=str),
        idempotency_key,
        request_hash,
        lease_timeout,
    )


async def update_stage_checkpoint(
    conn: Optional[asyncpg.Connection],
    inspection_id: str,
    status: str,
    lease_timeout: Optional[datetime] = None,
) -> None:
    """Asynchronously logs stage checkpoint to Postgres."""
    if conn is None:
        return
    await conn.execute(
        """
        UPDATE app.inspection
        SET status = $2, lease_timeout = $3
        WHERE id = $1;
        """,
        inspection_id,
        status,
        lease_timeout,
    )


async def save_terminal_success(
    conn: Optional[asyncpg.Connection],
    inspection_id: str,
    overall: str,
    overall_ui_bucket: str,
    summary_dict: Dict[str, Any],
    ocr_doc_dict: Optional[Dict[str, Any]],
    declaration_set_dict: Optional[Dict[str, Any]],
    engine_dict: Dict[str, Any],
    completed_at: datetime,
) -> None:
    """Updates inspection to COMPLETE with full analytical artifacts."""
    if conn is None:
        return
    await conn.execute(
        """
        UPDATE app.inspection
        SET status = 'COMPLETE',
            overall = $2,
            overall_ui_bucket = $3,
            summary = $4::jsonb,
            ocr_document = $5::jsonb,
            declaration_set = $6::jsonb,
            engine = $7::jsonb,
            completed_at = $8,
            lease_timeout = NULL
        WHERE id = $1;
        """,
        inspection_id,
        overall,
        overall_ui_bucket,
        json.dumps(summary_dict, default=str),
        json.dumps(ocr_doc_dict, default=str) if ocr_doc_dict else None,
        json.dumps(declaration_set_dict, default=str) if declaration_set_dict else None,
        json.dumps(engine_dict, default=str),
        completed_at,
    )


async def save_terminal_failure(
    conn: Optional[asyncpg.Connection],
    inspection_id: str,
    error_code: str,
    error_message: str,
    completed_at: datetime,
) -> None:
    """Updates inspection to FAILED status with failure diagnostics."""
    if conn is None:
        return
    await conn.execute(
        """
        UPDATE app.inspection
        SET status = 'FAILED',
            error_code = $2,
            error_message = $3,
            completed_at = $4,
            lease_timeout = NULL
        WHERE id = $1;
        """,
        inspection_id,
        error_code,
        error_message,
        completed_at,
    )


async def get_inspection_by_id(
    conn: Optional[asyncpg.Connection],
    inspection_id: str,
) -> Optional[Dict[str, Any]]:
    """Fetches complete inspection record from Postgres."""
    if conn is None:
        return None
    row = await conn.fetchrow(
        """
        SELECT id, status, overall, overall_ui_bucket, summary, context,
               ocr_document, declaration_set, engine, error_code, error_message,
               created_at, completed_at
        FROM app.inspection
        WHERE id = $1;
        """,
        inspection_id,
    )
    if not row:
        return None

    res = dict(row)
    # Parse JSON fields if returned as string
    for json_col in ["summary", "context", "ocr_document", "declaration_set", "engine"]:
        if isinstance(res.get(json_col), str):
            res[json_col] = json.loads(res[json_col])
    return res


async def list_inspections(
    conn: Optional[asyncpg.Connection],
    limit: int = 20,
    cursor_created_at: Optional[datetime] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Cursor-paginated inspection history query."""
    if conn is None:
        return []

    conditions = []
    params = []
    idx = 1

    if cursor_created_at is not None:
        conditions.append(f"created_at < ${idx}")
        params.append(cursor_created_at)
        idx += 1

    if status_filter:
        conditions.append(f"status = ${idx}")
        params.append(status_filter)
        idx += 1

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT id, status, overall, overall_ui_bucket, summary, context,
               created_at, completed_at
        FROM app.inspection
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${idx};
    """
    params.append(limit)

    rows = await conn.fetch(query, *params)
    results = []
    for r in rows:
        item = dict(r)
        for json_col in ["summary", "context"]:
            if isinstance(item.get(json_col), str):
                item[json_col] = json.loads(item[json_col])
        results.append(item)
    return results


async def reap_stale_inspections(
    conn: Optional[asyncpg.Connection],
    now: Optional[datetime] = None,
) -> List[str]:
    """
    Finds non-terminal inspections that exceeded worker lease timeout
    and marks them FAILED with WORKER_INTERRUPTED (ADR-0007).
    """
    if conn is None:
        return []
    current_time = now or datetime.now(timezone.utc)
    rows = await conn.fetch(
        """
        UPDATE app.inspection
        SET status = 'FAILED',
            error_code = 'WORKER_INTERRUPTED',
            error_message = 'Worker process lease timed out before completion.',
            completed_at = $1,
            lease_timeout = NULL
        WHERE status NOT IN ('COMPLETE', 'FAILED')
          AND lease_timeout IS NOT NULL
          AND lease_timeout < $1
        RETURNING id;
        """,
        current_time,
    )
    return [r["id"] for r in rows]
