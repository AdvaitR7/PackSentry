"""
Tests for Normalisation and Alias Matching (C3).
Verifies:
- Unicode NFKC, lowercasing (Latin only), whitespace collapsing.
- Currency and multiplication sign unification.
- Trailing punctuation stripping from tokens.
- raw_text is NEVER altered (ADR-0002 invariant).
- Longest-alias-first matching against the real aliases.yaml.
"""

import pytest

from app.normalise import (
    build_normalised_document,
    load_alias_table,
    match_aliases,
    normalise_text,
)
from lmpc_schema import ImageSlot, Line, OcrDocument, PanelRole, Transform


def test_normalise_preserves_unit_notation():
    """CRITICAL ADR-0002 invariant: 'gms' must NOT be corrected to 'g'."""
    raw = "Net Qty.: 1200 gms"
    norm = normalise_text(raw)
    assert "gms" in norm
    assert norm == "net qty 1200 gms"


def test_normalise_currency_unification():
    assert "rs 249" in normalise_text("MRP Rs. 249.00")
    assert "rs 249" in normalise_text("MRP ₹249.00")
    assert "rs 249" in normalise_text("MRP INR 249.00")


def test_normalise_multiplication_unification():
    result = normalise_text("4 X 100 g = 400 g")
    assert " x " in result
    result2 = normalise_text("90cm × 200cm")
    assert "x" in result2


def test_normalise_whitespace_collapse():
    result = normalise_text("Net    Qty:    1200   g")
    assert "  " not in result


def test_normalise_devanagari_untouched():
    raw = "शुद्ध मात्रा: 500 ग्राम"
    result = normalise_text(raw)
    assert "शुद्ध" in result
    assert "मात्रा" in result


def test_normalise_nfkc_unicode():
    # Fullwidth characters should normalize to standard forms
    result = normalise_text("Ｎet Ｑty")
    assert "net" in result.lower() or "n" in result


def test_raw_text_never_mutated_in_line():
    """Simulates the OcrDocument -> NormalisedDocument pipeline preserving raw_text exactly."""
    doc = OcrDocument(
        ocr_engine="test",
        ocr_version="1.0",
        images=[
            ImageSlot(
                image_id="img1",
                role=PanelRole.PDP,
                analysis_width=1200,
                analysis_height=1600,
                original_width=3000,
                original_height=4000,
                transform=Transform(),
                lines=[
                    Line(
                        line_id="img1:l001",
                        raw_text="Net Qty.: 1200 gms",
                        confidence=0.95,
                        polygon_normalized=[[0.1, 0.1], [0.5, 0.1], [0.5, 0.2], [0.1, 0.2]],
                    )
                ],
            )
        ],
    )

    normalised = build_normalised_document(doc)
    assert len(normalised.lines) == 1
    line = normalised.lines[0]
    # raw_text must be byte-for-byte identical to OCR output
    assert line.raw_text == "Net Qty.: 1200 gms"
    # normalized_text must differ (lowercased, punctuation stripped)
    assert line.normalized_text != line.raw_text
    assert "gms" in line.normalized_text  # unit notation preserved, not corrected


def test_alias_matching_longest_first():
    """'net quantity' should win over 'net' style partial matches."""
    entries = load_alias_table()
    assert len(entries) > 0

    matched = match_aliases("net quantity 1200 gms", entries)
    assert "NET_QUANTITY" in matched


def test_alias_matching_mrp():
    entries = load_alias_table()
    matched = match_aliases("mrp rs 185 incl of all taxes", entries)
    assert "RETAIL_SALE_PRICE" in matched


def test_alias_matching_manufactured_by():
    entries = load_alias_table()
    matched = match_aliases("manufactured by cleanhome chemicals ltd", entries)
    assert "MANUFACTURER_NAME_ADDRESS" in matched


def test_alias_matching_no_match():
    entries = load_alias_table()
    matched = match_aliases("some random unrelated sentence about nothing", entries)
    assert matched == []


def test_alias_table_has_all_required_fields():
    """Ensures every Field enum referenced by rule engine has at least one alias entry."""
    entries = load_alias_table()
    field_names = {field for _, field in entries}
    required = {
        "NET_QUANTITY",
        "RETAIL_SALE_PRICE",
        "DATE_OF_MANUFACTURE_PACKING_IMPORT",
        "MANUFACTURER_NAME_ADDRESS",
        "COUNTRY_OF_ORIGIN",
        "CONSUMER_CARE",
        "COMMON_GENERIC_NAME",
        "COMMODITY_DIMENSIONS",
        "PIECE_COUNT",
        "USABLE_SHEET_COUNT",
    }
    missing = required - field_names
    assert not missing, f"Missing alias entries for fields: {missing}"
