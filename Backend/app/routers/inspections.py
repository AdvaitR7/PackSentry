"""
Inspection API Router (ADR-0007, ADR-0009, ADR-0013, ADR-0015).

Implements:
- POST /v1/inspections: multipart upload (context JSON + PDP, BACK, optional SIDE), content sniffing,
  idempotency, scratch-disk staging, and 202 Accepted return with Location header.
- GET /v1/inspections/{id}: ultra-fast (<1ms) in-flight polling from in-memory registry,
  terminal recovery from Supabase Postgres with signed evidence URLs.
- GET /v1/inspections: cursor-paginated inspection history.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from lmpc_schema import (
    CaptureContext,
    Citation,
    EngineMetadata,
    ExcludedRuleEntry,
    InspectionImageInfo,
    InspectionResponse,
    InspectionStatus,
    InternalVerdict,
    PanelRole,
    ProductContext,
    RuleResult,
    SummaryCounts,
    UiBucket,
)

from app.db.repositories import image_repo, inspection_repo, rule_result_repo
from app.db.scratch import cleanup_scratch_dir, get_scratch_dir, stream_upload_to_scratch
from app.db.session import acquire_connection
from app.db.storage import is_configured as is_storage_configured, mint_signed_url

logger = logging.getLogger("packsentry.api.inspections")

router = APIRouter(prefix="/inspections", tags=["Inspections"])


def _compute_request_hash(context_str: str, images_sha: List[str]) -> str:
    """Computes a deterministic hash of context and image digests for idempotency."""
    h = hashlib.sha256(context_str.strip().encode("utf-8"))
    for s in sorted(images_sha):
        h.update(s.encode("utf-8"))
    return h.hexdigest()


@router.post("", status_code=202)
async def create_inspection(
    request: Request,
    response: Response,
    context: str = Form(..., description="Serialized CaptureContext JSON"),
    pdp: UploadFile = File(..., alias="PDP", description="Required Principal Display Panel image"),
    back: UploadFile = File(..., alias="BACK", description="Required Back Panel image"),
    side: Optional[UploadFile] = File(None, alias="SIDE", description="Optional Side Panel image"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Initiates a new statutory package compliance inspection.
    Validates context schema, validates image content via decoding,
    streams to local scratch disk, and returns 202 Accepted immediately.
    """
    # 1. Validate Context JSON
    try:
        context_dict = json.loads(context)
        capture_ctx = CaptureContext.model_validate(context_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid 'context' JSON payload: {exc}",
        )

    # 2. Stage files to Scratch Disk and compute in-flight hashes
    temp_id = f"insp_{uuid4().hex[:12]}"
    scratch_dir = get_scratch_dir(temp_id)

    try:
        # Stream PDP
        pdp_path = scratch_dir / "pdp_original.jpg"
        pdp_sha, pdp_w, pdp_h = await stream_upload_to_scratch(pdp, pdp_path)

        # Stream BACK
        back_path = scratch_dir / "back_original.jpg"
        back_sha, back_w, back_h = await stream_upload_to_scratch(back, back_path)

        # Stream SIDE if provided
        side_sha, side_w, side_h = (None, None, None)
        if side is not None:
            side_path = scratch_dir / "side_original.jpg"
            side_sha, side_w, side_h = await stream_upload_to_scratch(side, side_path)

    except HTTPException:
        cleanup_scratch_dir(temp_id)
        raise
    except Exception as exc:
        cleanup_scratch_dir(temp_id)
        raise HTTPException(status_code=422, detail=f"Failed to process image uploads: {exc}")

    # 3. Check Idempotency
    all_shas = [pdp_sha, back_sha] + ([side_sha] if side_sha else [])
    req_hash = _compute_request_hash(context, all_shas)

    async with acquire_connection() as conn:
        if conn and idempotency_key:
            existing = await inspection_repo.find_by_idempotency_key(conn, idempotency_key)
            if existing:
                cleanup_scratch_dir(temp_id)
                if existing.get("request_hash") == req_hash:
                    existing_id = existing["id"]
                    response.headers["Location"] = f"/v1/inspections/{existing_id}"
                    return {
                        "inspection_id": existing_id,
                        "status": existing["status"],
                        "replayed": True,
                    }
                else:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Idempotency-Key '{idempotency_key}' was already used with a different request payload.",
                    )

    # 4. Save Context and Manifest to scratch directory for the worker
    manifest = {
        PanelRole.PDP.value: {
            "filename": "pdp_original.jpg",
            "image_id": f"img_{uuid4().hex[:8]}",
            "sha256": pdp_sha,
            "width": pdp_w,
            "height": pdp_h,
        },
        PanelRole.BACK.value: {
            "filename": "back_original.jpg",
            "image_id": f"img_{uuid4().hex[:8]}",
            "sha256": back_sha,
            "width": back_w,
            "height": back_h,
        },
    }
    if side is not None:
        manifest[PanelRole.SIDE.value] = {
            "filename": "side_original.jpg",
            "image_id": f"img_{uuid4().hex[:8]}",
            "sha256": side_sha,
            "width": side_w,
            "height": side_h,
        }

    with open(scratch_dir / "context.json", "w", encoding="utf-8") as f:
        json.dump(capture_ctx.model_dump(), f, default=str)
    with open(scratch_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    # 5. Insert initial record in Postgres
    async with acquire_connection() as conn:
        await inspection_repo.create_queued_inspection(
            conn=conn,
            inspection_id=temp_id,
            context_dict=capture_ctx.model_dump(),
            idempotency_key=idempotency_key,
            request_hash=req_hash,
        )

    # 6. Enqueue job in single-capacity background worker
    worker = getattr(request.app.state, "worker", None)
    if worker:
        await worker.enqueue(temp_id)
    else:
        logger.warning("Worker not attached to app state. Job %s enqueued only in DB.", temp_id)

    # 7. Return 202 Accepted with Location header
    response.headers["Location"] = f"/v1/inspections/{temp_id}"
    return {
        "inspection_id": temp_id,
        "status": "QUEUED",
    }


@router.get("/{inspection_id}")
async def get_inspection(inspection_id: str, request: Request):
    """
    Polls inspection state with sub-millisecond in-flight latency from memory,
    recovering complete immutable response from Postgres upon completion.
    """
    worker = getattr(request.app.state, "worker", None)

    # 1. Fast path: check in-memory registry (<1ms)
    if worker:
        job = worker.registry.get(inspection_id)
        if job:
            if job.status == InspectionStatus.COMPLETE and job.result:
                return job.result
            elif job.status == InspectionStatus.FAILED:
                return {
                    "inspection_id": inspection_id,
                    "status": "FAILED",
                    "error_code": job.error_code or "PIPELINE_ERROR",
                    "error_message": job.error_message or "Inspection processing failed.",
                }
            else:
                # In-flight status response
                return {
                    "inspection_id": inspection_id,
                    "status": job.status.value,
                    "stage_message": job.stage_message,
                }

    # 2. Database path (for finished jobs or past sessions)
    async with acquire_connection() as conn:
        row = await inspection_repo.get_inspection_by_id(conn, inspection_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Inspection '{inspection_id}' not found.")

        status_val = row.get("status")
        if status_val != "COMPLETE":
            return {
                "inspection_id": inspection_id,
                "status": status_val,
                "error_code": row.get("error_code"),
                "error_message": row.get("error_message"),
            }

        # Reconstruct InspectionResponse from Postgres tables
        images_data = await image_repo.get_images_for_inspection(conn, inspection_id)
        image_infos = []
        for img in images_data:
            orig_url = f"/v1/inspections/{inspection_id}/images/{img['role'].lower()}/original"
            if is_storage_configured():
                signed = mint_signed_url(img["storage_path"], expires_in_seconds=120)
                if signed:
                    orig_url = signed
            image_infos.append(
                InspectionImageInfo(
                    image_id=img["id"],
                    role=PanelRole(img["role"]),
                    original_url=orig_url,
                    original_width=img["width"],
                    original_height=img["height"],
                )
            )

        rule_results_data = await rule_result_repo.get_results_by_inspection_id(conn, inspection_id)
        rule_results = []
        for r in rule_results_data:
            rule_results.append(
                RuleResult(
                    rule_id=r["rule_id"],
                    provision=r["citation_snapshot"].get("provision", ""),
                    title=r["message"],
                    verdict=InternalVerdict(r["verdict"]),
                    ui_bucket=UiBucket(r["ui_bucket"]),
                    reason_code=r["reason_code"],
                    message=r["message"],
                    observed=r["observed"],
                    expected=r["expected"],
                    evidence=r["evidence"],
                    confidence=r["confidence"],
                    applicability=r["applicability"],
                    citation=Citation.model_validate(r["citation_snapshot"]),
                )
            )

        context_data = row.get("context", {})
        prod_ctx = ProductContext.model_validate(context_data)
        summary_data = row.get("summary", {})
        summary = SummaryCounts.model_validate(summary_data)
        engine_data = row.get("engine", {})
        engine_meta = EngineMetadata.model_validate(engine_data)

        return InspectionResponse(
            inspection_id=inspection_id,
            status=InspectionStatus.COMPLETE,
            created_at=row["created_at"],
            completed_at=row.get("completed_at"),
            overall=InternalVerdict(row["overall"]) if row.get("overall") else InternalVerdict.INDETERMINATE,
            overall_ui_bucket=UiBucket(row["overall_ui_bucket"]) if row.get("overall_ui_bucket") else UiBucket.MANUAL_REVIEW,
            summary=summary,
            context=prod_ctx,
            images=image_infos,
            declarations=[],
            rule_results=rule_results,
            configured_rule_ids=[r.rule_id for r in rule_results],
            evaluated_rule_ids=[r.rule_id for r in rule_results if r.applicability.status.value == "APPLICABLE"],
            excluded_rule_ids=[
                ExcludedRuleEntry(rule_id=r.rule_id, reason_code=r.applicability.reason_code or "NOT_APPLICABLE")
                for r in rule_results
                if r.applicability.status.value == "NOT_APPLICABLE"
            ],
            engine=engine_meta,
        )


@router.get("")
async def list_inspections(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[datetime] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    """Cursor-paginated inspection history."""
    async with acquire_connection() as conn:
        return await inspection_repo.list_inspections(
            conn=conn,
            limit=limit,
            cursor_created_at=cursor,
            status_filter=status,
        )
