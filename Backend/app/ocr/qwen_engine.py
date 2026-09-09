"""
Qwen2.5-VL Primary OCR Adapter.

Invokes local Qwen2.5-VL (7B primary, 3B fallback) via Ollama for full-panel
verbatim text recognition. Implements the standard OcrEngine protocol so its
recognized lines and polygons populate ImageSlot and flow through the standard
deterministic normalisation and extraction pipelines.
"""

import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx
from lmpc_schema import ImageSlot, Line, PanelRole, Transform, Word

from app.preprocessing import CoordinateMapper
from .protocol import OcrEngineError

logger = logging.getLogger("packsentry.ocr.qwen")

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("QWEN_OCR_MODEL", "qwen2.5vl:7b")
FALLBACK_MODEL = "qwen2.5vl:3b"


class QwenOcrAdapter:
    """OcrEngine implementation using local Qwen2.5-VL via Ollama."""

    engine_name = "qwen2.5vl"
    engine_version = "2.5"

    def __init__(
        self,
        host: str = DEFAULT_OLLAMA_HOST,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 12.0,
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def is_available(self) -> bool:
        """Checks if local Ollama is reachable and has a Qwen2.5-VL model available."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.host}/api/tags")
                if res.status_code != 200:
                    return False
                data = res.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return any("qwen2.5vl" in m or "qwen2.5-vl" in m or self.model in m for m in models)
        except Exception:
            return False

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
        Extracts all visible text lines verbatim using Qwen2.5-VL.
        Maps line bounding boxes back to original and normalized coordinate spaces.
        """
        prompt = (
            "You are a Legal Metrology text detection and OCR engine. "
            "Examine this packaging panel photo carefully. Extract every visible line of printed text "
            "verbatim, exactly as written, including numbers, units (e.g. g, gms, ml, kg), dates, "
            "currency, addresses, and commodity names in Hindi and English. Do not normalize or correct spelling. "
            "Return a JSON object with a key 'lines' containing an array of objects. "
            "Each object must have: 'text' (string with verbatim line content) and 'box_2d' "
            "([ymin, xmin, ymax, xmax] as integers on a 0 to 1000 scale representing the text boundary)."
        )

        b64_image = base64.b64encode(analysis_bytes).decode("utf-8")
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [b64_image],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.post(f"{self.host}/api/generate", json=payload)
                if res.status_code != 200:
                    raise OcrEngineError(
                        f"Ollama /api/generate returned HTTP {res.status_code}: {res.text[:200]}"
                    )
                data = res.json()
                raw_response = data.get("response", "{}")
        except Exception as exc:
            raise OcrEngineError(f"Qwen2.5-VL OCR inference failed: {exc}") from exc

        return self._parse_response(
            raw_response=raw_response,
            role=role,
            image_id=image_id,
            analysis_width=analysis_width,
            analysis_height=analysis_height,
            original_width=original_width,
            original_height=original_height,
            transform=transform,
        )

    def _parse_response(
        self,
        raw_response: str,
        role: PanelRole,
        image_id: str,
        analysis_width: int,
        analysis_height: int,
        original_width: int,
        original_height: int,
        transform: Transform,
    ) -> ImageSlot:
        """Parses JSON or line-structured response from Qwen into ImageSlot lines."""
        extracted_entries: List[Dict[str, Any]] = []

        try:
            parsed = json.loads(raw_response)
            if isinstance(parsed, dict):
                # Try common keys
                lines_data = parsed.get("lines") or parsed.get("text_lines") or parsed.get("declarations")
                if isinstance(lines_data, list):
                    for item in lines_data:
                        if isinstance(item, dict) and (item.get("text") or item.get("raw_text")):
                            extracted_entries.append({
                                "text": str(item.get("text") or item.get("raw_text")).strip(),
                                "box_2d": item.get("box_2d") or item.get("box") or [0, 0, 1000, 1000],
                            })
                        elif isinstance(item, str) and item.strip():
                            extracted_entries.append({"text": item.strip(), "box_2d": [0, 0, 1000, 1000]})
                elif not lines_data:
                    # Flat dictionary of detected fields
                    for k, v in parsed.items():
                        if isinstance(v, str) and v.strip():
                            extracted_entries.append({"text": f"{k}: {v}", "box_2d": [0, 0, 1000, 1000]})
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and (item.get("text") or item.get("raw_text")):
                        extracted_entries.append({
                            "text": str(item.get("text") or item.get("raw_text")).strip(),
                            "box_2d": item.get("box_2d") or [0, 0, 1000, 1000],
                        })
                    elif isinstance(item, str) and item.strip():
                        extracted_entries.append({"text": item.strip(), "box_2d": [0, 0, 1000, 1000]})
        except Exception:
            # Fallback: treat non-JSON raw response lines as verbatim lines
            for line in raw_response.splitlines():
                clean = line.strip().strip('"').strip("'")
                if clean and not clean.startswith("{") and not clean.startswith("}"):
                    extracted_entries.append({"text": clean, "box_2d": [0, 0, 1000, 1000]})

        lines: List[Line] = []
        for idx, entry in enumerate(extracted_entries):
            text = entry["text"]
            box = entry.get("box_2d", [0, 0, 1000, 1000])
            if not isinstance(box, (list, tuple)) or len(box) < 4:
                box = [0, 0, 1000, 1000]

            ymin, xmin, ymax, xmax = [float(c) for c in box[:4]]

            # Convert 0-1000 scale to pixel coordinates in analysis image
            px_x1 = max(0.0, min(float(analysis_width), (xmin / 1000.0) * analysis_width))
            px_y1 = max(0.0, min(float(analysis_height), (ymin / 1000.0) * analysis_height))
            px_x2 = max(px_x1, min(float(analysis_width), (xmax / 1000.0) * analysis_width))
            px_y2 = max(px_y1, min(float(analysis_height), (ymax / 1000.0) * analysis_height))

            # 4-point polygon in analysis coordinates
            poly_analysis = [
                [px_x1, px_y1],
                [px_x2, px_y1],
                [px_x2, px_y2],
                [px_x1, px_y2],
            ]

            poly_orig = CoordinateMapper.analysis_to_original(
                poly_analysis, transform, original_width, original_height
            )
            poly_norm = CoordinateMapper.original_to_normalized(
                poly_orig, original_width, original_height
            )

            lines.append(
                Line(
                    line_id=f"{image_id}:l{idx + 1:03d}",
                    raw_text=text,
                    confidence=0.95,
                    polygon_analysis=poly_analysis,
                    polygon_original=poly_orig,
                    polygon_normalized=poly_norm,
                    script="LATIN",
                    words=[],
                )
            )

        return ImageSlot(
            image_id=image_id,
            role=role,
            analysis_width=analysis_width,
            analysis_height=analysis_height,
            original_width=original_width,
            original_height=original_height,
            transform=transform,
            lines=lines,
        )
