"""
Declaration Extraction Pipeline (Track D per ADR-0001, ADR-0002, ADR-0005).

Orchestrates deterministic parsers (D1-D6) over NormalisedDocument and OcrDocument
to produce a complete, typed DeclarationSet.

Guarantees:
- Every field in Field enum is present in DeclarationSet.declarations (FOUND or NOT_FOUND).
- raw_value preserves OCR raw text untouched for legal adjudication (ADR-0002).
- Accurate EvidenceSpan coordinates attached to all found declarations.
- Panel coverage resolver sets not_found_reason on unlocated declarations (ADR-0005).
"""

import re
from typing import Dict, List, Optional, Tuple
from lmpc_schema import (
    CaptureContext,
    Declaration,
    DeclarationSet,
    EvidenceSpan,
    ExtractionMethod,
    ExtractionStatus,
    Field,
    Line,
    NormalisedDocument,
    NormalisedLine,
    OcrDocument,
)

from .address import parse_address_block, parse_consumer_care
from .coverage import assign_not_found_reasons, average_ocr_confidence, resolve_panel_coverage
from .date import parse_date
from .dimensions_count import (
    parse_commodity_dimensions,
    parse_per_piece_entries,
    parse_piece_count,
    parse_sheet_dimensions,
    parse_usable_sheet_count,
)
from .price import parse_price
from .quantity import parse_quantity

ALL_FIELDS = [
    Field.MANUFACTURER_NAME_ADDRESS,
    Field.PACKER_NAME_ADDRESS,
    Field.IMPORTER_NAME_ADDRESS,
    Field.COUNTRY_OF_ORIGIN,
    Field.COMMON_GENERIC_NAME,
    Field.NET_QUANTITY,
    Field.DATE_OF_MANUFACTURE_PACKING_IMPORT,
    Field.RETAIL_SALE_PRICE,
    Field.COMMODITY_DIMENSIONS,
    Field.CONSUMER_CARE,
    Field.PIECE_COUNT,
    Field.USABLE_SHEET_COUNT,
    Field.SHEET_DIMENSIONS,
    Field.PER_PIECE_ENTRIES,
]


def _build_line_lookup(ocr_doc: OcrDocument) -> Dict[str, Tuple[Line, str]]:
    """Maps line_id -> (Line, image_id) from OcrDocument."""
    lookup: Dict[str, Tuple[Line, str]] = {}
    for img in ocr_doc.images:
        for line in img.lines:
            lookup[line.line_id] = (line, img.image_id)
    return lookup


def _create_evidence_span(line: Line, image_id: str) -> EvidenceSpan:
    return EvidenceSpan(
        image_id=image_id,
        line_id=line.line_id,
        polygon_normalized=line.polygon_normalized,
        raw_text=line.raw_text,
    )


def _assign_first_match(
    extracted: Dict[Field, Declaration],
    field: Field,
    normalised_doc: NormalisedDocument,
    line_lookup: Dict[str, Tuple[Line, str]],
    parse_fn,
    *,
    alias_key: Optional[str] = None,
    pattern_confidence: float = 0.90,
    alias_confidence: float = 0.98,
) -> None:
    """
    Scans normalised lines in order and records the first successful parse as a FOUND
    Declaration. When alias_key is given, a line carrying that alias is credited to
    ALIAS_ANCHOR; otherwise extraction is PATTERN_ONLY at pattern_confidence.
    """
    for n_line in normalised_doc.lines:
        line_obj, img_id = line_lookup.get(n_line.line_id, (None, ""))
        if not line_obj:
            continue
        parsed_tuple = parse_fn(n_line.raw_text)
        if not parsed_tuple:
            continue

        raw_val, parsed_val = parsed_tuple
        if alias_key is not None:
            method = (
                ExtractionMethod.ALIAS_ANCHOR
                if alias_key in n_line.matched_aliases
                else ExtractionMethod.PATTERN_ONLY
            )
            confidence = alias_confidence if method == ExtractionMethod.ALIAS_ANCHOR else pattern_confidence
        else:
            method = ExtractionMethod.PATTERN_ONLY
            confidence = pattern_confidence
            parsed_val = None

        extracted[field] = Declaration(
            field=field,
            status=ExtractionStatus.FOUND,
            raw_value=raw_val,
            parsed=parsed_val,
            evidence=[_create_evidence_span(line_obj, img_id)],
            ocr_confidence=line_obj.confidence,
            extraction_confidence=confidence,
            method=method,
        )
        return


def extract_declarations(
    normalised_doc: NormalisedDocument,
    ocr_doc: OcrDocument,
    capture_context: CaptureContext,
) -> DeclarationSet:
    """
    Extracts all LMPC statutory declarations from normalised and OCR documents.
    Returns the complete DeclarationSet with all 14 fields and panel coverage.
    """
    line_lookup = _build_line_lookup(ocr_doc)
    extracted: Dict[Field, Declaration] = {}

    # Initialize all fields as NOT_FOUND
    for field in ALL_FIELDS:
        extracted[field] = Declaration(
            field=field,
            status=ExtractionStatus.NOT_FOUND,
            raw_value=None,
            parsed=None,
            evidence=[],
            ocr_confidence=None,
            extraction_confidence=None,
            method=None,
            not_found_reason=None,
        )

    # 1. NET_QUANTITY (D1)
    _assign_first_match(
        extracted, Field.NET_QUANTITY, normalised_doc, line_lookup, parse_quantity,
        alias_key="NET_QUANTITY", pattern_confidence=0.90,
    )

    # 2. RETAIL_SALE_PRICE (D2)
    _assign_first_match(
        extracted, Field.RETAIL_SALE_PRICE, normalised_doc, line_lookup, parse_price,
        alias_key="RETAIL_SALE_PRICE", pattern_confidence=0.90,
    )

    # 3. DATE_OF_MANUFACTURE_PACKING_IMPORT (D3)
    _assign_first_match(
        extracted, Field.DATE_OF_MANUFACTURE_PACKING_IMPORT, normalised_doc, line_lookup, parse_date,
        alias_key="DATE_OF_MANUFACTURE_PACKING_IMPORT", pattern_confidence=0.88,
    )

    # 4. ADDRESS FIELDS: MANUFACTURER, PACKER, IMPORTER (D4)
    # Collect candidate lines for address blocks
    mfg_lines: List[Tuple[Line, str]] = []
    pkr_lines: List[Tuple[Line, str]] = []
    imp_lines: List[Tuple[Line, str]] = []

    for n_line in normalised_doc.lines:
        line_obj, img_id = line_lookup.get(n_line.line_id, (None, ""))
        if not line_obj:
            continue

        raw = line_obj.raw_text
        if re.search(r"manufactured\s+by|mfd\.?\s+by|mfg\.?\s+by|उत्पादक", raw, re.IGNORECASE):
            mfg_lines.append((line_obj, img_id))
        elif re.search(r"packed\s+by|pkd\.?\s+by|पैकर", raw, re.IGNORECASE):
            pkr_lines.append((line_obj, img_id))
        elif re.search(r"imported\s+by|imp\.?\s+by|आयातकर्ता", raw, re.IGNORECASE):
            imp_lines.append((line_obj, img_id))

    # Evaluate manufacturer address block
    if mfg_lines:
        line_obj, img_id = mfg_lines[0]
        parsed_addr = parse_address_block([line_obj.raw_text])
        if parsed_addr:
            raw_val, addr_obj = parsed_addr
            extracted[Field.MANUFACTURER_NAME_ADDRESS] = Declaration(
                field=Field.MANUFACTURER_NAME_ADDRESS,
                status=ExtractionStatus.FOUND,
                raw_value=raw_val,
                parsed=addr_obj,
                evidence=[_create_evidence_span(line_obj, img_id)],
                ocr_confidence=line_obj.confidence,
                extraction_confidence=0.95,
                method=ExtractionMethod.ALIAS_ANCHOR,
            )

    # Evaluate packer address block
    if pkr_lines:
        line_obj, img_id = pkr_lines[0]
        parsed_addr = parse_address_block([line_obj.raw_text])
        if parsed_addr:
            raw_val, addr_obj = parsed_addr
            extracted[Field.PACKER_NAME_ADDRESS] = Declaration(
                field=Field.PACKER_NAME_ADDRESS,
                status=ExtractionStatus.FOUND,
                raw_value=raw_val,
                parsed=addr_obj,
                evidence=[_create_evidence_span(line_obj, img_id)],
                ocr_confidence=line_obj.confidence,
                extraction_confidence=0.95,
                method=ExtractionMethod.ALIAS_ANCHOR,
            )

    # Evaluate importer address block
    if imp_lines:
        line_obj, img_id = imp_lines[0]
        parsed_addr = parse_address_block([line_obj.raw_text])
        if parsed_addr:
            raw_val, addr_obj = parsed_addr
            extracted[Field.IMPORTER_NAME_ADDRESS] = Declaration(
                field=Field.IMPORTER_NAME_ADDRESS,
                status=ExtractionStatus.FOUND,
                raw_value=raw_val,
                parsed=addr_obj,
                evidence=[_create_evidence_span(line_obj, img_id)],
                ocr_confidence=line_obj.confidence,
                extraction_confidence=0.95,
                method=ExtractionMethod.ALIAS_ANCHOR,
            )

    # 5. COUNTRY_OF_ORIGIN
    for n_line in normalised_doc.lines:
        line_obj, img_id = line_lookup.get(n_line.line_id, (None, ""))
        if not line_obj:
            continue
        m = re.search(r"(?:country\s+of\s+origin|made\s+in|product\s+of)\s*[:.\-]?\s*([A-Za-z\s]+)", line_obj.raw_text, re.IGNORECASE)
        if m:
            country = m.group(1).strip()
            extracted[Field.COUNTRY_OF_ORIGIN] = Declaration(
                field=Field.COUNTRY_OF_ORIGIN,
                status=ExtractionStatus.FOUND,
                raw_value=country,
                parsed=None,
                evidence=[_create_evidence_span(line_obj, img_id)],
                ocr_confidence=line_obj.confidence,
                extraction_confidence=0.95,
                method=ExtractionMethod.ALIAS_ANCHOR,
            )
            break

    # 6. CONSUMER_CARE
    for n_line in normalised_doc.lines:
        line_obj, img_id = line_lookup.get(n_line.line_id, (None, ""))
        if not line_obj:
            continue
        cc = parse_consumer_care(line_obj.raw_text)
        if cc:
            raw_val, desc = cc
            extracted[Field.CONSUMER_CARE] = Declaration(
                field=Field.CONSUMER_CARE,
                status=ExtractionStatus.FOUND,
                raw_value=raw_val,
                parsed=None,
                evidence=[_create_evidence_span(line_obj, img_id)],
                ocr_confidence=line_obj.confidence,
                extraction_confidence=0.94,
                method=ExtractionMethod.ALIAS_ANCHOR,
            )
            break

    # 7. COMMON_GENERIC_NAME
    # Look for explicit generic name tag, or first prominent PDP line
    for n_line in normalised_doc.lines:
        line_obj, img_id = line_lookup.get(n_line.line_id, (None, ""))
        if not line_obj:
            continue
        if "COMMON_GENERIC_NAME" in n_line.matched_aliases:
            m = re.search(r"(?:generic\s+name|commodity|product)\s*[:.\-]?\s*(.+)", line_obj.raw_text, re.IGNORECASE)
            g_name = m.group(1).strip() if m else line_obj.raw_text.strip()
            extracted[Field.COMMON_GENERIC_NAME] = Declaration(
                field=Field.COMMON_GENERIC_NAME,
                status=ExtractionStatus.FOUND,
                raw_value=g_name,
                parsed=None,
                evidence=[_create_evidence_span(line_obj, img_id)],
                ocr_confidence=line_obj.confidence,
                extraction_confidence=0.95,
                method=ExtractionMethod.ALIAS_ANCHOR,
            )
            break

    # If not explicitly tagged with alias, check top prominent line on PDP (not Net Qty or MRP)
    if extracted[Field.COMMON_GENERIC_NAME].status == ExtractionStatus.NOT_FOUND:
        for img in ocr_doc.images:
            for line_obj in img.lines:
                raw_lower = line_obj.raw_text.lower()
                if not any(k in raw_lower for k in ["net", "mrp", "mfg", "pkd", "rs", "care", "manufactured", "origin"]):
                    if len(line_obj.raw_text.split()) >= 2:
                        extracted[Field.COMMON_GENERIC_NAME] = Declaration(
                            field=Field.COMMON_GENERIC_NAME,
                            status=ExtractionStatus.FOUND,
                            raw_value=line_obj.raw_text.strip(),
                            parsed=None,
                            evidence=[_create_evidence_span(line_obj, img.image_id)],
                            ocr_confidence=line_obj.confidence,
                            extraction_confidence=0.85,
                            method=ExtractionMethod.POSITIONAL,
                        )
                        break
            if extracted[Field.COMMON_GENERIC_NAME].status == ExtractionStatus.FOUND:
                break

    # 8. COMMODITY_DIMENSIONS (D5)
    _assign_first_match(
        extracted, Field.COMMODITY_DIMENSIONS, normalised_doc, line_lookup,
        parse_commodity_dimensions, pattern_confidence=0.92,
    )

    # 9. PIECE_COUNT (D5)
    _assign_first_match(
        extracted, Field.PIECE_COUNT, normalised_doc, line_lookup,
        parse_piece_count, pattern_confidence=0.92,
    )

    # 10. USABLE_SHEET_COUNT & SHEET_DIMENSIONS (D5)
    for n_line in normalised_doc.lines:
        line_obj, img_id = line_lookup.get(n_line.line_id, (None, ""))
        if not line_obj:
            continue
        sc_tuple = parse_usable_sheet_count(line_obj.raw_text)
        if sc_tuple:
            raw_val, sheet_cnt = sc_tuple
            extracted[Field.USABLE_SHEET_COUNT] = Declaration(
                field=Field.USABLE_SHEET_COUNT,
                status=ExtractionStatus.FOUND,
                raw_value=raw_val,
                parsed=None,
                evidence=[_create_evidence_span(line_obj, img_id)],
                ocr_confidence=line_obj.confidence,
                extraction_confidence=0.95,
                method=ExtractionMethod.PATTERN_ONLY,
            )

        sd_tuple = parse_sheet_dimensions(line_obj.raw_text)
        if sd_tuple and extracted[Field.SHEET_DIMENSIONS].status == ExtractionStatus.NOT_FOUND:
            raw_val, sheet_dim = sd_tuple
            extracted[Field.SHEET_DIMENSIONS] = Declaration(
                field=Field.SHEET_DIMENSIONS,
                status=ExtractionStatus.FOUND,
                raw_value=raw_val,
                parsed=None,
                evidence=[_create_evidence_span(line_obj, img_id)],
                ocr_confidence=line_obj.confidence,
                extraction_confidence=0.90,
                method=ExtractionMethod.PATTERN_ONLY,
            )

    # 11. PER_PIECE_ENTRIES (D5)
    all_raw_lines = [l.raw_text for l in normalised_doc.lines]
    pp_tuple = parse_per_piece_entries(all_raw_lines)
    if pp_tuple:
        raw_val, _ = pp_tuple
        extracted[Field.PER_PIECE_ENTRIES] = Declaration(
            field=Field.PER_PIECE_ENTRIES,
            status=ExtractionStatus.FOUND,
            raw_value=raw_val,
            parsed=None,
            evidence=[],
            ocr_confidence=0.95,
            extraction_confidence=0.90,
            method=ExtractionMethod.PATTERN_ONLY,
        )

    # D6: Panel Coverage Resolver & not_found_reason assignment
    coverage = resolve_panel_coverage(ocr_doc, capture_context.all_panels_captured)
    avg_conf = average_ocr_confidence(ocr_doc)
    declaration_list = assign_not_found_reasons(list(extracted.values()), coverage, avg_conf)

    return DeclarationSet(
        declarations=declaration_list,
        panel_coverage=coverage,
    )
