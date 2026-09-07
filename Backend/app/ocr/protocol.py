"""
OCR Engine Protocol (Track C1 per ADR-0001, ADR-0004).

Defines the contract for OCR adapters (Cloud Vision primary, PaddleOCR fallback).
Every adapter accepts preprocessed panel image bytes and geometric transform,
and emits an ImageSlot populated with Lines, Words, and mapped Polygons.
"""

from typing import List, Protocol, runtime_checkable
from lmpc_schema import ImageSlot, PanelRole, Transform


class OcrEngineError(Exception):
    """Base exception for OCR engine failures."""
    pass


class CircuitBreakerOpenError(OcrEngineError):
    """Raised when an engine's circuit breaker is open."""
    pass


@runtime_checkable
class OcrEngine(Protocol):
    """Standardized protocol for text detection adapters."""
    engine_name: str
    engine_version: str

    async def is_available(self) -> bool:
        """Returns whether the engine is initialized and ready to serve requests."""
        ...

    async def recognize_panel(
        self,
        analysis_bytes: bytes,
        role: PanelRole,
        image_id: str,
        analysis_width: int,
        analysis_height: int,
        original_width: int,
        original_height: int,
        transform: Transform,
    ) -> ImageSlot:
        """
        Extracts text and bounding polygons from an analysis image.
        Returns a complete ImageSlot with polygon_analysis, polygon_original,
        and polygon_normalized populated.
        """
        ...
