"""
OCR Router and Failover Orchestrator (C1 per ADR-0004).

Orchestrates primary OCR (Google Cloud Vision) and local automatic fallback (PaddleOCR):
- Calls Cloud Vision first on every panel.
- On Cloud Vision timeout (3.5s), transport error, quota limit, missing credentials,
  or open circuit breaker, automatically dispatches to PaddleOCR without failing.
- Aggregates recognized ImageSlots into a unified OcrDocument.
- Tracks source engine on OcrDocument so downstream stages remain truthful and explainable.
"""

import logging
from typing import List, Optional, Tuple
from lmpc_schema import ImageSlot, OcrDocument, PanelRole

from app.preprocessing import ProcessedPanel
from .cloud_vision import GoogleCloudVisionAdapter
from .paddleocr_engine import PaddleOcrAdapter
from .protocol import CircuitBreakerOpenError, OcrEngine, OcrEngineError

logger = logging.getLogger("packsentry.ocr.router")


class OcrRouter:
    """Manages primary Cloud Vision execution and seamless PaddleOCR fallback."""

    def __init__(
        self,
        primary: Optional[OcrEngine] = None,
        fallback: Optional[OcrEngine] = None,
    ):
        self.primary = primary or GoogleCloudVisionAdapter()
        self.fallback = fallback or PaddleOcrAdapter()

    async def recognize_panel(
        self,
        analysis_bytes: bytes,
        role: PanelRole,
        image_id: str,
        analysis_width: int,
        analysis_height: int,
        original_width: int,
        original_height: int,
        transform,
    ) -> Tuple[ImageSlot, str]:
        """
        Attempts primary OCR; falls back to secondary OCR on any error or circuit trip.
        Returns (ImageSlot, engine_name_used).
        """
        try:
            slot = await self.primary.recognize_panel(
                analysis_bytes=analysis_bytes,
                role=role,
                image_id=image_id,
                analysis_width=analysis_width,
                analysis_height=analysis_height,
                original_width=original_width,
                original_height=original_height,
                transform=transform,
            )
            return slot, self.primary.engine_name
        except (CircuitBreakerOpenError, OcrEngineError, Exception) as exc:
            logger.warning(
                "Primary OCR '%s' unavailable (%s). Falling back automatically to '%s'.",
                self.primary.engine_name,
                exc,
                self.fallback.engine_name,
            )

            # Local fallback execution
            slot = await self.fallback.recognize_panel(
                analysis_bytes=analysis_bytes,
                role=role,
                image_id=image_id,
                analysis_width=analysis_width,
                analysis_height=analysis_height,
                original_width=original_width,
                original_height=original_height,
                transform=transform,
            )
            return slot, self.fallback.engine_name

    async def recognize_inspection(
        self,
        panel_records: List[Tuple[ProcessedPanel, PanelRole, str]],
    ) -> OcrDocument:
        """
        Processes all captured panel images for an inspection.
        panel_records: List of (ProcessedPanel, PanelRole, image_id).
        Returns the unified OcrDocument.
        """
        slots: List[ImageSlot] = []
        engines_used: List[str] = []

        for panel, role, img_id in panel_records:
            slot, engine_used = await self.recognize_panel(
                analysis_bytes=panel.analysis_bytes,
                role=role,
                image_id=img_id,
                analysis_width=panel.analysis_width,
                analysis_height=panel.analysis_height,
                original_width=panel.original_width,
                original_height=panel.original_height,
                transform=panel.transform,
            )
            slots.append(slot)
            if engine_used not in engines_used:
                engines_used.append(engine_used)

        primary_engine = engines_used[0] if engines_used else self.primary.engine_name
        return OcrDocument(
            ocr_engine=primary_engine,
            ocr_version="2026.09",
            images=slots,
        )
