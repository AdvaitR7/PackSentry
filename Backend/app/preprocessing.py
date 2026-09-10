"""
Image Preprocessing and Coordinate Mapping (B3 and C2 per ADR-0001, ADR-0012).

Handles:
- Headless EXIF orientation correction and decode.
- Longest-edge scaling capped at 1600px, encoded to JPEG quality 85 for analysis.
- Transform computation (scale_x, scale_y, rotation_deg, offset_x, offset_y).
- Bidirectional coordinate mapping between analysis space, original pixel space,
  and normalized [0.0, 1.0] viewport space with <= 2px round-trip accuracy.
"""

from dataclasses import dataclass
import os
from typing import List, Optional, Tuple
import cv2 as cv
import numpy as np
from lmpc_schema import Transform

DEFAULT_MAX_ANALYSIS_EDGE = int(os.environ.get("MAX_ANALYSIS_EDGE", "2048"))


@dataclass
class ProcessedPanel:
    """Represents a preprocessed panel image and its geometric relationship to the original."""
    analysis_bytes: bytes
    analysis_image: np.ndarray
    original_width: int
    original_height: int
    analysis_width: int
    analysis_height: int
    transform: Transform


class CoordinateMapper:
    """
    Bidirectional coordinate mapping between:
    - analysis space: pixel coordinates in the resized analysis image (e.g. 1200x1600)
    - original space: pixel coordinates in the full-resolution captured image (e.g. 3024x4032)
    - normalized space: unit coordinates in [0.0, 1.0] relative to original image width and height
    """

    @staticmethod
    def analysis_to_original(
        polygon_analysis: List[List[float]],
        transform: Transform,
        original_width: int,
        original_height: int,
    ) -> List[List[float]]:
        """Maps polygon from analysis image space to original camera image space."""
        orig_poly: List[List[float]] = []
        scale_x = transform.scale_x if transform.scale_x > 0 else 1.0
        scale_y = transform.scale_y if transform.scale_y > 0 else 1.0

        for pt in polygon_analysis:
            xa, ya = pt[0], pt[1]
            xo = (xa - transform.offset_x) / scale_x
            yo = (ya - transform.offset_y) / scale_y
            # Clamp to image bounds
            xo = max(0.0, min(float(original_width), xo))
            yo = max(0.0, min(float(original_height), yo))
            orig_poly.append([round(xo, 1), round(yo, 1)])
        return orig_poly

    @staticmethod
    def original_to_normalized(
        polygon_original: List[List[float]],
        original_width: int,
        original_height: int,
    ) -> List[List[float]]:
        """Maps polygon from original pixel space to unit [0.0, 1.0] coordinates."""
        norm_poly: List[List[float]] = []
        w = max(1.0, float(original_width))
        h = max(1.0, float(original_height))

        for pt in polygon_original:
            xo, yo = pt[0], pt[1]
            xn = max(0.0, min(1.0, xo / w))
            yn = max(0.0, min(1.0, yo / h))
            norm_poly.append([round(xn, 4), round(yn, 4)])
        return norm_poly

    @staticmethod
    def normalized_to_original(
        polygon_normalized: List[List[float]],
        original_width: int,
        original_height: int,
    ) -> List[List[float]]:
        """Maps polygon from unit [0.0, 1.0] coordinates back to original pixel space."""
        orig_poly: List[List[float]] = []
        w = float(original_width)
        h = float(original_height)

        for pt in polygon_normalized:
            xn, yn = pt[0], pt[1]
            xo = xn * w
            yo = yn * h
            orig_poly.append([round(xo, 1), round(yo, 1)])
        return orig_poly

    @staticmethod
    def analysis_to_normalized(
        polygon_analysis: List[List[float]],
        transform: Transform,
        original_width: int,
        original_height: int,
    ) -> List[List[float]]:
        """Direct helper mapping analysis coordinates to normalized [0.0, 1.0] coordinates."""
        orig = CoordinateMapper.analysis_to_original(
            polygon_analysis, transform, original_width, original_height
        )
        return CoordinateMapper.original_to_normalized(orig, original_width, original_height)


class ImagePreprocessor:
    """Preprocesses camera panel photos for OCR and evidence recording."""

    @staticmethod
    def preprocess_panel(
        raw_bytes: bytes,
        max_edge: int = DEFAULT_MAX_ANALYSIS_EDGE,
        jpeg_quality: int = 85,
    ) -> Optional[ProcessedPanel]:
        """
        Decodes raw bytes with EXIF orientation correction, scales longest edge to <= max_edge,
        computes the geometric Transform, and encodes analysis image to JPEG.
        """
        if not raw_bytes:
            return None

        # cv.IMREAD_COLOR applies embedded EXIF orientation by default in OpenCV 4+
        img = cv.imdecode(np.frombuffer(raw_bytes, np.uint8), cv.IMREAD_COLOR)
        if img is None:
            return None

        orig_h, orig_w = img.shape[:2]
        scale = min(max_edge / max(orig_h, orig_w), 1.0)
        new_w = max(round(orig_w * scale), 1)
        new_h = max(round(orig_h * scale), 1)

        if scale < 1.0:
            analysis_img = cv.resize(img, (new_w, new_h), interpolation=cv.INTER_AREA)
        else:
            analysis_img = img

        scale_x = new_w / orig_w
        scale_y = new_h / orig_h

        transform = Transform(
            rotation_deg=0.0,
            scale_x=round(scale_x, 6),
            scale_y=round(scale_y, 6),
            offset_x=0.0,
            offset_y=0.0,
        )

        encode_params = [int(cv.IMWRITE_JPEG_QUALITY), jpeg_quality]
        success, enc_buf = cv.imencode(".jpg", analysis_img, encode_params)
        if not success:
            return None

        return ProcessedPanel(
            analysis_bytes=enc_buf.tobytes(),
            analysis_image=analysis_img,
            original_width=orig_w,
            original_height=orig_h,
            analysis_width=new_w,
            analysis_height=new_h,
            transform=transform,
        )

    @staticmethod
    def process(raw_bytes: bytes, max_edge: int = 1600):
        """Legacy interface for backwards compatibility with main.py."""
        panel = ImagePreprocessor.preprocess_panel(raw_bytes, max_edge=max_edge)
        if panel is None:
            return None, None
        affine = np.array([
            [panel.transform.scale_x, 0.0, 0.0],
            [0.0, panel.transform.scale_y, 0.0],
        ], dtype=np.float64)
        return panel.analysis_image, affine
