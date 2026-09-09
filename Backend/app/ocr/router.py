"""
OCR Router and Failover Orchestrator.

Runs one OCR engine at a time for each panel in priority order:
Qwen2.5-VL -> PaddleOCR -> Google Cloud Vision.
"""

import logging
from typing import List, Optional, Tuple
from lmpc_schema import ImageSlot, OcrDocument, PanelRole

from app.preprocessing import ProcessedPanel
from .cloud_vision import GoogleCloudVisionAdapter
from .paddleocr_engine import PaddleOcrAdapter
from .protocol import OcrEngine, OcrEngineError
from .qwen_engine import QwenOcrAdapter

logger = logging.getLogger("packsentry.ocr.router")


class OcrRouter:
    """Runs Qwen first, then PaddleOCR, then Cloud Vision, one engine at a time."""

    def __init__(
        self,
        primary: Optional[OcrEngine] = None,
        fallback: Optional[OcrEngine] = None,
        tertiary: Optional[OcrEngine] = None,
    ):
        self.primary = primary or QwenOcrAdapter()
        self.fallback = fallback or PaddleOcrAdapter()
        self.tertiary = tertiary or GoogleCloudVisionAdapter()

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
        """Tries each configured OCR engine sequentially and returns the first success."""
        kwargs = {
            "analysis_bytes": analysis_bytes,
            "role": role,
            "image_id": image_id,
            "analysis_width": analysis_width,
            "analysis_height": analysis_height,
            "original_width": original_width,
            "original_height": original_height,
            "transform": transform,
        }
        engines = [self.primary, self.fallback, self.tertiary]
        failures = []

        for index, engine in enumerate(engines):
            try:
                slot = await engine.recognize_panel(**kwargs)
                return slot, engine.engine_name
            except Exception as exc:
                failures.append(f"{engine.engine_name}: {exc}")
                if index < len(engines) - 1:
                    logger.warning(
                        "OCR '%s' unavailable (%s). Trying '%s'.",
                        engine.engine_name,
                        exc,
                        engines[index + 1].engine_name,
                    )

        raise OcrEngineError("All OCR engines failed: " + "; ".join(failures))

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
