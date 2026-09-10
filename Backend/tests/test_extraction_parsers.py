"""
Tests for Deterministic Extraction Parsers (D1-D6).
Exercises the parsers against statutory formats named in Prototype_A_Workflow.md
and against the six permanent OCR fixtures (ADR-0010).
"""

import json
from datetime import datetime
from pathlib import Path
import pytest

from app.extraction import (
    extract_declarations,
    parse_address_block,
    parse_commodity_dimensions,
    parse_consumer_care,
    parse_date,
    parse_per_piece_entries,
    parse_piece_count,
    parse_price,
    parse_quantity,
    parse_sheet_dimensions,
    parse_usable_sheet_count,
)
from app.normalise import build_normalised_document
from lmpc_schema import (
    CaptureContext,
    CommodityCategory,
    DateForm,
    DateLabel,
    DimensionKind,
    ExtractionMethod,
    ExtractionStatus,
    Field,
    ImportStatus,
    NotFoundReason,
    OcrDocument,
    PackageType,
    PricePrefixForm,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ocr"


def load_fixture(name: str) -> OcrDocument:
    with open(FIXTURES_DIR / name, "r", encoding="utf-8") as f:
        data = json.load(f)
    return OcrDocument.model_validate(data)


def make_capture_context(all_panels_captured: bool = True) -> CaptureContext:
    return CaptureContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        all_panels_captured=all_panels_captured,
        inspector_id="test_inspector",
        captured_at=datetime(2026, 9, 7, 10, 0, 0),
    )


# ---------- D1: Quantity Parser ----------

def test_parse_quantity_simple_gms():
    result = parse_quantity("Net Qty.: 1200 gms")
    assert result is not None
    raw_val, parsed = result
    assert parsed.magnitude == 1200.0
    assert parsed.unit_raw == "gms"
    assert parsed.unit_canonical == "g"
    assert parsed.dimension == DimensionKind.MASS
    assert parsed.symbol_is_prescribed is False  # gms is NOT prescribed SI


def test_parse_quantity_prescribed_g():
    result = parse_quantity("Net Qty.: 250 g")
    assert result is not None
    _, parsed = result
    assert parsed.magnitude == 250.0
    assert parsed.unit_canonical == "g"
    assert parsed.symbol_is_prescribed is True


def test_parse_quantity_kg_decimal():
    result = parse_quantity("Net Weight: 1.2 kg")
    assert result is not None
    _, parsed = result
    assert parsed.magnitude == 1.2
    assert parsed.unit_canonical == "kg"
    assert parsed.dimension == DimensionKind.MASS


def test_parse_quantity_multi_unit():
    result = parse_quantity("4 x 100 g = 400 g")
    assert result is not None
    _, parsed = result
    assert parsed.multi_unit is not None
    assert parsed.multi_unit.count == 4
    assert parsed.multi_unit.each.magnitude == 100.0
    assert parsed.magnitude == 400.0


@pytest.mark.parametrize("text", ["1 U", "1U", "1 unit", "1 Unit"])
def test_parse_quantity_number_variants(text):
    result = parse_quantity(text)
    assert result is not None
    _, parsed = result
    assert parsed.magnitude == 1.0
    assert parsed.dimension == DimensionKind.NUMBER
    assert parsed.symbol_is_prescribed is True


def test_parse_quantity_number_pieces():
    result = parse_quantity("20 pieces")
    assert result is not None
    _, parsed = result
    assert parsed.magnitude == 20.0
    assert parsed.dimension == DimensionKind.NUMBER
    assert parsed.symbol_is_prescribed is True  # 2021 amendment: piece is lawful


def test_parse_quantity_when_packed_qualifier():
    result = parse_quantity("Net Qty: 500 ml (when packed)")
    assert result is not None
    _, parsed = result
    assert parsed.qualifier == "when packed"


def test_parse_quantity_no_match():
    assert parse_quantity("MANUFACTURED BY: ABC Ltd") is None


# ---------- D2: Price Parser ----------

def test_parse_price_mrp_inclusive():
    result = parse_price("MRP Rs. 249.00 incl. of all taxes")
    assert result is not None
    _, parsed = result
    assert parsed.amount == 249.00
    assert parsed.prefix_form == PricePrefixForm.MRP
    assert parsed.inclusive_phrase_present is True


def test_parse_price_maximum_retail_price():
    result = parse_price("Maximum Retail Price Rs. 185.00")
    assert result is not None
    _, parsed = result
    assert parsed.amount == 185.00
    assert parsed.prefix_form == PricePrefixForm.MAXIMUM_RETAIL_PRICE


def test_parse_price_no_inclusive_phrase():
    result = parse_price("MRP Rs. 99.00")
    assert result is not None
    _, parsed = result
    assert parsed.inclusive_phrase_present is False


@pytest.mark.parametrize("text", [
    "M.R.P. Rs. 250.00",
    "M.R.P. 250",
    "M.R.P 250",
    "M. R. P. 250",
    "M. R. P. Rs. 250",
    "M.R.P.: 250",
    "M.R.P.: ₹250",
    "M R P 250",
])
def test_parse_price_mrp_with_dots_and_spaces(text):
    result = parse_price(text)
    assert result is not None
    _, parsed = result
    assert parsed.amount == 250.0
    assert parsed.prefix_form == PricePrefixForm.MRP


# ---------- D3: Date Parser ----------

def test_parse_date_numeric():
    result = parse_date("MFG: 07/2026")
    assert result is not None
    _, parsed = result
    assert parsed.month == 7
    assert parsed.year == 2026
    assert parsed.form == DateForm.NUMERIC
    assert parsed.label == DateLabel.MFG


def test_parse_date_words():
    result = parse_date("Packed on July 2026")
    assert result is not None
    _, parsed = result
    assert parsed.month == 7
    assert parsed.year == 2026
    assert parsed.form == DateForm.WORDS
    assert parsed.label == DateLabel.PKD


def test_parse_date_pkd_dot_format():
    result = parse_date("PKD 07.26")
    assert result is not None
    _, parsed = result
    assert parsed.month == 7
    assert parsed.year == 2026
    assert parsed.label == DateLabel.PKD


def test_parse_date_devanagari():
    result = parse_date("जुलाई 2026")
    assert result is not None
    _, parsed = result
    assert parsed.month == 7
    assert parsed.year == 2026


def test_parse_date_imported():
    result = parse_date("Imported: 09/2026")
    assert result is not None
    _, parsed = result
    assert parsed.label == DateLabel.IMPORTED


@pytest.mark.parametrize("expiry_line", [
    "EXP: 07/2027",
    "EXPIRY: 12/2028",
    "Use By: 08/2027",
    "Best Before: 05/2028",
])
def test_parse_date_excludes_standalone_expiry_and_use_by(expiry_line):
    assert parse_date(expiry_line) is None


def test_parse_date_joint_mfd_and_exp():
    result = parse_date("MFD: 07/2025, EXP: 07/2026")
    assert result is not None
    _, parsed = result
    assert parsed.month == 7
    assert parsed.year == 2025
    assert parsed.label == DateLabel.MFG


# ---------- D4: Address & Consumer Care ----------

@pytest.mark.parametrize("text,expected_pin", [
    ("CleanHome Chemicals Ltd, 42 Industrial Area, Vapi, Gujarat 396195", "396195"),
    ("Mkt. by: Marico Ltd., Kalinga, Santacruz (East), Mumbai-400 098, MH.", "400098"),
    ("SIPCT Industrial Growth Center, Perundurai-638 052, TN.", "638052"),
])
def test_parse_address_block_pin_formats(text, expected_pin):
    result = parse_address_block([text])
    assert result is not None
    _, parsed = result
    assert parsed.pin_code == expected_pin


def test_parse_address_complete():
    lines = ["MANUFACTURED BY: CleanHome Chemicals Ltd, 42 Industrial Area, Vapi, Gujarat 396195"]
    result = parse_address_block(lines)
    assert result is not None
    _, parsed = result
    assert parsed.has_premises_number is True
    assert parsed.has_street is True
    assert parsed.has_state is True
    assert parsed.pin_code == "396195"
    assert parsed.role_marker.value == "MANUFACTURED BY"


def test_parse_address_incomplete_no_pin_no_state():
    lines = ["Packed by: Local Packers, Main Road"]
    result = parse_address_block(lines)
    assert result is not None
    _, parsed = result
    assert parsed.pin_code is None


def test_parse_consumer_care_email_and_phone():
    result = parse_consumer_care("Consumer Care: care@cleanhome.com, Tel: 0260-2451234")
    assert result is not None


def test_parse_consumer_care_no_match():
    assert parse_consumer_care("MANUFACTURED BY: ABC Ltd") is None


# ---------- D5: Dimensions & Count ----------

def test_parse_commodity_dimensions():
    result = parse_commodity_dimensions("220 cm x 240 cm")
    assert result is not None
    raw_val, formatted = result
    assert "220" in formatted
    assert "240" in formatted


def test_parse_commodity_dimensions_size_prefix():
    result = parse_commodity_dimensions("Size: 5 m")
    assert result is not None


def test_parse_piece_count():
    result = parse_piece_count("20 pieces")
    assert result is not None
    _, count = result
    assert count == 20


def test_parse_usable_sheet_count():
    result = parse_usable_sheet_count("100 usable sheets")
    assert result is not None
    _, count = result
    assert count == 100


def test_parse_sheet_dimensions():
    result = parse_sheet_dimensions("Sheet size: 20 cm x 20 cm")
    assert result is not None


def test_parse_per_piece_entries():
    lines = [
        "1 Bed Sheet: 220 cm x 240 cm",
        "2 Pillow Covers: 45 cm x 70 cm",
    ]
    result = parse_per_piece_entries(lines)
    assert result is not None
    _, entries = result
    assert len(entries) == 2


# ---------- D6 + Pipeline: Full DeclarationSet Assembly ----------

def test_pipeline_clean_compliant_pack():
    ocr_doc = load_fixture("clean_compliant_pack.json")
    normalised = build_normalised_document(ocr_doc)
    ctx = make_capture_context(all_panels_captured=True)
    decl_set = extract_declarations(normalised, ocr_doc, ctx)

    assert decl_set.panel_coverage.all_panels_confirmed is True
    assert len(decl_set.declarations) == 14  # all Field enum members present

    qty_decl = next(d for d in decl_set.declarations if d.field == Field.NET_QUANTITY)
    assert qty_decl.status == ExtractionStatus.FOUND


def test_pipeline_unit_violation_1200g():
    ocr_doc = load_fixture("unit_violation_1200g.json")
    normalised = build_normalised_document(ocr_doc)
    ctx = make_capture_context(all_panels_captured=True)
    decl_set = extract_declarations(normalised, ocr_doc, ctx)

    qty_decl = next(d for d in decl_set.declarations if d.field == Field.NET_QUANTITY)
    assert qty_decl.status == ExtractionStatus.FOUND
    assert qty_decl.parsed.magnitude == 1200.0
    assert qty_decl.parsed.unit_canonical == "g"

    price_decl = next(d for d in decl_set.declarations if d.field == Field.RETAIL_SALE_PRICE)
    assert price_decl.status == ExtractionStatus.FOUND
    assert price_decl.parsed.amount == 185.00

    date_decl = next(d for d in decl_set.declarations if d.field == Field.DATE_OF_MANUFACTURE_PACKING_IMPORT)
    assert date_decl.status == ExtractionStatus.FOUND
    assert date_decl.parsed.month == 6
    assert date_decl.parsed.year == 2026

    origin_decl = next(d for d in decl_set.declarations if d.field == Field.COUNTRY_OF_ORIGIN)
    assert origin_decl.status == ExtractionStatus.FOUND


def test_pipeline_missing_mrp():
    ocr_doc = load_fixture("missing_mrp.json")
    normalised = build_normalised_document(ocr_doc)
    ctx = make_capture_context(all_panels_captured=True)
    decl_set = extract_declarations(normalised, ocr_doc, ctx)

    price_decl = next(d for d in decl_set.declarations if d.field == Field.RETAIL_SALE_PRICE)
    assert price_decl.status == ExtractionStatus.NOT_FOUND
    assert price_decl.not_found_reason == NotFoundReason.NO_MATCH_IN_CAPTURED_PANELS


def test_pipeline_panel_not_captured_reason():
    """When all_panels_captured=False, every NOT_FOUND field must be PANEL_NOT_CAPTURED (ADR-0005)."""
    ocr_doc = load_fixture("missing_mrp.json")
    normalised = build_normalised_document(ocr_doc)
    ctx = make_capture_context(all_panels_captured=False)
    decl_set = extract_declarations(normalised, ocr_doc, ctx)

    assert decl_set.panel_coverage.all_panels_confirmed is False
    for decl in decl_set.declarations:
        if decl.status == ExtractionStatus.NOT_FOUND:
            assert decl.not_found_reason == NotFoundReason.PANEL_NOT_CAPTURED


def test_pipeline_textile_per_piece():
    ocr_doc = load_fixture("textile_per_piece.json")
    normalised = build_normalised_document(ocr_doc)
    ctx = make_capture_context(all_panels_captured=True)
    decl_set = extract_declarations(normalised, ocr_doc, ctx)

    piece_decl = next(d for d in decl_set.declarations if d.field == Field.PIECE_COUNT)
    dims_decl = next(d for d in decl_set.declarations if d.field == Field.COMMODITY_DIMENSIONS)
    assert piece_decl.status == ExtractionStatus.FOUND or dims_decl.status == ExtractionStatus.FOUND


def test_pipeline_sheet_product():
    ocr_doc = load_fixture("sheet_product.json")
    normalised = build_normalised_document(ocr_doc)
    ctx = make_capture_context(all_panels_captured=True)
    decl_set = extract_declarations(normalised, ocr_doc, ctx)

    sheet_decl = next(d for d in decl_set.declarations if d.field == Field.USABLE_SHEET_COUNT)
    assert sheet_decl.status == ExtractionStatus.FOUND
    assert sheet_decl.raw_value is not None
