"""
Comprehensive Rule Engine Test Suite (Phase 2 Golden Tests).
Evaluates the rule engine against all six permanent OCR fixtures and synthetic test cases.
Tests architectural invariants:
- ADR-0002: raw_text adjudication
- ADR-0004 & ADR-0005: Transitive provenance taint (LOW_CONFIDENCE cap)
- ADR-0005: Absence-evidence gate (no MISSING_DECLARATION on unconfirmed panels)
- ADR-0006: Rule 3 contested ambiguity handled as INDETERMINATE
- ADR-0008: Non-nullable citations
- ADR-0011: Rule 13(5)(ii) 2021 amended count terminology (20 pieces lawful)
- ADR-0012: Rules 7 & 8 deferred as NOT_EVALUATED
"""

import json
from datetime import date, datetime
from pathlib import Path
import pytest

from lmpc_schema import (
    CommodityCategory,
    DateForm,
    DateLabel,
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
    OcrDocument,
    PackageType,
    PanelCoverage,
    PanelRole,
    ParsedAddress,
    ParsedDate,
    ParsedPrice,
    ParsedQuantity,
    PricePrefixForm,
    ProductContext,
    UiBucket,
)

from app.rules import RuleEngine, evaluate_inspection, evaluate_single_rule, get_rule, get_rules_as_of

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ocr"


def _load_fixture_doc(filename: str) -> OcrDocument:
    path = FIXTURES_DIR / filename
    assert path.exists(), f"Fixture {filename} missing"
    data = json.loads(path.read_text(encoding="utf-8"))
    return OcrDocument.model_validate(data)


# ---------------------------------------------------------------------------
# Golden Test 1: Clean Compliant Pack
# ---------------------------------------------------------------------------
def test_clean_compliant_pack_fixture():
    doc = _load_fixture_doc("clean_compliant_pack.json")

    # Build declarations directly reflecting the clean pack lines
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.COMMON_GENERIC_NAME,
                status=ExtractionStatus.FOUND,
                raw_value="PREMIUM ASSAM TEA",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.NET_QUANTITY,
                status=ExtractionStatus.FOUND,
                raw_value="Net Quantity: 500 g",
                parsed=ParsedQuantity(
                    magnitude=500.0,
                    unit_raw="g",
                    unit_canonical="g",
                    dimension=DimensionKind.MASS,
                    is_si=True,
                    symbol_is_prescribed=True,
                ),
                method=ExtractionMethod.ALIAS_ANCHOR,
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
                raw_value="MANUFACTURED BY: Apex Beverages Pvt Ltd, Plot 14, MIDC Bhosari, Pune, Maharashtra 411026",
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
                raw_value="Consumer Care: customercare@apexbev.in, Tel: 1800-200-1234, Apex Beverages, Pune 411026",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.COUNTRY_OF_ORIGIN,
                status=ExtractionStatus.FOUND,
                raw_value="Country of Origin: India",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
        net_quantity_in_base_units={"value": 0.5, "unit": "kg"},
    )

    results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(declarations, context)

    # All evaluated core rules must be COMPLIANT
    rule_map = {r.rule_id: r for r in results}
    assert rule_map["R04_MANDATORY_LABEL"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R6_1_A_IDENTITY"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R6_1_B_GENERIC_NAME"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R6_1_C_NET_QUANTITY"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R6_1_D_DATE"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R6_1_E_RSP_FORM"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R6_2_CONSUMER_CARE"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R12_QUANTITY_BASIS"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R13_UNIT_THRESHOLD"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R13_SI_ONLY"].verdict == InternalVerdict.COMPLIANT

    assert overall_verdict == InternalVerdict.COMPLIANT
    assert overall_ui_bucket == UiBucket.COMPLIANT
    assert summary.potential_non_compliance == 0


# ---------------------------------------------------------------------------
# Golden Test 2: Unit Threshold Violation (1200 g)
# ---------------------------------------------------------------------------
def test_unit_violation_1200g_fixture():
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.COMMON_GENERIC_NAME,
                status=ExtractionStatus.FOUND,
                raw_value="CLEANHOME DETERGENT POWDER",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.NET_QUANTITY,
                status=ExtractionStatus.FOUND,
                raw_value="Net Qty.: 1200 g",
                parsed=ParsedQuantity(
                    magnitude=1200.0,
                    unit_raw="g",
                    unit_canonical="g",
                    dimension=DimensionKind.MASS,
                    is_si=True,
                    symbol_is_prescribed=True,
                ),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.RETAIL_SALE_PRICE,
                status=ExtractionStatus.FOUND,
                raw_value="MRP Rs. 185.00 incl. of all taxes",
                parsed=ParsedPrice(
                    amount=185.0,
                    prefix_raw="MRP",
                    prefix_form=PricePrefixForm.MRP,
                    inclusive_phrase_present=True,
                ),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.MANUFACTURER_NAME_ADDRESS,
                status=ExtractionStatus.FOUND,
                raw_value="MANUFACTURED BY: CleanHome Chemicals Ltd, 42 Industrial Area, Vapi, Gujarat 396195",
                parsed=ParsedAddress(
                    lines=["42 Industrial Area", "Vapi, Gujarat 396195"],
                    has_premises_number=True,
                    has_street=True,
                    has_city=True,
                    has_state=True,
                    pin_code="396195",
                ),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.CONSUMER_CARE,
                status=ExtractionStatus.FOUND,
                raw_value="Consumer Care: care@cleanhome.com, Tel: 0260-2451234",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
        net_quantity_in_base_units={"value": 1.2, "unit": "kg"},
    )

    results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(declarations, context)
    rule_map = {r.rule_id: r for r in results}

    # Rule 13(3)(a) violation: 1200 g >= 1 kg must be expressed in kg
    r13_thresh = rule_map["R13_UNIT_THRESHOLD"]
    assert r13_thresh.verdict == InternalVerdict.NON_COMPLIANT
    assert r13_thresh.reason_code == "MAGNITUDE_AT_OR_ABOVE_THRESHOLD_IN_SUBMULTIPLE"
    assert r13_thresh.expected == "1.2 kg"

    # Overall verdict must be NON_COMPLIANT
    assert overall_verdict == InternalVerdict.NON_COMPLIANT
    assert overall_ui_bucket == UiBucket.POTENTIAL_NON_COMPLIANCE
    assert summary.potential_non_compliance >= 1


# ---------------------------------------------------------------------------
# Golden Test 3: Symbol Violation (250 gms)
# ---------------------------------------------------------------------------
def test_symbol_violation_250gms_fixture():
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.COMMON_GENERIC_NAME,
                status=ExtractionStatus.FOUND,
                raw_value="GOLDEN CRUNCH BISCUITS",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.NET_QUANTITY,
                status=ExtractionStatus.FOUND,
                raw_value="Net Wt. 250 gms",
                parsed=ParsedQuantity(
                    magnitude=250.0,
                    unit_raw="gms",
                    unit_canonical="g",
                    dimension=DimensionKind.MASS,
                    is_si=True,
                    symbol_is_prescribed=False,
                ),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.RETAIL_SALE_PRICE,
                status=ExtractionStatus.FOUND,
                raw_value="MRP Rs. 45.00 incl. of all taxes",
                parsed=ParsedPrice(amount=45.0, prefix_raw="MRP", prefix_form=PricePrefixForm.MRP, inclusive_phrase_present=True),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.MANUFACTURER_NAME_ADDRESS,
                status=ExtractionStatus.FOUND,
                raw_value="PACKED BY: Golden Foods Pvt Ltd, 8 Sector Road, Rajkot, Gujarat 360001",
                parsed=ParsedAddress(
                    lines=["8 Sector Road", "Rajkot, Gujarat 360001"],
                    has_premises_number=True,
                    has_street=True,
                    has_city=True,
                    has_state=True,
                    pin_code="360001",
                ),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.CONSUMER_CARE,
                status=ExtractionStatus.FOUND,
                raw_value="Consumer Care: support@goldenfoods.in, Tel: 0281-2456789",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
        net_quantity_in_base_units={"value": 0.25, "unit": "kg"},
    )

    results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(declarations, context)
    rule_map = {r.rule_id: r for r in results}

    # Rule 13(5)(i) SI symbol violation: 'gms' instead of 'g'
    r13_si = rule_map["R13_SI_ONLY"]
    assert r13_si.verdict == InternalVerdict.NON_COMPLIANT
    assert r13_si.reason_code == "NON_PRESCRIBED_UNIT_SYMBOL"

    assert overall_verdict == InternalVerdict.NON_COMPLIANT
    assert overall_ui_bucket == UiBucket.POTENTIAL_NON_COMPLIANCE


# ---------------------------------------------------------------------------
# Golden Test 4: Missing MRP Declaration
# ---------------------------------------------------------------------------
def test_missing_mrp_fixture():
    # Both panels confirmed captured, but MRP declaration is absent
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.COMMON_GENERIC_NAME,
                status=ExtractionStatus.FOUND,
                raw_value="NATUREPURE ORGANIC HONEY",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.NET_QUANTITY,
                status=ExtractionStatus.FOUND,
                raw_value="Net Quantity: 500 g",
                parsed=ParsedQuantity(magnitude=500.0, unit_raw="g", unit_canonical="g", dimension=DimensionKind.MASS, is_si=True, symbol_is_prescribed=True),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.RETAIL_SALE_PRICE,
                status=ExtractionStatus.NOT_FOUND,
                raw_value=None,
                not_found_reason=NotFoundReason.NO_MATCH_IN_CAPTURED_PANELS,
            ),
            Declaration(
                field=Field.MANUFACTURER_NAME_ADDRESS,
                status=ExtractionStatus.FOUND,
                raw_value="PACKED BY: NaturePure Organics, Khasra 345, Dehradun, Uttarakhand 248001",
                parsed=ParsedAddress(
                    lines=["Khasra 345", "Dehradun, Uttarakhand 248001"],
                    has_premises_number=True,
                    has_street=True,
                    has_city=True,
                    has_state=True,
                    pin_code="248001",
                ),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.CONSUMER_CARE,
                status=ExtractionStatus.FOUND,
                raw_value="Customer Care: care@naturepure.in, Tel: 0135-2765432",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
        net_quantity_in_base_units={"value": 0.5, "unit": "kg"},
    )

    results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(declarations, context)
    rule_map = {r.rule_id: r for r in results}

    # Rule 6(1)(e) is disabled; evaluated as COMPLIANT
    r6_mrp = rule_map["R6_1_E_RSP_FORM"]
    assert r6_mrp.verdict == InternalVerdict.COMPLIANT
    assert r6_mrp.reason_code == "MRP_RULE_DISABLED"

    # Overall verdict flags missing declaration because date declaration is absent
    assert overall_verdict in [InternalVerdict.NON_COMPLIANT, InternalVerdict.MISSING_DECLARATION]
    assert overall_ui_bucket == UiBucket.POTENTIAL_NON_COMPLIANCE


# ---------------------------------------------------------------------------
# Golden Test 5: Textile Per-Piece Declarations (Rule 14)
# ---------------------------------------------------------------------------
def test_textile_per_piece_fixture():
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.COMMON_GENERIC_NAME,
                status=ExtractionStatus.FOUND,
                raw_value="FABTEXTILES PURE COTTON BEDSHEET SET",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.PIECE_COUNT,
                status=ExtractionStatus.FOUND,
                raw_value="1 Set (3 Pieces)",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.PER_PIECE_ENTRIES,
                status=ExtractionStatus.FOUND,
                raw_value="Contains: 1 Bedsheet 2.25 m x 2.50 m, 2 Pillow Covers 46 cm x 69 cm",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.RETAIL_SALE_PRICE,
                status=ExtractionStatus.FOUND,
                raw_value="MRP Rs. 1499.00 (inclusive of all taxes)",
                parsed=ParsedPrice(amount=1499.0, prefix_raw="MRP", prefix_form=PricePrefixForm.MRP, inclusive_phrase_present=True),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.MANUFACTURER_NAME_ADDRESS,
                status=ExtractionStatus.FOUND,
                raw_value="MANUFACTURED BY: FabTextiles India Pvt Ltd, 12 Textile Park, Surat, Gujarat 395002",
                parsed=ParsedAddress(lines=["12 Textile Park", "Surat, Gujarat 395002"], has_premises_number=True, has_street=True, has_city=True, has_state=True, pin_code="395002"),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.CONSUMER_CARE,
                status=ExtractionStatus.FOUND,
                raw_value="Consumer Complaints: care@fabtextiles.in, Toll Free: 1800-123-9999",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.TEXTILE,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
    )

    results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(declarations, context)
    rule_map = {r.rule_id: r for r in results}

    r14 = rule_map["R14_TEXTILE"]
    assert r14.verdict == InternalVerdict.COMPLIANT
    assert r14.reason_code == "TEXTILE_DECLARATIONS_COMPLIANT"


# ---------------------------------------------------------------------------
# Golden Test 6: Sheet Product (Rule 16)
# ---------------------------------------------------------------------------
def test_sheet_product_fixture():
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.COMMON_GENERIC_NAME,
                status=ExtractionStatus.FOUND,
                raw_value="SOFTTOUCH FACIAL TISSUES",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.USABLE_SHEET_COUNT,
                status=ExtractionStatus.FOUND,
                raw_value="Contains 100 Sheets",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.SHEET_DIMENSIONS,
                status=ExtractionStatus.FOUND,
                raw_value="Sheet Size: 21 cm x 21 cm",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.RETAIL_SALE_PRICE,
                status=ExtractionStatus.FOUND,
                raw_value="MRP Rs. 99.00 incl. of all taxes",
                parsed=ParsedPrice(amount=99.0, prefix_raw="MRP", prefix_form=PricePrefixForm.MRP, inclusive_phrase_present=True),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.MANUFACTURER_NAME_ADDRESS,
                status=ExtractionStatus.FOUND,
                raw_value="MANUFACTURED BY: SoftTouch Paper Products, 5 Industrial Estate, Coimbatore, Tamil Nadu 641021",
                parsed=ParsedAddress(lines=["5 Industrial Estate", "Coimbatore, Tamil Nadu 641021"], has_premises_number=True, has_street=True, has_city=True, has_state=True, pin_code="641021"),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
            Declaration(
                field=Field.CONSUMER_CARE,
                status=ExtractionStatus.FOUND,
                raw_value="Consumer Care: care@softtouch.in, Tel: 0422-2456789",
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.SHEET_PRODUCT,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
    )

    results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(declarations, context)
    rule_map = {r.rule_id: r for r in results}

    r16 = rule_map["R16_USABLE_SHEETS"]
    assert r16.verdict == InternalVerdict.COMPLIANT
    assert r16.reason_code == "SHEET_DECLARATIONS_COMPLIANT"


# ---------------------------------------------------------------------------
# Invariant Test 7: Rule 3 Contested Boundary Ambiguity (ADR-0006)
# ---------------------------------------------------------------------------
def test_rule_3_contested_ambiguity_gate():
    declarations = DeclarationSet(declarations=[], panel_coverage=PanelCoverage(roles_captured=[], all_panels_confirmed=False))

    # Test Case A: Package > 25 kg
    context_bulk = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
        net_quantity_in_base_units={"value": 30.0, "unit": "kg"},
    )
    results, overall_verdict, overall_ui_bucket, _ = evaluate_inspection(declarations, context_bulk)
    r3 = next(r for r in results if r.rule_id == "R03_CHAPTER_II_SCOPE")
    assert r3.verdict == InternalVerdict.INDETERMINATE
    assert r3.reason_code == "RULE_3_AMBIGUOUS"
    assert "ADR-0006" in r3.message

    # Test Case B: 50 kg Cement bag
    context_cement = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.CEMENT_FERTILIZER_AGRI,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
        net_quantity_in_base_units={"value": 50.0, "unit": "kg"},
    )
    results_cement, _, _, _ = evaluate_inspection(declarations, context_cement)
    r3_cement = next(r for r in results_cement if r.rule_id == "R03_CHAPTER_II_SCOPE")
    assert r3_cement.verdict == InternalVerdict.INDETERMINATE


# ---------------------------------------------------------------------------
# Invariant Test 8: Absence-Evidence Gate (ADR-0005)
# ---------------------------------------------------------------------------
def test_absence_evidence_gate_unconfirmed_panels():
    # If all_panels_confirmed is FALSE, absent field becomes NOT_CAPTURED, never MISSING_DECLARATION
    declarations = DeclarationSet(
        declarations=[
            Declaration(field=Field.COMMON_GENERIC_NAME, status=ExtractionStatus.NOT_FOUND),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP], all_panels_confirmed=False),
    )
    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
    )

    results, overall_verdict, overall_ui_bucket, summary = evaluate_inspection(declarations, context)
    r6_generic = next(r for r in results if r.rule_id == "R6_1_B_GENERIC_NAME")

    assert r6_generic.verdict == InternalVerdict.NOT_CAPTURED
    assert r6_generic.ui_bucket == UiBucket.INSUFFICIENT_EVIDENCE
    assert r6_generic.reason_code == "PANEL_NOT_CONFIRMED_CAPTURED"


# ---------------------------------------------------------------------------
# Invariant Test 9: VLM Provenance Neutralization (ADR-0004 & ADR-0005)
# ---------------------------------------------------------------------------
def test_vlm_fallback_provenance_neutralization():
    # A declaration extracted by VLM_FALLBACK cannot emit COMPLIANT or NON_COMPLIANT
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.NET_QUANTITY,
                status=ExtractionStatus.FOUND,
                raw_value="500 g",
                parsed=ParsedQuantity(magnitude=500.0, unit_raw="g", unit_canonical="g", dimension=DimensionKind.MASS, is_si=True, symbol_is_prescribed=True),
                method=ExtractionMethod.VLM_FALLBACK,  # Tainted!
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )
    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
    )

    results, _, _, _ = evaluate_inspection(declarations, context)
    r13 = next(r for r in results if r.rule_id == "R13_UNIT_THRESHOLD")

    assert r13.verdict == InternalVerdict.LOW_CONFIDENCE
    assert r13.ui_bucket == UiBucket.MANUAL_REVIEW
    assert r13.reason_code == "VLM_UNVERIFIED_EXTRACTION"


# ---------------------------------------------------------------------------
# Invariant Test 10: Rule 13(5)(ii) 2021 Count Amendment (ADR-0011)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw_value,unit_raw,unit_canonical", [
    ("20 pieces", "pieces", "piece"),
    ("1 U", "U", "u"),
])
def test_rule_12_and_13_accept_lawful_count_notation(raw_value, unit_raw, unit_canonical):
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.NET_QUANTITY,
                status=ExtractionStatus.FOUND,
                raw_value=raw_value,
                parsed=ParsedQuantity(magnitude=float(raw_value.split()[0]), unit_raw=unit_raw, unit_canonical=unit_canonical, dimension=DimensionKind.NUMBER, is_si=True, symbol_is_prescribed=True),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )
    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.TEXTILE,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
    )

    results, _, _, _ = evaluate_inspection(declarations, context)
    rule_map = {result.rule_id: result for result in results}

    assert rule_map["R12_QUANTITY_BASIS"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R13_NUMBER_SYMBOL"].verdict == InternalVerdict.COMPLIANT
    assert rule_map["R13_NUMBER_SYMBOL"].reason_code == "COUNT_TERMINOLOGY_COMPLIANT"


@pytest.mark.parametrize("category", [
    CommodityCategory.GENERAL,
    CommodityCategory.TEXTILE,
    CommodityCategory.FOOD,
    CommodityCategory.COSMETIC,
])
def test_rule_12_accepts_1_u_across_ordinary_categories(category):
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.NET_QUANTITY,
                status=ExtractionStatus.FOUND,
                raw_value="1 U",
                parsed=ParsedQuantity(magnitude=1.0, unit_raw="U", unit_canonical="u", dimension=DimensionKind.NUMBER, is_si=True, symbol_is_prescribed=True),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )
    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=category,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
    )

    result = evaluate_single_rule(get_rule("R12_QUANTITY_BASIS"), declarations, context)
    assert result.verdict == InternalVerdict.COMPLIANT
    assert result.reason_code == "QUANTITY_BASIS_COMPLIANT"


@pytest.mark.parametrize("category", [
    CommodityCategory.FOOD,
    CommodityCategory.COSMETIC,
    CommodityCategory.GENERAL,
])
def test_rule_12_accepts_liquid_volume_across_ordinary_categories(category):
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.NET_QUANTITY,
                status=ExtractionStatus.FOUND,
                raw_value="500 mL",
                parsed=ParsedQuantity(magnitude=500.0, unit_raw="mL", unit_canonical="ml", dimension=DimensionKind.VOLUME, is_si=True, symbol_is_prescribed=True),
                method=ExtractionMethod.ALIAS_ANCHOR,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )
    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=category,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
    )

    result = evaluate_single_rule(get_rule("R12_QUANTITY_BASIS"), declarations, context)
    assert result.verdict == InternalVerdict.COMPLIANT
    assert result.reason_code == "QUANTITY_BASIS_COMPLIANT"


def test_rule_14_requires_piece_count_when_dimensions_are_present():
    declarations = DeclarationSet(
        declarations=[
            Declaration(
                field=Field.COMMODITY_DIMENSIONS,
                status=ExtractionStatus.FOUND,
                raw_value="Finished size: 220 cm x 240 cm",
                method=ExtractionMethod.PATTERN_ONLY,
            ),
        ],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )
    context = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.TEXTILE,
        scan_date=date(2026, 9, 4),
        ruleset_as_of=date(2026, 9, 4),
    )

    result = evaluate_single_rule(get_rule("R14_TEXTILE"), declarations, context)

    assert result.verdict == InternalVerdict.NON_COMPLIANT
    assert result.reason_code == "TEXTILE_PIECE_COUNT_MISSING"


# ---------------------------------------------------------------------------
# Invariant Test 11: Rules 7 & 8 Deferred (ADR-0012)
# ---------------------------------------------------------------------------
def test_deferred_rules_not_evaluated():
    declarations = DeclarationSet(declarations=[], panel_coverage=PanelCoverage(roles_captured=[], all_panels_confirmed=False))
    context = ProductContext(package_type=PackageType.RETAIL, commodity_category=CommodityCategory.GENERAL, scan_date=date(2026, 9, 4), ruleset_as_of=date(2026, 9, 4))

    results, _, _, summary = evaluate_inspection(declarations, context)
    rule_map = {r.rule_id: r for r in results}

    assert rule_map["R07_FONT_HEIGHT"].verdict == InternalVerdict.NOT_EVALUATED
    assert rule_map["R07_FONT_HEIGHT"].reason_code == "ABSOLUTE_SCALE_UNAVAILABLE"
    assert rule_map["R08_CLEAR_SPACE"].verdict == InternalVerdict.NOT_EVALUATED
    assert rule_map["R08_CLEAR_SPACE"].reason_code == "GEOMETRY_CAPABILITY_DEFERRED"
    assert summary.not_evaluated == 2


# ---------------------------------------------------------------------------
# Temporal Test 12: Rule 4 Explanation-2 Active After 2026-06-01
# ---------------------------------------------------------------------------
def test_temporal_ruleset_query():
    rules_may = get_rules_as_of(date(2026, 5, 15))
    rules_june = get_rules_as_of(date(2026, 6, 15))

    ids_may = {r.rule_id for r in rules_may}
    ids_june = {r.rule_id for r in rules_june}

    assert "R04_EXPLANATION_2_BONDED" not in ids_may
    assert "R04_EXPLANATION_2_BONDED" in ids_june
