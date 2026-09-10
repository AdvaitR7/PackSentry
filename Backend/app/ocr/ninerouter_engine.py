"""9Router OpenAI-compatible multimodal OCR adapter."""

import base64
import json
import logging
import os
from typing import Any, Dict, Optional

import httpx
from lmpc_schema import ImageSlot, PanelRole, Transform

from .gemini_engine import (
    STRUCTURED_RESPONSE_SCHEMA,
    SYSTEM_PROMPT,
    GeminiFlashOcrAdapter,
)
from .protocol import OcrEngineError

logger = logging.getLogger("packsentry.ocr.ninerouter")

DEFAULT_NINEROUTER_URL = os.environ.get("NINEROUTER_URL", "").strip().rstrip("/")
DEFAULT_NINEROUTER_MODEL = os.environ.get(
    "NINEROUTER_OCR_MODEL", "ag/gemini-3.8-flash"
).strip()
DEFAULT_NINEROUTER_TIMEOUT = float(
    os.environ.get("NINEROUTER_TIMEOUT_SECONDS", "60.0")
)


def _to_json_schema(value: Any) -> Any:
    """Converts Gemini schema casing/nullability to standard JSON Schema."""
    if isinstance(value, list):
        return [_to_json_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    converted: Dict[str, Any] = {}
    nullable = value.get("nullable") is True
    for key, item in value.items():
        if key == "nullable":
            continue
        if key == "type" and isinstance(item, str):
            converted[key] = item.lower()
        else:
            converted[key] = _to_json_schema(item)

    if nullable and "type" in converted:
        converted["type"] = [converted["type"], "null"]
    return converted


NINEROUTER_RESPONSE_SCHEMA = _to_json_schema(STRUCTURED_RESPONSE_SCHEMA)
NINEROUTER_EXTRACTION_INSTRUCTION = (
    "Extract all compliance-relevant label information from this product photograph. "
    "Return ONLY one JSON object that exactly matches the requested schema. Use the "
    "exact property names, especially top-level 'regions' and region 'bbox_2d'; do "
    "not rename them to 'declarations' or 'bounding_box'.\n"
    f"{json.dumps(NINEROUTER_RESPONSE_SCHEMA, separators=(',', ':'))}"
)


def _normalize_response(parsed: Any) -> Dict[str, Any]:
    """Normalizes known Antigravity aliases without changing observed evidence."""
    if not isinstance(parsed, dict):
        raise ValueError("response root must be a JSON object")

    if "regions" not in parsed and isinstance(parsed.get("declarations"), list):
        parsed["regions"] = parsed.pop("declarations")
    for region in parsed.get("regions") or []:
        if not isinstance(region, dict):
            continue
        if "bbox_2d" not in region and "bounding_box" in region:
            region["bbox_2d"] = region.pop("bounding_box")
        normalized = region.get("normalized_value")
        if normalized is not None and not isinstance(normalized, str):
            region["normalized_value"] = json.dumps(normalized, separators=(",", ":"))

    parsed.setdefault("product_summary", {
        "brand": None,
        "product_name": None,
        "variant": None,
        "category": "unknown",
    })
    parsed.setdefault("extraction_notes", [])
    return parsed


class NineRouterOcrAdapter:
    """OcrEngine implementation using 9Router's OpenAI-compatible endpoint."""

    engine_name = "9router-antigravity"
    engine_version = "v1"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = DEFAULT_NINEROUTER_MODEL,
        timeout_seconds: float = DEFAULT_NINEROUTER_TIMEOUT,
    ):
        configured_url = (
            os.environ.get("NINEROUTER_URL", "").strip()
            if base_url is None
            else base_url
        )
        self.base_url = configured_url.strip().rstrip("/")
        self.api_key = (
            os.environ.get("NINEROUTER_KEY", "").strip()
            if api_key is None
            else api_key.strip()
        )
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def is_available(self) -> bool:
        """Returns whether a 9Router base URL is configured."""
        return bool(self.base_url and self.model)

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
        if not self.base_url:
            raise OcrEngineError("NINEROUTER_URL environment variable is not configured.")
        if not self.model:
            raise OcrEngineError("NINEROUTER_OCR_MODEL is not configured.")

        image_data = base64.b64encode(analysis_bytes).decode("utf-8")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": NINEROUTER_EXTRACTION_INSTRUCTION,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            },
                        },
                    ],
                },
            ],
            "temperature": 0.0,
            "stream": False,
            # 9Router's OpenAI-to-Gemini translator reads the schema from
            # response_format.schema when type is json_object. Its json_schema
            # shape is not converted into Gemini responseSchema for Antigravity.
            "response_format": {
                "type": "json_object",
                "schema": NINEROUTER_RESPONSE_SCHEMA,
            },
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise OcrEngineError(
                f"9Router model '{self.model}' timed out after {self.timeout_seconds:.0f}s."
            ) from exc
        except httpx.HTTPError as exc:
            raise OcrEngineError(f"9Router request failed: {exc}") from exc

        if response.status_code != 200:
            retry_after = response.headers.get("retry-after")
            detail = response.text[:400]
            suffix = f" Retry after {retry_after}s." if retry_after else ""
            raise OcrEngineError(
                f"9Router returned HTTP {response.status_code}: {detail}{suffix}"
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "\n".join(
                    str(part.get("text", ""))
                    for part in content
                    if isinstance(part, dict) and part.get("text")
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty choices[0].message.content")
            parsed_content = content.strip()
            if parsed_content.startswith("```json"):
                parsed_content = parsed_content[7:]
            if parsed_content.startswith("```"):
                parsed_content = parsed_content[3:]
            if parsed_content.endswith("```"):
                parsed_content = parsed_content[:-3]
            parsed = _normalize_response(json.loads(parsed_content.strip()))
            regions = parsed.get("regions")
            if not isinstance(regions, list) or not any(
                isinstance(region, dict)
                and str(region.get("observed_text") or "").strip()
                for region in regions
            ):
                raise ValueError("response contains no usable observed_text regions")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise OcrEngineError(
                f"9Router returned invalid structured OCR JSON: {exc}"
            ) from exc

        slot = GeminiFlashOcrAdapter._parse_response(
            raw_response=json.dumps(parsed),
            role=role,
            image_id=image_id,
            analysis_width=analysis_width,
            analysis_height=analysis_height,
            original_width=original_width,
            original_height=original_height,
            transform=transform,
        )
        logger.info(
            "9Router model '%s' OCR extracted %d regions for panel '%s' (%s)",
            self.model,
            len(slot.lines),
            role.value,
            image_id,
        )
        return slot
