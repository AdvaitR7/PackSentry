"""
Unit tests for QwenOcrAdapter (Phase 1).
Verifies parsing of JSON, line-based, and bounding-box coordinates into valid ImageSlot structures.
"""

import pytest
from lmpc_schema import PanelRole, Transform
from app.ocr.qwen_engine import QwenOcrAdapter


def test_qwen_ocr_parse_structured_json():
    adapter = QwenOcrAdapter()
    sample_json = """
    {
        "lines": [
            {"text": "Net Qty: 500 g", "box_2d": [100, 200, 150, 600]},
            {"text": "MRP Rs. 150.00 (incl. of all taxes)", "box_2d": [200, 200, 250, 800]}
        ]
    }
    """
    slot = adapter._parse_response(
        raw_response=sample_json,
        role=PanelRole.PDP,
        image_id="img_test_pdp",
        analysis_width=1000,
        analysis_height=1000,
        original_width=2000,
        original_height=2000,
        transform=Transform(),
    )

    assert slot.image_id == "img_test_pdp"
    assert len(slot.lines) == 2
    assert slot.lines[0].raw_text == "Net Qty: 500 g"
    assert slot.lines[0].confidence == 0.95
    assert slot.lines[0].polygon_analysis == [
        [200.0, 100.0],
        [600.0, 100.0],
        [600.0, 150.0],
        [200.0, 150.0],
    ]
    # Check normalized polygon mapping
    assert slot.lines[0].polygon_normalized[0] == [0.1, 0.05]
    assert slot.lines[0].polygon_normalized[2] == [0.3, 0.075]


def test_qwen_ocr_parse_fallback_raw_lines():
    adapter = QwenOcrAdapter()
    raw_text = "Manufactured by ABC Foods Ltd\nNet Wt. 1 kg\nBest Before 12 Months"
    slot = adapter._parse_response(
        raw_response=raw_text,
        role=PanelRole.BACK,
        image_id="img_test_back",
        analysis_width=800,
        analysis_height=1200,
        original_width=1600,
        original_height=2400,
        transform=Transform(),
    )

    assert len(slot.lines) == 3
    assert slot.lines[0].raw_text == "Manufactured by ABC Foods Ltd"
    assert slot.lines[1].raw_text == "Net Wt. 1 kg"
    assert slot.lines[2].raw_text == "Best Before 12 Months"
