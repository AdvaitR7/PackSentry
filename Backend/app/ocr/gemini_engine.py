"""
Gemini 2.5 Flash OCR and Visual Label Extraction Adapter.

Invokes Google AI Studio Gemini 2.5 Flash via REST API using high-precision
product-label extraction prompting and structured region schema.
Emits standardized Line and ImageSlot structures with normalized coordinates,
flowing seamlessly through downstream deterministic normalisation, extraction,
and statutory rule evaluation.
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

logger = logging.getLogger("packsentry.ocr.gemini")

DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_OCR_MODEL", "gemini-2.5-flash")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

SYSTEM_PROMPT = """You are a high-precision visual product-label extraction system.

The uploaded images are photographs of a physical retail product taken using a mobile phone.
There may be multiple images showing different sides of the SAME product.

Your job is to extract visible product-label information for downstream regulatory/compliance analysis.

IMPORTANT RULES:

1. Extract only information actually visible in the images.
2. Do NOT invent, infer, complete, correct, or autocorrect missing text.
3. Preserve the literal visible text in "observed_text", including spelling, numbers, units and punctuation.
4. "normalized_value" may contain a standardized interpretation only when it is unambiguous.
5. If text is partially unreadable, preserve what is readable and mark legibility accordingly.
6. Never silently convert uncertain digits. For example, if "500" could be "5OO", preserve the visible text.
7. Multiple images may contain duplicate declarations. Do not duplicate identical information unnecessarily.
8. Extract compliance-relevant declarations including, when visible:
   - brand
   - product name
   - variant
   - manufactured_by (separate declaration of name and address of manufacturer)
   - marketed_by (separate declaration of name and address of marketer or packer)
   - imported_by (name and address of importer; optional for domestic goods)
   - ingredients / composition
   - allergens
   - nutrition information
   - net quantity / weight / volume
   - MRP / retail price
   - batch / lot number
   - manufacture / packing date
   - expiry / use-by / best-before
   - country of origin
   - warnings and cautions
   - directions for use
   - storage instructions
   - marketing/product claims
   - regulatory registrations/licence numbers
   - customer-care information
   - cosmetic ingredient/composition declarations
   - barcode numbers
   - certification/regulatory marks
   - any other potentially compliance-relevant printed text

9. For every extracted region provide a bounding box in:
   [ymin, xmin, ymax, xmax]

   Coordinates must be integers normalized from 0 to 1000 relative to the SOURCE IMAGE.

   Top-left = [0,0]
   Bottom-right = [1000,1000]

10. source_image_index is zero-based according to the order images were provided.

11. Bounding boxes should surround the complete relevant text region/declaration, not individual characters.
12. If an ingredients paragraph occupies one continuous region, return one ingredients region.
13. If the same type of information appears in disconnected regions, return separate regions.
14. Handling Stamped, Inkjet, or Misaligned Label Information:
    - Variable information such as MRP, manufacturing/packing date, and expiry/use-by date is frequently stamped, coded with inkjet or dot-matrix printers, or printed in a separate dedicated window/flap, often displaced or not aligned with the pre-printed static label headings.
    - If price-like information (e.g. "Rs. 250", "₹250", "250.00", "250/-") is visible, carefully reason about its visual proximity and relationship to pre-printed "MRP" or "M.R.P." headings. Categorize this under field_type "mrp_price" and associate the visible label (e.g. "MRP" or "M.R.P.").
    - If multiple dates are stamped or printed without clear individual headings:
      * Use chronological reasoning: the use-by / expiry date is ALWAYS chronologically ahead of (later than) the manufacture / packing date.
      * Assign the earlier chronological date to field_type "manufacture_date" (or "packing_date").
      * Assign the later chronological date to field_type "expiry_date" (or "best_before").
      * If an explicit heading is visible (e.g. "MFD", "PKD", "EXP", "USE BY", "BEST BEFORE"), associate it in "label".
    - Do not discard or ignore stamped text simply because it is misaligned, dot-matrix, or printed in a different orientation.

15. Do not perform the final legal compliance decision. Only extract observable evidence."""


STRUCTURED_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "product_summary": {
            "type": "OBJECT",
            "properties": {
                "brand": {
                    "type": "STRING",
                    "description": "Brand name exactly as visibly printed.",
                    "nullable": True,
                },
                "product_name": {
                    "type": "STRING",
                    "description": "Product name exactly as visibly printed.",
                    "nullable": True,
                },
                "variant": {
                    "type": "STRING",
                    "description": "Visible variant, flavour, formulation, shade or subtype.",
                    "nullable": True,
                },
                "category": {
                    "type": "STRING",
                    "enum": [
                        "food",
                        "cosmetic",
                        "personal_care",
                        "agricultural_product",
                        "household_product",
                        "supplement",
                        "other",
                        "unknown",
                    ],
                },
                "manufactured_by": {
                    "type": "STRING",
                    "description": "Name and complete address of the manufacturer as visibly printed, or null if absent.",
                    "nullable": True,
                },
                "marketed_by": {
                    "type": "STRING",
                    "description": "Name and complete address of the marketer or packer as visibly printed, or null if absent.",
                    "nullable": True,
                },
                "imported_by": {
                    "type": "STRING",
                    "description": "Name and complete address of the importer as visibly printed (optional, null for domestic goods).",
                    "nullable": True,
                },
            },
            "required": ["brand", "product_name", "variant", "category"],
        },
        "regions": {
            "type": "ARRAY",
            "description": "Compliance-relevant visible text regions across all supplied images.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "field_type": {
                        "type": "STRING",
                        "enum": [
                            "brand",
                            "product_name",
                            "variant",
                            "product_description",
                            "ingredients",
                            "composition",
                            "allergen_statement",
                            "nutrition_panel",
                            "net_quantity",
                            "mrp_price",
                            "batch_lot",
                            "manufacture_date",
                            "packing_date",
                            "expiry_date",
                            "best_before",
                            "manufacturer",
                            "packer",
                            "importer",
                            "marketer",
                            "country_of_origin",
                            "regulatory_license",
                            "registration_number",
                            "warnings_cautions",
                            "directions_for_use",
                            "storage_instructions",
                            "product_claim",
                            "customer_care",
                            "barcode_number",
                            "certification_mark",
                            "other",
                        ],
                    },
                    "label": {
                        "type": "STRING",
                        "description": "Printed heading such as INGREDIENTS, MRP, NET WT, CAUTION, etc.",
                        "nullable": True,
                    },
                    "observed_text": {
                        "type": "STRING",
                        "description": "Literal transcription. Do not silently correct spelling, numbers, units or punctuation.",
                    },
                    "normalized_value": {
                        "type": "STRING",
                        "description": "Normalized interpretation only when unambiguous.",
                        "nullable": True,
                    },
                    "source_image_index": {
                        "type": "INTEGER",
                        "description": "Zero-based index of the image containing this text.",
                    },
                    "bbox_2d": {
                        "type": "ARRAY",
                        "description": "Exactly four integers: [ymin, xmin, ymax, xmax], normalized from 0 to 1000 relative to the source image.",
                        "items": {"type": "INTEGER"},
                    },
                    "legibility": {
                        "type": "STRING",
                        "enum": ["clear", "partially_readable", "uncertain"],
                    },
                },
                "required": [
                    "field_type",
                    "label",
                    "observed_text",
                    "normalized_value",
                    "source_image_index",
                    "bbox_2d",
                    "legibility",
                ],
            },
        },
        "extraction_notes": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
    },
    "required": [
        "product_summary",
        "regions",
        "extraction_notes",
    ],
}


class GeminiFlashOcrAdapter:
    """OcrEngine implementation using Gemini 2.5 Flash via Google AI Studio REST API."""

    engine_name = "gemini-2.5-flash"
    engine_version = "2.5"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GEMINI_MODEL,
        timeout_seconds: float = 18.0,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def is_available(self) -> bool:
        """Checks if the Gemini API key is configured and non-empty."""
        return bool(self.api_key)

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
        Extracts all visible text regions verbatim using Gemini 2.5 Flash.
        Maps region bounding boxes back to original and normalized coordinate spaces.
        """
        if not self.api_key:
            raise OcrEngineError("GEMINI_API_KEY environment variable is not configured.")

        b64_image = base64.b64encode(analysis_bytes).decode("utf-8")

        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "parts": [
                        {"text": "Extract all compliance-relevant label information from this product photograph."},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": b64_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
                "responseSchema": STRUCTURED_RESPONSE_SCHEMA,
            },
        }

        url = f"{GEMINI_API_ENDPOINT}/{self.model}:generateContent?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise OcrEngineError(
                        f"Gemini API returned HTTP {res.status_code}: {res.text[:400]}"
                    )
                data = res.json()
                raw_response = self._extract_candidate_text(data)
        except OcrEngineError:
            raise
        except Exception as exc:
            raise OcrEngineError(f"Gemini 2.5 Flash OCR inference failed: {exc}") from exc

        slot = self._parse_response(
            raw_response=raw_response,
            role=role,
            image_id=image_id,
            analysis_width=analysis_width,
            analysis_height=analysis_height,
            original_width=original_width,
            original_height=original_height,
            transform=transform,
        )
        logger.info(
            "Gemini 2.5 Flash OCR extracted %d regions for panel '%s' (%s)",
            len(slot.lines),
            role.value,
            image_id,
        )
        return slot

    def _extract_candidate_text(self, data: Dict[str, Any]) -> str:
        """Extracts generated text string from Gemini API response candidates."""
        candidates = data.get("candidates", [])
        if not candidates:
            raise OcrEngineError("Gemini API returned no candidates in response.")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p.get("text", "") for p in parts if "text" in p]
        return "\n".join(text_parts).strip()

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
        """Parses structured JSON response into standardized ImageSlot lines and mapped polygons."""
        extracted_entries: List[Dict[str, Any]] = []

        try:
            parsed = json.loads(raw_response)
            if isinstance(parsed, dict):
                regions_data = parsed.get("regions")
                if isinstance(regions_data, list) and regions_data:
                    for item in regions_data:
                        if not isinstance(item, dict):
                            continue
                        observed = str(item.get("observed_text") or "").strip()
                        if not observed:
                            continue
                        label = str(item.get("label") or "").strip()
                        field_type = str(item.get("field_type") or "").strip()

                        # Preserve observed evidence. A model-assigned field type is not
                        # text printed on the package and must never be injected into raw_text.
                        full_text = (
                            f"{label}: {observed}"
                            if label and label.lower() not in observed.lower()
                            else observed
                        )

                        extracted_entries.append({
                            "text": full_text,
                            "box_2d": item.get("bbox_2d") or [0, 0, 1000, 1000],
                            "field_type": field_type,
                        })

                    # If separate commercial entity fields were extracted in product_summary,
                    # ensure they are present for downstream address/identity extraction.
                    summary = parsed.get("product_summary") or {}
                    existing_texts = {e["text"].lower() for e in extracted_entries}
                    for field_key, field_role in [
                        ("manufactured_by", "manufacturer"),
                        ("marketed_by", "packer"),
                        ("imported_by", "importer"),
                    ]:
                        val = summary.get(field_key)
                        if isinstance(val, str) and val.strip() and val.strip().lower() not in existing_texts:
                            extracted_entries.append({
                                "text": val.strip(),
                                "box_2d": [0, 0, 1000, 1000],
                                "field_type": field_role,
                            })
                else:
                    # Fallback for alternative line structure
                    lines_data = (
                        parsed.get("lines")
                        or parsed.get("text_lines")
                        or parsed.get("declarations")
                    )
                    if isinstance(lines_data, list):
                        for item in lines_data:
                            if isinstance(item, dict) and (item.get("text") or item.get("raw_text")):
                                extracted_entries.append({
                                    "text": str(item.get("text") or item.get("raw_text")).strip(),
                                    "box_2d": item.get("box_2d") or item.get("box") or [0, 0, 1000, 1000],
                                })
                            elif isinstance(item, str) and item.strip():
                                extracted_entries.append({
                                    "text": item.strip(),
                                    "box_2d": [0, 0, 1000, 1000],
                                })
                    elif not lines_data:
                        for k, v in parsed.items():
                            if isinstance(v, str) and v.strip():
                                extracted_entries.append({
                                    "text": f"{k}: {v}",
                                    "box_2d": [0, 0, 1000, 1000],
                                })
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and (item.get("text") or item.get("raw_text") or item.get("observed_text")):
                        txt = str(item.get("observed_text") or item.get("text") or item.get("raw_text")).strip()
                        extracted_entries.append({
                            "text": txt,
                            "box_2d": item.get("bbox_2d") or item.get("box_2d") or [0, 0, 1000, 1000],
                        })
                    elif isinstance(item, str) and item.strip():
                        extracted_entries.append({
                            "text": item.strip(),
                            "box_2d": [0, 0, 1000, 1000],
                        })
        except Exception:
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

            px_x1 = max(0.0, min(float(analysis_width), (xmin / 1000.0) * analysis_width))
            px_y1 = max(0.0, min(float(analysis_height), (ymin / 1000.0) * analysis_height))
            px_x2 = max(px_x1, min(float(analysis_width), (xmax / 1000.0) * analysis_width))
            px_y2 = max(px_y1, min(float(analysis_height), (ymax / 1000.0) * analysis_height))

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

            # Build constituent words from line
            words: List[Word] = []
            tokens = text.split()
            if tokens:
                step_w = (px_x2 - px_x1) / max(len(tokens), 1)
                for w_idx, token in enumerate(tokens):
                    w_x1 = px_x1 + w_idx * step_w
                    w_x2 = w_x1 + step_w
                    w_poly = [[w_x1, px_y1], [w_x2, px_y1], [w_x2, px_y2], [w_x1, px_y2]]
                    w_orig = CoordinateMapper.analysis_to_original(
                        w_poly, transform, original_width, original_height
                    )
                    w_norm = CoordinateMapper.original_to_normalized(
                        w_orig, original_width, original_height
                    )
                    words.append(
                        Word(
                            raw_text=token,
                            confidence=0.95,
                            polygon_analysis=w_poly,
                            polygon_original=w_orig,
                            polygon_normalized=w_norm,
                        )
                    )

            lines.append(
                Line(
                    line_id=f"{image_id}:l{idx+1:03d}",
                    raw_text=text,
                    confidence=0.95,
                    polygon_analysis=poly_analysis,
                    polygon_original=poly_orig,
                    polygon_normalized=poly_norm,
                    words=words,
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
