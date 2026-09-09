"""
Phase 5 Safety-Negative Test Suite: Absence Evidence & VLM Provenance Taint.

This suite is intentionally adversarial. It proves that uncertainty can never be
converted into a statutory accusation or an unsupported compliance clearance.

ADR-0004: VLM-influenced evidence is strictly LOW_CONFIDENCE / MANUAL_REVIEW.
ADR-0005: OCR misses on unexamined panels are NOT_CAPTURED / INSUFFICIENT_EVIDENCE.
"""

from datetime import date
import pytest

from lmpc_schema import (
    CommodityCategory,
    Declaration,
    DeclarationSet,
    DimensionKind,
    EvidenceSpan,
    ExtractionMethod,
    ExtractionStatus,
    Field,
    ImportStatus,
    InternalVerdict,
    NotFoundReason,
    PackageType,
    PanelCoverage,
    PanelRole,
    ParsedPrice,
    ParsedQuantity,
    PricePrefixForm,
    ProductContext,
    UiBucket,
)

from app.provenance import FORBIDDEN_TAINTED_VERDICTS, verify_taint_neutralization
from app.rules import evaluate_inspection, evaluate_single_rule, get_rule


def make_context() -> ProductContext:
    return ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        scan_date=date(2026, 9, 7),
        ruleset_as_of=date(2026, 9, 7),
        net_quantity_in_base_units={"value": 0.5, "unit": "kg"},
    )


# ============================================================================
# 1. Absence-Evidence Gate: Missing OCR Never Becomes Statutory Absence
# ============================================================================

@pytest.mark.parametrize(
    "field,rule_id",
    [
        (Field.COMMON_GENERIC_NAME, "R6_1_B_GENERIC_NAME"),
        (Field.NET_QUANTITY, "R6_1_C_NET_QUANTITY"),
        (Field.DATE_OF_MANUFACTURE_PACKING_IMPORT, "R6_1_D_DATE"),
        (Field.RETAIL_SALE_PRICE, "R6_1_E_RSP_FORM"),
        (Field.CONSUMER_CARE, "R6_2_CONSUMER_CARE"),
    ],
)
def test_unconfirmed_panels_missing_field_never_accuses(field: Field, rule_id: str):
    """
    If all packaging panels were not examined, an OCR miss cannot become a legal
    declaration absence. Every mandatory field must route to recapture/review.
    """
    missing = Declaration(
        field=field,
        status=ExtractionStatus.NOT_FOUND,
        raw_value=None,
        not_found_reason=NotFoundReason.NO_MATCH_IN_CAPTURED_PANELS,
    )
    decl_set = DeclarationSet(
        declarations=[missing],
        panel_coverage=PanelCoverage(
            roles_captured=[PanelRole.PDP],
            all_panels_confirmed=False,
        ),
    )

    result = evaluate_single_rule(get_rule(rule_id), decl_set, make_context())

    assert result.verdict == InternalVerdict.NOT_CAPTURED
    assert result.ui_bucket == UiBucket.INSUFFICIENT_EVIDENCE
    assert result.reason_code == "PANEL_NOT_CONFIRMED_CAPTURED"
    assert result.verdict not in {
        InternalVerdict.NON_COMPLIANT,
        InternalVerdict.MISSING_DECLARATION,
    }


def test_missing_declaration_only_permitted_after_all_panels_confirmed():
    """The same OCR miss may become MISSING_DECLARATION only after full panel confirmation."""
    missing_mrp = Declaration(
        field=Field.RETAIL_SALE_PRICE,
        status=ExtractionStatus.NOT_FOUND,
        not_found_reason=NotFoundReason.NO_MATCH_IN_CAPTURED_PANELS,
    )

    partial = DeclarationSet(
        declarations=[missing_mrp],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP], all_panels_confirmed=False),
    )
    confirmed = DeclarationSet(
        declarations=[missing_mrp],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    rule = get_rule("R6_1_E_RSP_FORM")
    result_partial = evaluate_single_rule(rule, partial, make_context())
    result_confirmed = evaluate_single_rule(rule, confirmed, make_context())

    assert result_partial.verdict == InternalVerdict.NOT_CAPTURED
    assert result_confirmed.verdict == InternalVerdict.MISSING_DECLARATION


# ============================================================================
# 2. VLM Taint Gate: Generative Evidence Cannot Accuse or Clear
# ============================================================================

@pytest.mark.parametrize(
    "raw_value,parsed,rule_id",
    [
        (
            "500 g",
            ParsedQuantity(
                magnitude=500.0,
                unit_raw="g",
                unit_canonical="g",
                dimension=DimensionKind.MASS,
                is_si=True,
                symbol_is_prescribed=True,
            ),
            "R13_SI_ONLY",
        ),
        (
            "1200 gms",
            ParsedQuantity(
                magnitude=1200.0,
                unit_raw="gms",
                unit_canonical="g",
                dimension=DimensionKind.MASS,
                is_si=True,
                symbol_is_prescribed=False,
            ),
            "R13_SI_ONLY",
        ),
    ],
)
def test_vlm_quantity_cannot_clear_or_accuse(raw_value, parsed, rule_id):
    """Both seemingly compliant and seemingly violating VLM results neutralize identically."""
    tainted = Declaration(
        field=Field.NET_QUANTITY,
        status=ExtractionStatus.FOUND,
        raw_value=raw_value,
        parsed=parsed,
        evidence=[EvidenceSpan(image_id="img", line_id="line", raw_text=raw_value, polygon_normalized=[])],
        extraction_confidence=0.75,
        method=ExtractionMethod.VLM_FALLBACK,
    )
    decl_set = DeclarationSet(
        declarations=[tainted],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    result = evaluate_single_rule(get_rule(rule_id), decl_set, make_context())

    assert result.verdict == InternalVerdict.LOW_CONFIDENCE
    assert result.ui_bucket == UiBucket.MANUAL_REVIEW
    assert result.reason_code == "VLM_UNVERIFIED_EXTRACTION"
    assert result.verdict not in FORBIDDEN_TAINTED_VERDICTS
    verify_taint_neutralization(result, [tainted])


def test_vlm_price_cannot_clear_or_accuse():
    """A VLM-extracted MRP form cannot produce COMPLIANT or NON_COMPLIANT."""
    tainted_price = Declaration(
        field=Field.RETAIL_SALE_PRICE,
        status=ExtractionStatus.FOUND,
        raw_value="MRP Rs. 500.00",
        parsed=ParsedPrice(
            amount=500.0,
            prefix_raw="MRP",
            prefix_form=PricePrefixForm.MRP,
            inclusive_phrase_present=False,
        ),
        method=ExtractionMethod.VLM_FALLBACK,
        extraction_confidence=0.70,
    )
    decl_set = DeclarationSet(
        declarations=[tainted_price],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    result = evaluate_single_rule(get_rule("R6_1_E_RSP_FORM"), decl_set, make_context())
    assert result.verdict == InternalVerdict.LOW_CONFIDENCE
    assert result.ui_bucket == UiBucket.MANUAL_REVIEW
    assert result.reason_code == "VLM_UNVERIFIED_EXTRACTION"


def test_vlm_taint_forces_overall_manual_review():
    """Any critical VLM-neutralized rule on an otherwise compliant pack must surface as overall MANUAL_REVIEW."""
    from lmpc_schema import DateForm, DateLabel, ParsedAddress, ParsedDate

    clean_declarations = [
        Declaration(
            field=Field.COMMON_GENERIC_NAME,
            status=ExtractionStatus.FOUND,
            raw_value="PREMIUM ASSAM TEA",
            method=ExtractionMethod.ALIAS_ANCHOR,
        ),
        Declaration(
            field=Field.NET_QUANTITY,
            status=ExtractionStatus.FOUND,
            raw_value="500 g",
            parsed=ParsedQuantity(
                magnitude=500.0,
                unit_raw="g",
                unit_canonical="g",
                dimension=DimensionKind.MASS,
                is_si=True,
                symbol_is_prescribed=True,
            ),
            method=ExtractionMethod.VLM_FALLBACK,  # Tainted!
        ),
        Declaration(
            field=Field.RETAIL_SALE_PRICE,
            status=ExtractionStatus.FOUND,
            raw_value="MRP Rs. 249.00 (inclusive of all taxes)",
            parsed=ParsedPrice(
                amount=249.0,
                currency="INR",
                prefix_raw="MRP",
                prefix_form=PricePrefixForm.MRP,
                inclusive_phrase_present=True,
            ),
            method=ExtractionMethod.ALIAS_ANCHOR,
        ),
        Declaration(
            field=Field.MANUFACTURER_NAME_ADDRESS,
            status=ExtractionStatus.FOUND,
            raw_value="Apex Tea Ltd, Plot 14, MIDC Bhosari, Pune, Maharashtra 411026",
            parsed=ParsedAddress(
                lines=["Plot 14, MIDC Bhosari", "Pune, Maharashtra 411026"],
                has_premises_number=True,
                has_street=True,
                has_city=True,
                has_state=True,
                pin_code="411026",
            ),
            method=ExtractionMethod.ALIAS_ANCHOR,
        ),
        Declaration(
            field=Field.DATE_OF_MANUFACTURE_PACKING_IMPORT,
            status=ExtractionStatus.FOUND,
            raw_value="PKD: 07/2026",
            parsed=ParsedDate(month=7, year=2026, form=DateForm.NUMERIC, label=DateLabel.PKD),
            method=ExtractionMethod.ALIAS_ANCHOR,
        ),
        Declaration(
            field=Field.CONSUMER_CARE,
            status=ExtractionStatus.FOUND,
            raw_value="Consumer Care: care@apextea.in, Tel: 1800-200-1234",
            method=ExtractionMethod.ALIAS_ANCHOR,
        ),
    ]

    decl_set = DeclarationSet(
        declarations=clean_declarations,
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    results, overall, overall_ui, summary = evaluate_inspection(decl_set, make_context())
    quantity_results = [r for r in results if r.rule_id in {"R6_1_C_NET_QUANTITY", "R12_QUANTITY_BASIS", "R13_UNIT_THRESHOLD", "R13_SI_ONLY"}]

    assert any(r.verdict == InternalVerdict.LOW_CONFIDENCE for r in quantity_results)
    assert overall_ui == UiBucket.MANUAL_REVIEW
    assert summary.manual_review >= 1
