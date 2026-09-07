"""
Inspection Rule Results Repository (ADR-0008, ADR-0013).

Stores immutable evaluation snapshots in `app.inspection_rule_result`.
Each result preserves the evaluated citation, observed/expected text,
evidence spans, and confidence scores as JSONB.
"""

import json
from typing import Any, Dict, List, Optional
import asyncpg
from app.db.seed_rules import get_version_id_for_rule


async def save_rule_results(
    conn: Optional[asyncpg.Connection],
    inspection_id: str,
    rule_results: List[Any],
) -> None:
    """
    Persists evaluated RuleResult models into app.inspection_rule_result.
    Satisfies foreign keys on app.rule and app.rule_version.
    """
    if conn is None or not rule_results:
        return

    records = []
    for res in rule_results:
        # Resolve rule_version_id
        version_id = get_version_id_for_rule(res.rule_id)
        verdict_val = res.verdict.value if hasattr(res.verdict, "value") else str(res.verdict)
        ui_bucket_val = res.ui_bucket.value if hasattr(res.ui_bucket, "value") else str(res.ui_bucket)

        evidence_json = json.dumps([e.model_dump() if hasattr(e, "model_dump") else e for e in res.evidence], default=str)
        confidence_json = json.dumps(res.confidence.model_dump() if hasattr(res.confidence, "model_dump") else res.confidence, default=str)
        applicability_json = json.dumps(res.applicability.model_dump() if hasattr(res.applicability, "model_dump") else res.applicability, default=str)
        citation_json = json.dumps(res.citation.model_dump() if hasattr(res.citation, "model_dump") else res.citation, default=str)

        records.append((
            inspection_id,
            res.rule_id,
            version_id,
            verdict_val,
            ui_bucket_val,
            res.reason_code,
            res.message,
            res.observed,
            res.expected,
            evidence_json,
            confidence_json,
            applicability_json,
            citation_json,
        ))

    await conn.executemany(
        """
        INSERT INTO app.inspection_rule_result (
            inspection_id, rule_id, rule_version_id, verdict, ui_bucket,
            reason_code, message, observed, expected, evidence,
            confidence, applicability, citation_snapshot
        )
        VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10::jsonb,
            $11::jsonb, $12::jsonb, $13::jsonb
        );
        """,
        records,
    )


async def get_results_by_inspection_id(
    conn: Optional[asyncpg.Connection],
    inspection_id: str,
) -> List[Dict[str, Any]]:
    """Fetches all immutable rule result rows for an inspection."""
    if conn is None:
        return []
    rows = await conn.fetch(
        """
        SELECT id, rule_id, rule_version_id, verdict, ui_bucket,
               reason_code, message, observed, expected, evidence,
               confidence, applicability, citation_snapshot, created_at
        FROM app.inspection_rule_result
        WHERE inspection_id = $1
        ORDER BY id ASC;
        """,
        inspection_id,
    )
    results = []
    for r in rows:
        item = dict(r)
        for json_col in ["evidence", "confidence", "applicability", "citation_snapshot"]:
            if isinstance(item.get(json_col), str):
                item[json_col] = json.loads(item[json_col])
        results.append(item)
    return results
