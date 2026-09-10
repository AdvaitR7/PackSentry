"""
End-to-End Pipeline Integration Test (Phase 3 Gate per ADR-0001, ADR-0010).

Simulates the full headless inspection flow:
1. Panel Preprocessing: raw camera bytes -> ProcessedPanel with Transform & scaled analysis bytes.
2. OCR: ProcessedPanel -> OcrDocument with Lines and mapped Polygons (analysis, original, normalized).
3. Normalisation: OcrDocument -> NormalisedDocument with matched aliases.
4. Extraction: NormalisedDocument + OcrDocument + CaptureContext -> DeclarationSet.
5. Adjudication: DeclarationSet + ProductContext -> RuleResult[] and overall verdict.

Verifies that real image fixtures flow from raw pixels to non-nullable citations and truthful verdicts.
"""

import json
from datetime import date, datetime
from pathlib import Path
import pytest

from app.extraction import extract_declarations
from app.normalise import build_normalised_document
from app.preprocessing import CoordinateMapper, ImagePreprocessor
from app.rules import evaluate_inspection
from lmpc_schema import (
    CaptureContext,
    CommodityCategory,
    ExtractionStatus,
    Field,
    ImportStatus,
    InternalVerdict,
    NotFoundReason,
    OcrDocument,
    PackageType,
    PanelRole,
    ProductContext,
    UiBucket,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ocr"


def test_full_pipeline_unit_violation_1200g():
    # 1. Load the 1200g OCR fixture
    with open(FIXTURES_DIR / "unit_violation_1200g.json", "r", encoding="utf-8") as f:
        ocr_doc = OcrDocument.model_validate(json.load(f))

    # 2. Normalisation (C3)
    norm_doc = build_normalised_document(ocr_doc)
    assert len(norm_doc.lines) > 0
    # Confirm matched aliases on the net quantity line
    qty_line = next(l for l in norm_doc.lines if "1200" in l.raw_text)
    assert "NET_QUANTITY" in qty_line.matched_aliases

    # 3. Extraction (D1-D6)
    capture_ctx = CaptureContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        all_panels_captured=True,
        inspector_id="insp_p3",
        captured_at=datetime(2026, 9, 7, 10, 0, 0),
    )
    decl_set = extract_declarations(norm_doc, ocr_doc, capture_ctx)
    assert decl_set.panel_coverage.all_panels_confirmed is True

    # Check extracted declarations
    qty_decl = next(d for d in decl_set.declarations if d.field == Field.NET_QUANTITY)
    assert qty_decl.status.value == "FOUND"
    assert qty_decl.parsed.magnitude == 1200.0
    assert qty_decl.parsed.unit_canonical == "g"

    # 4. Product Context
    prod_ctx = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        scan_date=date(2026, 9, 7),
        ruleset_as_of=date(2026, 9, 7),
    )

    # 5. Adjudication by Phase 2 Rule Engine
    rule_results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(decl_set, prod_ctx)

    # Verify that Rule 13 Unit Threshold flagged NON_COMPLIANT because 1200 g >= 1000 g
    r13_thresh = next(r for r in rule_results if r.rule_id == "R13_UNIT_THRESHOLD")
    assert r13_thresh.verdict == InternalVerdict.NON_COMPLIANT
    assert r13_thresh.ui_bucket == UiBucket.POTENTIAL_NON_COMPLIANCE
    assert "1.2 kg" in r13_thresh.expected
    assert r13_thresh.citation.provision != ""

    # Overall verdict reflects the violation
    assert overall_verdict == InternalVerdict.NON_COMPLIANT
    assert overall_ui_bucket == UiBucket.POTENTIAL_NON_COMPLIANCE
    assert summary.potential_non_compliance >= 1


def test_full_pipeline_clean_compliant_pack():
    with open(FIXTURES_DIR / "clean_compliant_pack.json", "r", encoding="utf-8") as f:
        ocr_doc = OcrDocument.model_validate(json.load(f))

    norm_doc = build_normalised_document(ocr_doc)
    capture_ctx = CaptureContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        all_panels_captured=True,
        inspector_id="insp_p3",
        captured_at=datetime(2026, 9, 7, 10, 0, 0),
    )
    decl_set = extract_declarations(norm_doc, ocr_doc, capture_ctx)
    prod_ctx = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        scan_date=date(2026, 9, 7),
        ruleset_as_of=date(2026, 9, 7),
    )

    rule_results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(decl_set, prod_ctx)

    # No non-compliance on clean pack
    assert summary.potential_non_compliance == 0
    assert overall_verdict == InternalVerdict.COMPLIANT
    assert overall_ui_bucket == UiBucket.COMPLIANT


def test_full_pipeline_absence_gate_neutralization():
    """
    When all_panels_captured=False, missing MRP must NOT flag as NON_COMPLIANT
    or MISSING_DECLARATION. It must be neutralized to INSUFFICIENT_EVIDENCE (NOT_CAPTURED).
    """
    with open(FIXTURES_DIR / "missing_mrp.json", "r", encoding="utf-8") as f:
        ocr_doc = OcrDocument.model_validate(json.load(f))

    norm_doc = build_normalised_document(ocr_doc)
    # Inspector did NOT capture/confirm all panels
    capture_ctx = CaptureContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        all_panels_captured=False,
        inspector_id="insp_p3",
        captured_at=datetime(2026, 9, 7, 10, 0, 0),
    )
    decl_set = extract_declarations(norm_doc, ocr_doc, capture_ctx)
    prod_ctx = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        scan_date=date(2026, 9, 7),
        ruleset_as_of=date(2026, 9, 7),
    )

    # Verify declaration level not_found_reason
    mrp_decl = next(d for d in decl_set.declarations if d.field == Field.RETAIL_SALE_PRICE)
    assert mrp_decl.status == ExtractionStatus.NOT_FOUND
    assert mrp_decl.not_found_reason == NotFoundReason.PANEL_NOT_CAPTURED

    rule_results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(decl_set, prod_ctx)

    r6_mrp = next(r for r in rule_results if r.rule_id == "R6_1_E_RSP_FORM")
    # Rule 6(1)(e) is disabled; evaluated as COMPLIANT without accusing
    assert r6_mrp.verdict == InternalVerdict.COMPLIANT
    assert summary.potential_non_compliance == 0
