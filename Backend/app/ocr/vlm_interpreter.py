"""
Selective Qwen2.5-VL VLM Interpreter (D7 per ADR-0004).

Selectively invokes local Qwen2.5-VL (7B primary, 3B fallback) via Ollama
for difficult label regions or unlocated declarations.
CRITICAL SAFETY INVARIANT (ADR-0004, ADR-0005):
Everything output by this interpreter is tagged with ExtractionMethod.VLM_FALLBACK
and carries transitive provenance taint. It can NEVER support an accusation or clean clearance.
"""

import base64
import json
import logging
import os
from typing import Any, Dict, Optional
import httpx
from lmpc_schema import (
    Declaration,
    EvidenceSpan,
    ExtractionMethod,
    ExtractionStatus,
    Field,
)

from app.extraction.date import parse_date
from app.extraction.price import parse_price
from app.extraction.quantity import parse_quantity
from app.provenance import tag_as_vlm_fallback

logger = logging.getLogger("packsentry.ocr.vlm")

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = "qwen2.5vl:7b"
FALLBACK_MODEL = "qwen2.5vl:3b"


class QwenVlmInterpreter:
    """Selective vision-language interpretation adapter via Ollama."""

    def __init__(
        self,
        host: str = DEFAULT_OLLAMA_HOST,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 6.0,
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def is_reachable(self) -> bool:
        """Checks if local Ollama daemon is running and reachable."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.host}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def get_readiness(self) -> Dict[str, Any]:
        """Returns detailed Ollama engine readiness for /healthz."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.host}/api/ps")
                if res.status_code != 200:
                    return {"reachable": False, "resident": False, "model": self.model}
                data = res.json()
                models = data.get("models", [])
                is_resident = any(self.model in m.get("name", "") for m in models)
                return {
                    "reachable": True,
                    "resident": is_resident,
                    "model": self.model,
                    "running_models": [m.get("name") for m in models],
                }
        except Exception as e:
            return {"reachable": False, "resident": False, "model": self.model, "error": str(e)}

    async def interpret_field(
        self,
        field: Field,
        image_bytes: bytes,
        image_id: str,
    ) -> Optional[Declaration]:
        """
        Selectively queries Qwen2.5-VL for a single unlocated declaration.
        Returns a Declaration tagged with ExtractionMethod.VLM_FALLBACK.
        """
        prompt = (
            f"You are a Legal Metrology packaging inspector. Look at this package photo. "
            f"Extract the exact visible text for the declaration: {field.value}. "
            f"Return a JSON object with keys: 'found' (boolean), 'exact_raw_text' (string or null). "
            f"Transcribe verbatim without correcting spellings or units."
        )

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
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
                    logger.warning("Ollama /api/generate returned status %d", res.status_code)
                    return None
                data = res.json()
                raw_response = data.get("response", "{}")
                parsed_json = json.loads(raw_response)
        except Exception as e:
            logger.warning("VLM interpretation call failed: %s", e)
            return None

        found = parsed_json.get("found", False)
        raw_text = parsed_json.get("exact_raw_text")

        if not found or not raw_text:
            return None

        # Parse the raw text according to the requested field
        parsed_subobject = None
        if field == Field.NET_QUANTITY:
            q_res = parse_quantity(raw_text)
            if q_res:
                _, parsed_subobject = q_res
        elif field == Field.RETAIL_SALE_PRICE:
            p_res = parse_price(raw_text)
            if p_res:
                _, parsed_subobject = p_res
        elif field == Field.DATE_OF_MANUFACTURE_PACKING_IMPORT:
            d_res = parse_date(raw_text)
            if d_res:
                _, parsed_subobject = d_res

        evidence = [
            EvidenceSpan(
                image_id=image_id,
                line_id=f"{image_id}:vlm_fallback",
                polygon_normalized=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
                raw_text=raw_text,
            )
        ]

        decl = Declaration(
            field=field,
            status=ExtractionStatus.FOUND,
            raw_value=raw_text,
            parsed=parsed_subobject,
            evidence=evidence,
            ocr_confidence=0.85,
            extraction_confidence=0.75,
            method=ExtractionMethod.VLM_FALLBACK,
        )

        return tag_as_vlm_fallback(decl)
