"""
Tests for OCR Engine Protocol, Circuit Breaker, and Automatic Failover (C1, ADR-0004).

Since this environment has no live Google Cloud Vision credentials, the failover
tests exercise the OcrEngine protocol and OcrRouter wiring against FAKE engines,
proving:
1. The circuit breaker state machine (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
2. That OcrRouter automatically dispatches to the fallback engine on any primary
   failure, without raising, and records which engine actually served the panel.

The final section drives the REAL PaddleOcrAdapter against the installed
paddleocr build, so upstream API drift fails here rather than at inspection time.
"""

import importlib.util
import time
from pathlib import Path

import pytest
from lmpc_schema import ImageSlot, Line, PanelRole, Transform

from app.ocr.cloud_vision import CircuitBreaker, CircuitState
from app.ocr.paddleocr_engine import PaddleOcrAdapter
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
            lines=[
                Line(
                    line_id=f"{image_id}:l001",
                    raw_text="Net Qty: 500 g",
                    confidence=0.95,
                    polygon_analysis=[],
                    polygon_original=[],
                    polygon_normalized=[],
                    words=[],
                )
            ],
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
async def test_router_uses_tertiary_when_primary_and_fallback_fail():
    router = OcrRouter(
        primary=FakeFailingEngine(),
        fallback=FakeFailingEngine(),
        tertiary=FakeSuccessEngine(),
    )
    slot, engine_used = await router.recognize_panel(
        analysis_bytes=b"fake_bytes",
        role=PanelRole.PDP,
        image_id="img_tertiary",
        analysis_width=1200,
        analysis_height=1600,
        original_width=3024,
        original_height=4032,
        transform=Transform(),
    )
    assert engine_used == "fake_success_engine"
    assert slot.image_id == "img_tertiary"


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


# ---------- Real PaddleOCR Adapter Contract (no mocks) ----------
#
# The failover tests above deliberately use fakes to isolate the router's wiring,
# which means the real adapter's constructor, inference call, and result parsing
# have no coverage at all. These tests drive the installed paddleocr build
# directly so a breaking upstream API change fails here instead of at inspection
# time in the app.

paddleocr_required = pytest.mark.skipif(
    importlib.util.find_spec("paddleocr") is None,
    reason="paddleocr is not installed in this environment",
)

SAMPLE_PANEL = Path(__file__).resolve().parents[2] / "Frontend/app/assets/images/front.png"


@paddleocr_required
def test_paddle_adapter_builds_cpu_instance_with_supported_kwargs():
    """The CPU constructor kwargs must be accepted by the installed paddleocr."""
    PaddleOcrAdapter(lang="en", use_gpu=False)._build_instance(use_gpu=False)


@paddleocr_required
@pytest.mark.skipif(not SAMPLE_PANEL.exists(), reason="sample panel fixture missing")
@pytest.mark.asyncio
async def test_paddle_adapter_recognizes_a_real_panel_on_cpu():
    """
    Full adapter path on real image bytes: constructor -> inference -> parsing.
    Asserts real text came back, so a silently-empty parse cannot pass.
    """
    adapter = PaddleOcrAdapter(lang="en", use_gpu=False)
    slot = await adapter.recognize_panel(
        analysis_bytes=SAMPLE_PANEL.read_bytes(),
        role=PanelRole.PDP,
        image_id="img_real_pdp",
        analysis_width=1200,
        analysis_height=1600,
        original_width=1200,
        original_height=1600,
        transform=Transform(),
    )

    assert slot.image_id == "img_real_pdp"
    assert slot.lines, "PaddleOCR returned no lines for a text-bearing panel"
    assert any(line.raw_text.strip() for line in slot.lines)
    for line in slot.lines:
        assert 0.0 <= line.confidence <= 1.0
        assert len(line.polygon_analysis) == 4


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
