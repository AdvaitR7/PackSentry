"""
End-to-End OCR Failover Rehearsal Test (Phase 5 Hardening & Demo Rehearsal).

Simulates forced Google Cloud Vision outage (network timeout, invalid ADC credentials,
or 403 quota exhaustion) and verifies that:
1. OcrRouter seamlessly switches to PaddleOCR without raising an unhandled exception.
2. The Circuit Breaker trips after repeated failures to protect latency.
3. The resulting OcrDocument strictly stamps ocr_engine as the fallback engine.
4. The entire downstream pipeline (Normalise -> Extract -> Evaluate) runs cleanly,
   producing a valid, verifiable InspectionResponse.
"""

from unittest.mock import AsyncMock, patch
import pytest

from lmpc_schema import (
    CaptureContext,
    CommodityCategory,
    ImportStatus,
    InspectionResponse,
    PackageType,
    PanelRole,
    ProductContext,
    Transform,
)

from app.extraction import extract_declarations
from app.normalise import build_normalised_document
from app.ocr.cloud_vision import GoogleCloudVisionAdapter
from app.ocr.paddleocr_engine import PaddleOcrAdapter
from app.ocr.protocol import OcrEngineError
from app.ocr.router import OcrRouter
from app.preprocessing import ProcessedPanel
from app.rules import evaluate_inspection
import numpy as np


@pytest.mark.asyncio
async def test_rehearsal_forced_cloud_vision_failure_triggers_fallback():
    """
    Simulates a live demonstration scenario where Google Cloud Vision credentials
    are missing or network connectivity is severed.
    """
    # 1. Primary engine that fails as Google Cloud Vision would under missing credentials
    failing_cloud_vision = GoogleCloudVisionAdapter()

    # Mock the internal vision client to simulate transport/credential failure
    with patch.object(
        failing_cloud_vision,
        "recognize_panel",
        side_effect=OcrEngineError("Simulated WAN disconnect / ADC missing during rehearsal."),
    ):
        # 2. Local fallback engine (PaddleOCR adapter with simulated lines)
        fallback_paddle = PaddleOcrAdapter()

        async def mock_paddle_recognize(image_id, role, analysis_width, analysis_height,
                                        original_width, original_height, transform, **kwargs):
            from lmpc_schema import ImageSlot, Line, Word
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
                        line_id="l1",
                        raw_text="PREMIUM ASSAM TEA",
                        confidence=0.98,
                        polygon_normalized=[[0.0, 0.0], [1.0, 1.0]],
                        words=[Word(raw_text="PREMIUM", confidence=0.98, polygon_normalized=[[0.0, 0.0], [0.5, 0.5]])],
                    ),
                    Line(
                        line_id="l2",
                        raw_text="Net Qty: 500 g",
                        confidence=0.95,
                        polygon_normalized=[[0.0, 0.0], [1.0, 1.0]],
                        words=[],
                    ),
                    Line(
                        line_id="l3",
                        raw_text="MRP Rs. 249.00 (inclusive of all taxes)",
                        confidence=0.96,
                        polygon_normalized=[[0.0, 0.0], [1.0, 1.0]],
                        words=[],
                    ),
                ],
            )

        with patch.object(fallback_paddle, "recognize_panel", side_effect=mock_paddle_recognize):
            # Orchestrate with OcrRouter
            router = OcrRouter(primary=failing_cloud_vision, fallback=fallback_paddle)

            panel = ProcessedPanel(
                analysis_bytes=b"sample_jpeg_bytes",
                analysis_image=np.zeros((10, 10, 3), dtype=np.uint8),
                original_width=3024,
                original_height=4032,
                analysis_width=1200,
                analysis_height=1600,
                transform=Transform(),
            )

            # Recognize multiple inspection panels
            ocr_doc = await router.recognize_inspection([
                (panel, PanelRole.PDP, "img_pdp_001"),
                (panel, PanelRole.BACK, "img_back_002"),
            ])

            # Invariant 1: Router did not crash and populated both panels
            assert len(ocr_doc.images) == 2

            # Invariant 2: Truthful engine stamping (recorded paddleocr, not cloud vision)
            assert ocr_doc.ocr_engine == "paddleocr"

            # Invariant 3: Downstream pipeline succeeds end-to-end
            norm_doc = build_normalised_document(ocr_doc)
            assert len(norm_doc.lines) > 0

            from datetime import datetime, timezone
            capture_ctx = CaptureContext(
                inspector_id="insp_rehearsal_001",
                captured_at=datetime.now(timezone.utc),
                package_type=PackageType.RETAIL,
                commodity_category=CommodityCategory.GENERAL,
                import_status=ImportStatus.DOMESTIC,
                all_panels_confirmed=True,
            )
            declarations = extract_declarations(norm_doc, ocr_doc, capture_ctx)
            assert declarations is not None

            from datetime import date
            product_ctx = ProductContext(
                package_type=PackageType.RETAIL,
                commodity_category=CommodityCategory.GENERAL,
                import_status=ImportStatus.DOMESTIC,
                scan_date=date(2026, 9, 7),
                ruleset_as_of=date(2026, 9, 7),
            )
            rule_results, overall_verdict, ui_bucket, summary = evaluate_inspection(declarations, product_ctx)

            assert overall_verdict is not None
            assert ui_bucket is not None
            assert len(rule_results) == 23


@pytest.mark.asyncio
async def test_rehearsal_circuit_breaker_trips_to_protect_latency():
    """Verifies that consecutive failures trip circuit breaker OPEN so primary is skipped."""
    primary = GoogleCloudVisionAdapter()
    primary.breaker.failure_threshold = 2

    # Record 2 failures to simulate quota error or outage
    primary.breaker.record_failure()
    primary.breaker.record_failure()
    assert primary.breaker.can_attempt() is False

    fallback = PaddleOcrAdapter()
    with patch.object(
        fallback,
        "recognize_panel",
        new_callable=AsyncMock,
    ) as mock_fallback:
        from lmpc_schema import ImageSlot
        mock_fallback.return_value = ImageSlot(
            image_id="img1",
            role=PanelRole.PDP,
            analysis_width=100,
            analysis_height=100,
            original_width=100,
            original_height=100,
            transform=Transform(),
            lines=[],
        )

        router = OcrRouter(primary=primary, fallback=fallback)
        slot, engine = await router.recognize_panel(
            analysis_bytes=b"data",
            role=PanelRole.PDP,
            image_id="img1",
            analysis_width=100,
            analysis_height=100,
            original_width=100,
            original_height=100,
            transform=Transform(),
        )

        assert engine == "paddleocr"
        mock_fallback.assert_called_once()
