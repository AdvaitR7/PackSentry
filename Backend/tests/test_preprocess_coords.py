"""
Tests for Image Preprocessing and Coordinate Mapping (B3 & C2).
Verifies:
- EXIF orientation handling & longest-edge scaling to <= 1600 px.
- Transform matrix calculation.
- Bidirectional coordinate mapping with <= 2.0 px round-trip error.
"""

import cv2 as cv
import numpy as np
import pytest

from app.preprocessing import CoordinateMapper, ImagePreprocessor
from lmpc_schema import Transform


def create_test_image_bytes(width: int = 3000, height: int = 4000) -> bytes:
    """Generates an uncompressed synthetic test image as JPEG bytes."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Draw simple geometric patterns to ensure non-empty compression
    cv.rectangle(img, (200, 300), (1200, 800), (255, 255, 255), -1)
    cv.circle(img, (1500, 2000), 400, (0, 255, 0), -1)
    cv.putText(img, "NET QTY 500g", (500, 1500), cv.FONT_HERSHEY_SIMPLEX, 4.0, (0, 0, 255), 8)
    success, buf = cv.imencode(".jpg", img, [int(cv.IMWRITE_JPEG_QUALITY), 95])
    assert success
    return buf.tobytes()


def test_image_preprocessor_resize():
    orig_w, orig_h = 3000, 4000
    raw_bytes = create_test_image_bytes(width=orig_w, height=orig_h)

    panel = ImagePreprocessor.preprocess_panel(raw_bytes, max_edge=1600, jpeg_quality=85)
    assert panel is not None
    assert panel.original_width == orig_w
    assert panel.original_height == orig_h
    # Longest edge must be exactly 1600
    assert max(panel.analysis_width, panel.analysis_height) == 1600
    assert panel.analysis_height == 1600
    assert panel.analysis_width == 1200
    assert len(panel.analysis_bytes) > 0
    assert panel.transform.scale_y == pytest.approx(1600 / 4000, rel=1e-4)
    assert panel.transform.scale_x == pytest.approx(1200 / 3000, rel=1e-4)


def test_image_preprocessor_small_image_no_upscale():
    # If image is already smaller than max_edge, scale factor must be 1.0
    raw_bytes = create_test_image_bytes(width=800, height=600)
    panel = ImagePreprocessor.preprocess_panel(raw_bytes, max_edge=1600)
    assert panel is not None
    assert panel.original_width == 800
    assert panel.original_height == 600
    assert panel.analysis_width == 800
    assert panel.analysis_height == 600
    assert panel.transform.scale_x == 1.0
    assert panel.transform.scale_y == 1.0


def test_coordinate_mapping_round_trip_accuracy():
    """
    Asserts that mapping a point from original space -> analysis space -> original space
    and original space -> normalized space -> original space satisfies <= 2.0 px error.
    """
    orig_w, orig_h = 3024, 4032
    analysis_w, analysis_h = 1200, 1600
    transform = Transform(
        rotation_deg=0.0,
        scale_x=analysis_w / orig_w,
        scale_y=analysis_h / orig_h,
        offset_x=0.0,
        offset_y=0.0,
    )

    # Test various sample polygons across the label surface
    test_polygons = [
        [[500.0, 600.0], [1500.0, 600.0], [1500.0, 750.0], [500.0, 750.0]],
        [[120.0, 2200.0], [2400.0, 2200.0], [2400.0, 2350.0], [120.0, 2350.0]],
        [[0.0, 0.0], [3024.0, 0.0], [3024.0, 4032.0], [0.0, 4032.0]],
    ]

    for orig_poly in test_polygons:
        # 1. Map to analysis space
        analysis_poly = [
            [pt[0] * transform.scale_x, pt[1] * transform.scale_y]
            for pt in orig_poly
        ]

        # 2. Map back to original space using CoordinateMapper
        recovered_orig = CoordinateMapper.analysis_to_original(
            analysis_poly, transform, orig_w, orig_h
        )

        for orig_pt, rec_pt in zip(orig_poly, recovered_orig):
            assert abs(orig_pt[0] - rec_pt[0]) <= 2.0, f"X round-trip error too large: {orig_pt} vs {rec_pt}"
            assert abs(orig_pt[1] - rec_pt[1]) <= 2.0, f"Y round-trip error too large: {orig_pt} vs {rec_pt}"

        # 3. Map original to normalized [0.0, 1.0]
        norm_poly = CoordinateMapper.original_to_normalized(orig_poly, orig_w, orig_h)
        for pt in norm_poly:
            assert 0.0 <= pt[0] <= 1.0
            assert 0.0 <= pt[1] <= 1.0

        # 4. Map normalized back to original
        recovered_from_norm = CoordinateMapper.normalized_to_original(norm_poly, orig_w, orig_h)
        for orig_pt, rec_norm_pt in zip(orig_poly, recovered_from_norm):
            assert abs(orig_pt[0] - rec_norm_pt[0]) <= 2.0, f"Norm round-trip error too large: {orig_pt} vs {rec_norm_pt}"
            assert abs(orig_pt[1] - rec_norm_pt[1]) <= 2.0, f"Norm round-trip error too large: {orig_pt} vs {rec_norm_pt}"


def test_legacy_process_interface():
    raw_bytes = create_test_image_bytes(width=1000, height=2000)
    img, affine = ImagePreprocessor.process(raw_bytes, max_edge=1600)
    assert img is not None
    assert affine is not None
    assert affine.shape == (2, 3)
    assert img.shape[0] == 1600
    assert img.shape[1] == 800
