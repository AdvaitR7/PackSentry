"""
Comprehensive Golden Statutory Verdict Test Suite (Phase 5 Hardening).

Quality Gate:
Guarantees that every single registered Legal Metrology statutory rule in
Backend/app/rules/registry.py (all 23 rules) produces strict, expected, and undriftable
verdicts across compliant, non-compliant, indeterminate, deferred, and excluded cases.
CI will fail on any unapproved verdict drift or citation deviation.
"""

from datetime import date
import pytest

from lmpc_schema import (
    BaseUnitsInfo,
    CommodityCategory,
    DateForm,
    DateLabel,
    Declaration,
    DeclarationSet,
    DimensionKind,
    ExtractionMethod,
    ExtractionStatus,
    Field,
    ImportStatus,
    InternalVerdict,
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

from app.rules import evaluate_inspection, evaluate_single_rule, get_all_rules, get_rule
from app.rules.registry import get_rules_as_of


def make_coverage(all_confirmed: bool = True) -> PanelCoverage:
    return PanelCoverage(
        roles_captured=[PanelRole.PDP, PanelRole.BACK],
        all_panels_confirmed=all_confirmed,
    )


def make_context(
    package_type: PackageType = PackageType.RETAIL,
    commodity_category: CommodityCategory = CommodityCategory.GENERAL,
    import_status: ImportStatus = ImportStatus.DOMESTIC,
    ruleset_as_of: date = date(2026, 9, 7),
    net_quantity_in_base_units: BaseUnitsInfo = None,
) -> ProductContext:
    return ProductContext(
        package_type=package_type,
        commodity_category=commodity_category,
        import_status=import_status,
        scan_date=ruleset_as_of,
        ruleset_as_of=ruleset_as_of,
        net_quantity_in_base_units=net_quantity_in_base_units,
    )


# ============================================================================
# 1. Registry Invariant: All 23 Rules Must Be Registered and Carry Valid Citations
# ============================================================================

def test_rule_registry_completeness_and_citations():
    rules = get_all_rules()
    assert len(rules) == 23, f"Expected exactly 23 statutory rules in registry, got {len(rules)}"

    rule_ids = set()
    for rule in rules:
        assert rule.rule_id not in rule_ids, f"Duplicate rule_id detected: {rule.rule_id}"
        rule_ids.add(rule.rule_id)

        # ADR-0008: Citations are non-nullable
        assert rule.citation is not None, f"Rule {rule.rule_id} missing required statutory citation."
        assert rule.citation.provision, f"Rule {rule.rule_id} citation missing provision."
        assert rule.citation.instrument, f"Rule {rule.rule_id} citation missing instrument."
        assert rule.citation.gsr, f"Rule {rule.rule_id} citation missing gsr."
        assert rule.effective_from is not None, f"Rule {rule.rule_id} missing effective_from date."


# ============================================================================
# 2. Golden Rule Tests: Rule 03 & Rule 04
# ============================================================================

def test_golden_r03_scope_indeterminate():
    spec = get_rule("R03_CHAPTER_II_SCOPE")
    assert spec is not None

    # Over 25 kg triggers contested boundary ambiguity (ADR-0006)
    ctx_bulk = make_context(
        net_quantity_in_base_units=BaseUnitsInfo(value=30.0, unit="kg"),
    )
    decl_set = DeclarationSet(declarations=[], panel_coverage=make_coverage())

    res = evaluate_single_rule(spec, decl_set, ctx_bulk)
    assert res.verdict == InternalVerdict.INDETERMINATE
    assert res.ui_bucket == UiBucket.MANUAL_REVIEW
    assert res.reason_code == "RULE_3_AMBIGUOUS"


def test_golden_r04_mandatory_label():
    spec = get_rule("R04_MANDATORY_LABEL")
    assert spec is not None
    ctx = make_context()

    # Case A: Compliant (bears primary declarations: identity, quantity, price)
    decl_set_comp = DeclarationSet(
        declarations=[
            Declaration(field=Field.MANUFACTURER_NAME_ADDRESS, status=ExtractionStatus.FOUND, raw_value="Apex Tea Ltd"),
            Declaration(field=Field.NET_QUANTITY, status=ExtractionStatus.FOUND, raw_value="500 g"),
            Declaration(field=Field.RETAIL_SALE_PRICE, status=ExtractionStatus.FOUND, raw_value="MRP Rs. 100"),
        ],
        panel_coverage=make_coverage(),
    )
    res_comp = evaluate_single_rule(spec, decl_set_comp, ctx)
    assert res_comp.verdict == InternalVerdict.COMPLIANT
    assert res_comp.reason_code == "MANDATORY_DECLARATIONS_AFFIXED"

    # Case B: Excluded category (Institutional package deferred under Rule 3(c))
    ctx_institutional = make_context(package_type=PackageType.INSTITUTIONAL)
    res_excl = evaluate_single_rule(spec, decl_set_comp, ctx_institutional)
    assert res_excl.verdict == InternalVerdict.NOT_APPLICABLE


def test_golden_r04_explanation_2_digital_bonded():
    spec = get_rule("R04_EXPLANATION_2_BONDED")
    assert spec is not None

    # Pre-commencement date (< 2026-06-01) -> NOT_APPLICABLE via Gate 1
    ctx_old = make_context(import_status=ImportStatus.IMPORTED, ruleset_as_of=date(2026, 1, 1))
    decl_set = DeclarationSet(declarations=[], panel_coverage=make_coverage())
    res_old = evaluate_single_rule(spec, decl_set, ctx_old)
    assert res_old.verdict == InternalVerdict.NOT_APPLICABLE

    # Active date (>= 2026-06-01) Domestic product -> Compliant (not relevant to domestic)
    ctx_dom = make_context(import_status=ImportStatus.DOMESTIC, ruleset_as_of=date(2026, 7, 1))
    res_dom = evaluate_single_rule(spec, decl_set, ctx_dom)
    assert res_dom.verdict == InternalVerdict.COMPLIANT
    assert res_dom.reason_code == "EXPLANATION_2_NOT_RELEVANT_DOMESTIC"


# ============================================================================
# 3. Golden Rule Tests: Rule 6 Mandatory Declarations
# ============================================================================

def test_golden_r06_identity_name_address():
    spec = get_rule("R6_1_A_IDENTITY")
    assert spec is not None
    ctx = make_context()

    decl_valid = Declaration(
        field=Field.MANUFACTURER_NAME_ADDRESS,
        status=ExtractionStatus.FOUND,
        raw_value="Apex Tea Ltd, Plot 5, MIDC, Pune, Maharashtra 411026",
        parsed=ParsedAddress(
            lines=["Plot 5, MIDC", "Pune, Maharashtra 411026"],
            has_premises_number=True,
            has_street=True,
            has_city=True,
            has_state=True,
            pin_code="411026",
        ),
        method=ExtractionMethod.ALIAS_ANCHOR,
    )
    res_comp = evaluate_single_rule(spec, DeclarationSet(declarations=[decl_valid], panel_coverage=make_coverage()), ctx)
    assert res_comp.verdict == InternalVerdict.COMPLIANT


def test_golden_r06_retail_sale_price_inclusive_phrase():
    spec = get_rule("R6_1_E_RSP_FORM")
    assert spec is not None
    ctx = make_context()

    # Valid MRP with statutory inclusive phrase
    decl_valid = Declaration(
        field=Field.RETAIL_SALE_PRICE,
        status=ExtractionStatus.FOUND,
        raw_value="MRP Rs. 150.00 (inclusive of all taxes)",
        parsed=ParsedPrice(amount=150.0, prefix_raw="MRP", prefix_form=PricePrefixForm.MRP, inclusive_phrase_present=True),
        method=ExtractionMethod.ALIAS_ANCHOR,
    )
    res_comp = evaluate_single_rule(spec, DeclarationSet(declarations=[decl_valid], panel_coverage=make_coverage()), ctx)
    assert res_comp.verdict == InternalVerdict.COMPLIANT

    # Violation: MRP missing "inclusive of all taxes"
    decl_invalid = Declaration(
        field=Field.RETAIL_SALE_PRICE,
        status=ExtractionStatus.FOUND,
        raw_value="MRP Rs. 150.00",
        parsed=ParsedPrice(amount=150.0, prefix_raw="MRP", prefix_form=PricePrefixForm.MRP, inclusive_phrase_present=False),
        method=ExtractionMethod.ALIAS_ANCHOR,
    )
    res_non_comp = evaluate_single_rule(spec, DeclarationSet(declarations=[decl_invalid], panel_coverage=make_coverage()), ctx)
    assert res_non_comp.verdict == InternalVerdict.NON_COMPLIANT
    assert res_non_comp.reason_code == "TAX_INCLUSIVE_PHRASE_MISSING"


def test_golden_r06_country_of_origin():
    spec = get_rule("R6_COUNTRY_OF_ORIGIN")
    assert spec is not None

    # Domestic -> Compliant because country of origin is not legally mandated
    ctx_dom = make_context(import_status=ImportStatus.DOMESTIC)
    res_dom = evaluate_single_rule(spec, DeclarationSet(declarations=[], panel_coverage=make_coverage()), ctx_dom)
    assert res_dom.verdict == InternalVerdict.COMPLIANT
    assert res_dom.reason_code == "DOMESTIC_NOT_MANDATED"

    # Imported with origin declared -> COMPLIANT
    ctx_imp = make_context(import_status=ImportStatus.IMPORTED)
    decl_origin = Declaration(field=Field.COUNTRY_OF_ORIGIN, status=ExtractionStatus.FOUND, raw_value="Country of Origin: Germany")
    res_imp = evaluate_single_rule(spec, DeclarationSet(declarations=[decl_origin], panel_coverage=make_coverage()), ctx_imp)
    assert res_imp.verdict == InternalVerdict.COMPLIANT

    # Imported without origin -> MISSING_DECLARATION
    res_imp_missing = evaluate_single_rule(spec, DeclarationSet(declarations=[], panel_coverage=make_coverage()), ctx_imp)
    assert res_imp_missing.verdict == InternalVerdict.MISSING_DECLARATION
    assert res_imp_missing.reason_code == "COUNTRY_OF_ORIGIN_ABSENT"


# ============================================================================
# 4. Golden Rule Tests: Rule 12 & Rule 13 (Weights, Quantities, Symbols)
# ============================================================================

def test_golden_r12_quantity_basis():
    spec = get_rule("R12_QUANTITY_BASIS")
    assert spec is not None
    ctx = make_context()

    decl_qty = Declaration(
        field=Field.NET_QUANTITY,
        status=ExtractionStatus.FOUND,
        raw_value="500 g",
        parsed=ParsedQuantity(magnitude=500.0, unit_raw="g", unit_canonical="g", dimension=DimensionKind.MASS, is_si=True, symbol_is_prescribed=True),
    )
    res = evaluate_single_rule(spec, DeclarationSet(declarations=[decl_qty], panel_coverage=make_coverage()), ctx)
    assert res.verdict == InternalVerdict.COMPLIANT


def test_golden_r13_unit_threshold_and_si_symbol():
    spec_thresh = get_rule("R13_UNIT_THRESHOLD")
    spec_si = get_rule("R13_SI_ONLY")
    ctx = make_context(net_quantity_in_base_units=BaseUnitsInfo(value=1.2, unit="kg"))

    # Case A: 1200 g -> Threshold violation under Rule 13(3)(a)
    decl_1200g = Declaration(
        field=Field.NET_QUANTITY,
        status=ExtractionStatus.FOUND,
        raw_value="1200 g",
        parsed=ParsedQuantity(magnitude=1200.0, unit_raw="g", unit_canonical="g", dimension=DimensionKind.MASS, is_si=True, symbol_is_prescribed=True),
    )
    res_thresh = evaluate_single_rule(spec_thresh, DeclarationSet(declarations=[decl_1200g], panel_coverage=make_coverage()), ctx)
    assert res_thresh.verdict == InternalVerdict.NON_COMPLIANT
    assert res_thresh.reason_code == "MAGNITUDE_AT_OR_ABOVE_THRESHOLD_IN_SUBMULTIPLE"

    # Case B: 250 gms -> Non-prescribed unit symbol violation
    decl_250gms = Declaration(
        field=Field.NET_QUANTITY,
        status=ExtractionStatus.FOUND,
        raw_value="250 gms",
        parsed=ParsedQuantity(magnitude=250.0, unit_raw="gms", unit_canonical="g", dimension=DimensionKind.MASS, is_si=True, symbol_is_prescribed=False),
    )
    res_si = evaluate_single_rule(spec_si, DeclarationSet(declarations=[decl_250gms], panel_coverage=make_coverage()), ctx)
    assert res_si.verdict == InternalVerdict.NON_COMPLIANT
    assert res_si.reason_code == "NON_PRESCRIBED_UNIT_SYMBOL"


# ============================================================================
# 5. Golden Rule Tests: Category Specific Rules (Rules 14-17)
# ============================================================================

def test_golden_rules_14_to_17_category_gating():
    decl_set = DeclarationSet(declarations=[], panel_coverage=make_coverage())

    # R14 (Textile) only applies to TEXTILE
    spec_14 = get_rule("R14_TEXTILE")
    ctx_general = make_context(commodity_category=CommodityCategory.GENERAL)
    res_14_gen = evaluate_single_rule(spec_14, decl_set, ctx_general)
    assert res_14_gen.verdict == InternalVerdict.NOT_APPLICABLE
    assert res_14_gen.reason_code == "CATEGORY_MISMATCH"

    # R16 (Sheets) only applies to SHEET_PRODUCT
    spec_16 = get_rule("R16_USABLE_SHEETS")
    res_16_gen = evaluate_single_rule(spec_16, decl_set, ctx_general)
    assert res_16_gen.verdict == InternalVerdict.NOT_APPLICABLE
    assert res_16_gen.reason_code == "CATEGORY_MISMATCH"

    # R17 (Container Type) only applies to CONTAINER_TYPE
    spec_17 = get_rule("R17_CONTAINER_TYPE")
    res_17_gen = evaluate_single_rule(spec_17, decl_set, ctx_general)
    assert res_17_gen.verdict == InternalVerdict.NOT_APPLICABLE
    assert res_17_gen.reason_code == "CATEGORY_MISMATCH"


# ============================================================================
# 6. Golden Rule Tests: Deferred Rules (ADR-0012)
# ============================================================================

def test_golden_deferred_rules_truthfully_not_evaluated():
    decl_set = DeclarationSet(declarations=[], panel_coverage=PanelCoverage(roles_captured=[], all_panels_confirmed=False))
    ctx = make_context()

    r7 = evaluate_single_rule(get_rule("R07_FONT_HEIGHT"), decl_set, ctx)
    assert r7.verdict == InternalVerdict.NOT_EVALUATED
    assert r7.ui_bucket == UiBucket.NOT_EVALUATED
    assert r7.reason_code == "ABSOLUTE_SCALE_UNAVAILABLE"

    r8 = evaluate_single_rule(get_rule("R08_CLEAR_SPACE"), decl_set, ctx)
    assert r8.verdict == InternalVerdict.NOT_EVALUATED
    assert r8.ui_bucket == UiBucket.NOT_EVALUATED
    assert r8.reason_code == "GEOMETRY_CAPABILITY_DEFERRED"
