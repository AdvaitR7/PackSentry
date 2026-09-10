"""
OCR Router and Failover Orchestrator.

Runs one OCR engine at a time for each panel in priority order:
Gemini 2.5 Flash -> Qwen2.5-VL -> PaddleOCR -> Google Cloud Vision.
"""

import logging
from typing import List, Optional, Tuple
from lmpc_schema import ImageSlot, OcrDocument, PanelRole

from app.preprocessing import ProcessedPanel
from .cloud_vision import GoogleCloudVisionAdapter
from .gemini_engine import GeminiFlashOcrAdapter
from .paddleocr_engine import PaddleOcrAdapter
from .protocol import OcrEngine, OcrEngineError
from .qwen_engine import QwenOcrAdapter

logger = logging.getLogger("packsentry.ocr.router")


class OcrRouter:
    """Runs Gemini first (if configured), then Qwen, then PaddleOCR, then Cloud Vision."""

    def __init__(
        self,
        primary: Optional[OcrEngine] = None,
        fallback: Optional[OcrEngine] = None,
        tertiary: Optional[OcrEngine] = None,
        quaternary: Optional[OcrEngine] = None,
        engines: Optional[List[OcrEngine]] = None,
    ):
        if engines is not None:
            self.engines = engines
        elif (
            primary is not None
            or fallback is not None
            or tertiary is not None
            or quaternary is not None
        ):
            self.engines = [e for e in [primary, fallback, tertiary, quaternary] if e is not None]
        else:
            gemini = GeminiFlashOcrAdapter()
            if gemini.api_key:
                # Use Gemini 2.5 Flash exclusively when configured; do NOT run PaddleOCR or Qwen
                self.engines = [gemini]
            else:
                self.engines = [
                    gemini,
                    QwenOcrAdapter(),
                    PaddleOcrAdapter(),
                    GoogleCloudVisionAdapter(),
                ]

        self.primary = self.engines[0] if len(self.engines) > 0 else None
        self.fallback = self.engines[1] if len(self.engines) > 1 else None
        self.tertiary = self.engines[2] if len(self.engines) > 2 else None
        self.quaternary = self.engines[3] if len(self.engines) > 3 else None

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
        failures = []

        for index, engine in enumerate(self.engines):
            try:
                # If engine exposes availability check and reports unavailable, skip directly
                if hasattr(engine, "is_available"):
                    available = await engine.is_available()
                    if not available:
                        failures.append(
                            f"{engine.engine_name}: not available (unreachable or missing credentials)"
                        )
                        continue

                slot = await engine.recognize_panel(**kwargs)
                return slot, engine.engine_name
            except Exception as exc:
                failures.append(f"{engine.engine_name}: {exc}")
                if index < len(self.engines) - 1:
                    logger.warning(
                        "OCR '%s' unavailable (%s). Trying next configured engine.",
                        engine.engine_name,
                        exc,
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
