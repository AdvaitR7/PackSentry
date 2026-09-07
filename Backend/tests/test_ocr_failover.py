"""
Tests for OCR Engine Protocol, Circuit Breaker, and Automatic Failover (C1, ADR-0004).

Since this sandboxed environment has neither live Google Cloud Vision credentials
nor an installed PaddleOCR/paddlepaddle build (no cp314 wheels as of 2026-09, see
plan's Environment & Dependency Risks section), these tests exercise the
OcrEngine protocol and OcrRouter failover wiring against FAKE engines, proving:
1. The circuit breaker state machine (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
2. That OcrRouter automatically dispatches to the fallback engine on any primary
   failure, without raising, and records which engine actually served the panel.
"""

import time
import pytest
from lmpc_schema import ImageSlot, PanelRole, Transform

from app.ocr.cloud_vision import CircuitBreaker, CircuitState
from app.ocr.protocol import OcrEngineError
from app.ocr.router import OcrRouter


class FakeFailingEngine:
    """Simulates an OCR engine that always raises (e.g. Cloud Vision without credentials)."""
    engine_name = "fake_failing_engine"
    engine_version = "0.0"

    async def is_available(self) -> bool:
        return False

    async def recognize_panel(self, **kwargs) -> ImageSlot:
        raise OcrEngineError("Simulated primary engine failure (no credentials).")


class FakeSuccessEngine:
    """Simulates a working local fallback OCR engine."""
    engine_name = "fake_success_engine"
    engine_version = "1.0"

    async def is_available(self) -> bool:
        return True

    async def recognize_panel(self, image_id: str, role: PanelRole, analysis_width: int,
                               analysis_height: int, original_width: int, original_height: int,
                               transform: Transform, **kwargs) -> ImageSlot:
        return ImageSlot(
            image_id=image_id,
            role=role,
            analysis_width=analysis_width,
            analysis_height=analysis_height,
            original_width=original_width,
            original_height=original_height,
            transform=transform,
            lines=[],
        )


class FakeTimeoutEngine:
    """Simulates an engine whose circuit breaker has tripped OPEN."""
    engine_name = "fake_timeout_engine"
    engine_version = "0.0"

    def __init__(self):
        self.breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
        for _ in range(3):
            self.breaker.record_failure()

    async def is_available(self) -> bool:
        return self.breaker.can_attempt()

    async def recognize_panel(self, **kwargs) -> ImageSlot:
        from app.ocr.protocol import CircuitBreakerOpenError
        if not self.breaker.can_attempt():
            raise CircuitBreakerOpenError("Circuit breaker is OPEN.")
        raise OcrEngineError("Should not reach here in this test.")


# ---------- Circuit Breaker State Machine ----------

def test_circuit_breaker_starts_closed():
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.can_attempt() is True


def test_circuit_breaker_opens_after_threshold_failures():
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.can_attempt() is False


def test_circuit_breaker_half_open_after_cooldown():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.can_attempt() is False

    time.sleep(0.1)
    assert breaker.can_attempt() is True
    assert breaker.state == CircuitState.HALF_OPEN


def test_circuit_breaker_recovers_to_closed_on_success():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
    breaker.record_failure()
    time.sleep(0.1)
    assert breaker.can_attempt() is True  # transitions to HALF_OPEN

    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


# ---------- OcrRouter Automatic Failover ----------

@pytest.mark.asyncio
async def test_router_falls_back_on_primary_failure():
    router = OcrRouter(primary=FakeFailingEngine(), fallback=FakeSuccessEngine())
    slot, engine_used = await router.recognize_panel(
        analysis_bytes=b"fake_bytes",
        role=PanelRole.PDP,
        image_id="img_test",
        analysis_width=1200,
        analysis_height=1600,
        original_width=3024,
        original_height=4032,
        transform=Transform(),
    )
    assert engine_used == "fake_success_engine"
    assert slot.image_id == "img_test"


@pytest.mark.asyncio
async def test_router_falls_back_on_open_circuit_breaker():
    router = OcrRouter(primary=FakeTimeoutEngine(), fallback=FakeSuccessEngine())
    slot, engine_used = await router.recognize_panel(
        analysis_bytes=b"fake_bytes",
        role=PanelRole.BACK,
        image_id="img_test2",
        analysis_width=1200,
        analysis_height=1600,
        original_width=3024,
        original_height=4032,
        transform=Transform(),
    )
    assert engine_used == "fake_success_engine"


@pytest.mark.asyncio
async def test_router_uses_primary_when_healthy():
    router = OcrRouter(primary=FakeSuccessEngine(), fallback=FakeFailingEngine())
    slot, engine_used = await router.recognize_panel(
        analysis_bytes=b"fake_bytes",
        role=PanelRole.PDP,
        image_id="img_test3",
        analysis_width=1200,
        analysis_height=1600,
        original_width=3024,
        original_height=4032,
        transform=Transform(),
    )
    assert engine_used == "fake_success_engine"


@pytest.mark.asyncio
async def test_router_recognize_inspection_multiple_panels():
    from dataclasses import dataclass
    import numpy as np
    from app.preprocessing import ProcessedPanel

    router = OcrRouter(primary=FakeSuccessEngine(), fallback=FakeSuccessEngine())

    panel = ProcessedPanel(
        analysis_bytes=b"fake",
        analysis_image=np.zeros((10, 10, 3), dtype=np.uint8),
        original_width=3024,
        original_height=4032,
        analysis_width=1200,
        analysis_height=1600,
        transform=Transform(),
    )

    ocr_doc = await router.recognize_inspection([
        (panel, PanelRole.PDP, "img_pdp"),
        (panel, PanelRole.BACK, "img_back"),
    ])

    assert len(ocr_doc.images) == 2
    assert ocr_doc.ocr_engine == "fake_success_engine"
    image_ids = {img.image_id for img in ocr_doc.images}
    assert image_ids == {"img_pdp", "img_back"}
