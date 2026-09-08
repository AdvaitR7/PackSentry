"""
Single-Capacity Background Pipeline Worker (ADR-0007, ADR-0009, ADR-0013).

Orchestrates the 8-stage Legal Metrology inspection pipeline:
1. QUEUED: Job enqueued, stored in scratch disk and Postgres.
2. PREPROCESSING: EXIF orientation, 1600px longest-edge resize, transform matrix.
3. OCR: Cloud Vision primary with bounded timeout & automatic PaddleOCR fallback.
4. EXTRACTING: Normalisation, alias matching, D1-D6 deterministic parsers.
5. VLM INTERPRETATION (Selective D7): Pre-warmed Qwen2.5-VL for unlocated fields under LOW_CONFIDENCE taint cap.
6. EVALUATING: 23 statutory rules evaluation with absence & provenance gates.
7. PERSISTING: Private Supabase Storage upload, signed URL minting, Postgres snapshot write, scratch purge.
8. COMPLETE: Final immutable InspectionResponse rendered.

Guarantees:
- Single-capacity (capacity=1) execution protects GPU/VRAM from concurrent inference collisions.
- In-memory registry provides <5ms polling latency for GET /v1/inspections/{id}.
- Reaps stale worker leases on process startup with WORKER_INTERRUPTED.
"""

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from lmpc_schema import (
    CaptureContext,
    EngineMetadata,
    ExcludedRuleEntry,
    Field,
    ImageSlot,
    InspectionImageInfo,
    InspectionResponse,
    InspectionStatus,
    OcrDocument,
    PanelRole,
    ProductContext,
)

from app.db.repositories import image_repo, inspection_repo, rule_result_repo
from app.db.scratch import cleanup_scratch_dir, get_scratch_dir
from app.db.session import acquire_connection
from app.db.storage import is_configured as is_storage_configured, mint_signed_url, upload_evidence
from app.extraction.pipeline import extract_declarations
from app.normalise import build_normalised_document
from app.ocr.router import OcrRouter
from app.ocr.vlm_interpreter import QwenVlmInterpreter
from app.preprocessing import ImagePreprocessor
from app.rules import evaluate_inspection

logger = logging.getLogger("packsentry.worker")


@dataclass
class JobState:
    inspection_id: str
    status: InspectionStatus
    stage_message: str
    created_at: datetime
    updated_at: datetime
    result: Optional[InspectionResponse] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class InFlightJobRegistry:
    """In-memory thread-safe state registry for <5ms polling latency."""

    def __init__(self):
        self._jobs: Dict[str, JobState] = {}
        self._lock = asyncio.Lock()

    async def register(self, inspection_id: str, status: InspectionStatus = InspectionStatus.QUEUED) -> None:
        async with self._lock:
            now = datetime.now(timezone.utc)
            self._jobs[inspection_id] = JobState(
                inspection_id=inspection_id,
                status=status,
                stage_message="Job queued for processing",
                created_at=now,
                updated_at=now,
            )

    async def update_stage(self, inspection_id: str, status: InspectionStatus, message: str) -> None:
        async with self._lock:
            if inspection_id in self._jobs:
                job = self._jobs[inspection_id]
                job.status = status
                job.stage_message = message
                job.updated_at = datetime.now(timezone.utc)

    async def set_complete(self, inspection_id: str, result: InspectionResponse) -> None:
        async with self._lock:
            if inspection_id in self._jobs:
                job = self._jobs[inspection_id]
                job.status = InspectionStatus.COMPLETE
                job.stage_message = "Inspection completed successfully"
                job.result = result
                job.updated_at = datetime.now(timezone.utc)

    async def set_failed(self, inspection_id: str, error_code: str, error_message: str) -> None:
        async with self._lock:
            if inspection_id in self._jobs:
                job = self._jobs[inspection_id]
                job.status = InspectionStatus.FAILED
                job.stage_message = error_message
                job.error_code = error_code
                job.error_message = error_message
                job.updated_at = datetime.now(timezone.utc)

    def get(self, inspection_id: str) -> Optional[JobState]:
        """Synchronous read for ultra-low-latency (<1ms) API handlers."""
        return self._jobs.get(inspection_id)

    def snapshot(self) -> List[JobState]:
        """Returns a snapshot of in-memory jobs for offline history listing."""
        return list(self._jobs.values())


class InspectionWorker:
    """Bounded single-capacity background execution worker."""

    def __init__(
        self,
        ocr_router: Optional[OcrRouter] = None,
        vlm_interpreter: Optional[QwenVlmInterpreter] = None,
    ):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.registry = InFlightJobRegistry()
        self.ocr_router = ocr_router or OcrRouter()
        self.vlm_interpreter = vlm_interpreter or QwenVlmInterpreter()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Starts the worker event loop and reaps stale leases."""
        if self._running:
            return
        self._running = True

        # 1. Startup reaping: mark timed-out leases FAILED with WORKER_INTERRUPTED
        try:
            async with acquire_connection() as conn:
                reaped = await inspection_repo.reap_stale_inspections(conn)
                if reaped:
                    logger.warning("Reaped %d interrupted inspections on startup: %s", len(reaped), reaped)
        except Exception as exc:
            logger.warning("Failed to reap stale inspections on startup: %s", exc)

        # 2. Start worker consumer task
        self._task = asyncio.create_task(self._run_loop())
        logger.info("PackSentry background worker started (capacity=1).")

    async def stop(self) -> None:
        """Stops the worker gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("PackSentry background worker stopped.")

    async def enqueue(self, inspection_id: str) -> None:
        """Registers and queues an inspection ID for processing."""
        await self.registry.register(inspection_id, InspectionStatus.QUEUED)
        await self.queue.put(inspection_id)
        logger.debug("Enqueued inspection %s (queue size: %d)", inspection_id, self.queue.qsize())

    async def _run_loop(self) -> None:
        """Sequential single-job consumer loop."""
        while self._running:
            try:
                inspection_id = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                await self._execute_pipeline(inspection_id)
            except Exception as exc:
                logger.error("Unhandled pipeline error on inspection %s: %s", inspection_id, exc, exc_info=True)
                await self.registry.set_failed(inspection_id, "INTERNAL_PIPELINE_ERROR", str(exc))
                try:
                    async with acquire_connection() as conn:
                        await inspection_repo.save_terminal_failure(
                            conn=conn,
                            inspection_id=inspection_id,
                            error_code="INTERNAL_PIPELINE_ERROR",
                            error_message=str(exc),
                            completed_at=datetime.now(timezone.utc),
                        )
                except Exception as db_exc:
                    logger.error("Failed to write failure checkpoint for %s: %s", inspection_id, db_exc)
            finally:
                if is_storage_configured():
                    cleanup_scratch_dir(inspection_id)
                self.queue.task_done()

    async def _advance_stage(self, inspection_id: str, status: InspectionStatus, message: str) -> None:
        """Publishes a stage transition to the in-memory registry and the DB checkpoint."""
        await self.registry.update_stage(inspection_id, status, message)
        async with acquire_connection() as conn:
            await inspection_repo.update_stage_checkpoint(conn, inspection_id, status.value)

    async def _execute_pipeline(self, inspection_id: str) -> None:
        """Executes the complete end-to-end statutory inspection pipeline."""
        scratch_dir = get_scratch_dir(inspection_id)
        context_path = scratch_dir / "context.json"
        manifest_path = scratch_dir / "manifest.json"

        if not context_path.exists() or not manifest_path.exists():
            raise FileNotFoundError(f"Missing context or manifest in scratch directory for {inspection_id}")

        with open(context_path, "r", encoding="utf-8") as f:
            context_data = json.load(f)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        capture_ctx = CaptureContext.model_validate(context_data)

        # ---------------------------------------------------------------------
        # Stage 1: PREPROCESSING (EXIF, 1600px resize, Transform calculation)
        # ---------------------------------------------------------------------
        await self._advance_stage(inspection_id, InspectionStatus.PREPROCESSING, "Normalizing EXIF orientation and scaling images")

        preprocessed_panels: Dict[PanelRole, Dict[str, Any]] = {}
        for role_str, file_info in manifest.items():
            role = PanelRole(role_str)
            raw_path = scratch_dir / file_info["filename"]
            with open(raw_path, "rb") as f_in:
                raw_bytes = f_in.read()

            processed = ImagePreprocessor.preprocess_panel(raw_bytes, max_edge=1600)
            if processed is None:
                raise ValueError(f"Failed to preprocess panel {role.value}")

            analysis_bytes = processed.analysis_bytes
            orig_w = processed.original_width
            orig_h = processed.original_height
            ana_w = processed.analysis_width
            ana_h = processed.analysis_height
            transform = processed.transform

            # Save analysis image to scratch
            analysis_filename = f"{role.value.lower()}_analysis.jpg"
            analysis_path = scratch_dir / analysis_filename
            with open(analysis_path, "wb") as f_out:
                f_out.write(analysis_bytes)

            preprocessed_panels[role] = {
                "image_id": file_info["image_id"],
                "raw_bytes": raw_bytes,
                "analysis_bytes": analysis_bytes,
                "orig_w": orig_w,
                "orig_h": orig_h,
                "ana_w": ana_w,
                "ana_h": ana_h,
                "transform": transform,
                "original_filename": file_info["filename"],
                "analysis_filename": analysis_filename,
                "sha256": file_info["sha256"],
            }

        # ---------------------------------------------------------------------
        # Stage 2: OCR (Cloud Vision primary -> automatic PaddleOCR fallback)
        # ---------------------------------------------------------------------
        await self._advance_stage(inspection_id, InspectionStatus.OCR, "Detecting package text and calculating coordinate mappings")

        image_slots: List[ImageSlot] = []
        engines_used: List[str] = []

        for role, panel in preprocessed_panels.items():
            slot, engine_used = await self.ocr_router.recognize_panel(
                analysis_bytes=panel["analysis_bytes"],
                role=role,
                image_id=panel["image_id"],
                analysis_width=panel["ana_w"],
                analysis_height=panel["ana_h"],
                original_width=panel["orig_w"],
                original_height=panel["orig_h"],
                transform=panel["transform"],
            )
            image_slots.append(slot)
            engines_used.append(engine_used)

        primary_ocr_engine = engines_used[0] if engines_used else "google_cloud_vision"
        ocr_doc = OcrDocument(
            ocr_engine=primary_ocr_engine,
            ocr_version="v1",
            images=image_slots,
        )

        # ---------------------------------------------------------------------
        # Stage 3: EXTRACTING (Normalisation + Deterministic Parsers D1-D6)
        # ---------------------------------------------------------------------
        await self._advance_stage(inspection_id, InspectionStatus.EXTRACTING, "Extracting statutory declarations and validating SI units")

        norm_doc = build_normalised_document(ocr_doc)
        declaration_set = extract_declarations(norm_doc, ocr_doc, capture_ctx)

        # Selective VLM Fallback (D7) for critical missing declarations
        critical_fields = [Field.NET_QUANTITY, Field.RETAIL_SALE_PRICE]
        if await self.vlm_interpreter.is_reachable():
            for crit_field in critical_fields:
                existing_decl = next((d for d in declaration_set.declarations if d.field == crit_field), None)
                if existing_decl is None or existing_decl.status.value != "FOUND":
                    # Query VLM using PDP image
                    pdp_panel = preprocessed_panels.get(PanelRole.PDP)
                    if pdp_panel:
                        vlm_decl = await self.vlm_interpreter.interpret_field(
                            field=crit_field,
                            image_bytes=pdp_panel["analysis_bytes"],
                            image_id=pdp_panel["image_id"],
                        )
                        if vlm_decl:
                            declaration_set.declarations = [
                                d for d in declaration_set.declarations if d.field != crit_field
                            ] + [vlm_decl]

        # ---------------------------------------------------------------------
        # Stage 4: EVALUATING (Phase 2 23-Rule Statutory Engine)
        # ---------------------------------------------------------------------
        await self._advance_stage(inspection_id, InspectionStatus.EVALUATING, "Adjudicating Legal Metrology compliance across 23 statutory rules")

        scan_date_val = capture_ctx.captured_at.date() if isinstance(capture_ctx.captured_at, datetime) else date.today()
        prod_ctx = ProductContext(
            package_type=capture_ctx.package_type,
            commodity_category=capture_ctx.commodity_category,
            import_status=capture_ctx.import_status,
            fourth_schedule_key=capture_ctx.fourth_schedule_key,
            package_capacity_le_5cm3=capture_ctx.package_capacity_le_5cm3,
            scan_date=scan_date_val,
            ruleset_as_of=scan_date_val,
        )

        rule_results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(declaration_set, prod_ctx)

        # ---------------------------------------------------------------------
        # Stage 5: PERSISTING (Storage upload, signed URLs, DB transaction)
        # ---------------------------------------------------------------------
        await self._advance_stage(inspection_id, InspectionStatus.PERSISTING, "Saving evidence snapshots and minting verification URLs")

        completed_at = datetime.now(timezone.utc)
        image_infos: List[InspectionImageInfo] = []
        db_image_records: List[Dict[str, Any]] = []

        for role, panel in preprocessed_panels.items():
            orig_path = f"{inspection_id}/{role.value.lower()}_original.jpg"
            ana_path = f"{inspection_id}/{panel['analysis_filename']}"

            orig_url = f"/v1/inspections/{inspection_id}/images/{role.value.lower()}/original"
            ana_url = f"/v1/inspections/{inspection_id}/images/{role.value.lower()}/analysis"

            # Upload to private Supabase Storage if configured
            if is_storage_configured():
                try:
                    upload_evidence(orig_path, panel["raw_bytes"], "image/jpeg")
                    upload_evidence(ana_path, panel["analysis_bytes"], "image/jpeg")
                    signed_orig = mint_signed_url(orig_path, expires_in_seconds=120)
                    signed_ana = mint_signed_url(ana_path, expires_in_seconds=120)
                    if signed_orig:
                        orig_url = signed_orig
                    if signed_ana:
                        ana_url = signed_ana
                except Exception as st_exc:
                    logger.warning("Supabase Storage upload skipped (%s). Using relative URL.", st_exc)

            image_infos.append(
                InspectionImageInfo(
                    image_id=panel["image_id"],
                    role=role,
                    original_url=orig_url,
                    analysis_url=ana_url,
                    original_width=panel["orig_w"],
                    original_height=panel["orig_h"],
                )
            )

            db_image_records.append({
                "id": panel["image_id"],
                "inspection_id": inspection_id,
                "role": role.value,
                "storage_path": orig_path,
                "sha256": panel["sha256"],
                "width": panel["orig_w"],
                "height": panel["orig_h"],
            })

        engine_metadata = EngineMetadata(
            rule_engine_version="2026.09.01",
            ruleset_as_of=prod_ctx.ruleset_as_of,
            ocr_engine=ocr_doc.ocr_engine,
            alias_table_version=norm_doc.alias_table_version,
        )

        response = InspectionResponse(
            inspection_id=inspection_id,
            status=InspectionStatus.COMPLETE,
            created_at=self.registry.get(inspection_id).created_at if self.registry.get(inspection_id) else completed_at,
            completed_at=completed_at,
            overall=overall_verdict,
            overall_ui_bucket=overall_ui_bucket,
            summary=summary,
            context=prod_ctx,
            images=image_infos,
            declarations=declaration_set.declarations,
            rule_results=rule_results,
            configured_rule_ids=[r.rule_id for r in rule_results],
            evaluated_rule_ids=[r.rule_id for r in rule_results if r.applicability.status.value == "APPLICABLE"],
            excluded_rule_ids=[
                ExcludedRuleEntry(rule_id=r.rule_id, reason_code=r.applicability.reason_code or "NOT_APPLICABLE")
                for r in rule_results
                if r.applicability.status.value == "NOT_APPLICABLE"
            ],
            engine=engine_metadata,
        )

        # Commit to Postgres
        async with acquire_connection() as conn:
            if conn:
                await image_repo.record_inspection_images(conn, db_image_records)
                await rule_result_repo.save_rule_results(conn, inspection_id, rule_results)
                await inspection_repo.save_terminal_success(
                    conn=conn,
                    inspection_id=inspection_id,
                    overall=overall_verdict.value,
                    overall_ui_bucket=overall_ui_bucket.value,
                    summary_dict=summary.model_dump(),
                    ocr_doc_dict=ocr_doc.model_dump(),
                    declaration_set_dict=declaration_set.model_dump(),
                    engine_dict=engine_metadata.model_dump(),
                    completed_at=completed_at,
                )

        # ---------------------------------------------------------------------
        # Stage 6: COMPLETE
        # ---------------------------------------------------------------------
        await self.registry.set_complete(inspection_id, response)
        logger.info("Inspection %s completed successfully: %s (%s)", inspection_id, overall_verdict.value, overall_ui_bucket.value)
