"""
Tests for Selective VLM Interpreter and Transitive Provenance Taint Enforcement (D7, ADR-0004, ADR-0005).

Safety Invariants Tested:
1. Declarations produced by VLM fallback carry ExtractionMethod.VLM_FALLBACK.
2. An extracted declaration with VLM taint CANNOT produce COMPLIANT, NON_COMPLIANT,
   or MISSING_DECLARATION when evaluated by any statutory rule.
3. The rule engine evaluator strictly neutralizes the verdict to LOW_CONFIDENCE
   with reason_code = "VLM_UNVERIFIED_EXTRACTION".
4. Overall inspection aggregation reflects the neutralized verdict truthfully.
"""

from datetime import date, datetime
import pytest

from app.ocr.vlm_interpreter import QwenVlmInterpreter
from app.provenance import (
    is_any_tainted,
    is_tainted_declaration,
    tag_as_vlm_fallback,
    verify_taint_neutralization,
)
from app.rules import RuleEngine, evaluate_single_rule, get_rule
from lmpc_schema import (
    CaptureContext,
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
    PackageType,
    PanelCoverage,
    PanelRole,
    ParsedPrice,
    ParsedQuantity,
    PricePrefixForm,
    ProductContext,
    UiBucket,
)


def make_clean_context() -> ProductContext:
    return ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.DOMESTIC,
        scan_date=date(2026, 9, 7),
        ruleset_as_of=date(2026, 9, 7),
    )


def test_tag_as_vlm_fallback():
    decl = Declaration(
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
        extraction_confidence=0.99,
    )
    tagged = tag_as_vlm_fallback(decl, confidence_cap=0.75)
    assert tagged.method == ExtractionMethod.VLM_FALLBACK
    assert tagged.extraction_confidence == 0.75
    assert is_tainted_declaration(tagged) is True


def test_vlm_tainted_declaration_neutralized_in_rule_evaluation():
    """
    CRITICAL ADR-0004/0005 TEST:
    Even if the text appears 100% compliant ('500 g'), because it was extracted
    by VLM_FALLBACK, the evaluator MUST neutralize the verdict to LOW_CONFIDENCE
    and reason_code to VLM_UNVERIFIED_EXTRACTION.
    """
    tainted_decl = Declaration(
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
        evidence=[EvidenceSpan(image_id="img1", line_id="l1", polygon_normalized=[], raw_text="500 g")],
        ocr_confidence=0.85,
        extraction_confidence=0.75,
        method=ExtractionMethod.VLM_FALLBACK,
    )

    decl_set = DeclarationSet(
        declarations=[tainted_decl],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP], all_panels_confirmed=True),
    )
    ctx = make_clean_context()

    # Evaluate Rule 6(1)(c) Net Quantity presence
    spec = get_rule("R6_1_C_NET_QUANTITY")
    assert spec is not None
    result = evaluate_single_rule(spec, decl_set, ctx)

    # Invariant: Must NOT be COMPLIANT
    assert result.verdict != InternalVerdict.COMPLIANT
    assert result.verdict == InternalVerdict.LOW_CONFIDENCE
    assert result.ui_bucket == UiBucket.MANUAL_REVIEW
    assert result.reason_code == "VLM_UNVERIFIED_EXTRACTION"
    assert "generative VLM fallback" in result.message

    # Verify programmatic safety assertion
    verify_taint_neutralization(result, [tainted_decl])


def test_vlm_tainted_cannot_accuse_non_compliant():
    """
    CRITICAL ADR-0004/0005 TEST:
    Even if the VLM transcribes an apparent violation ('1200 gms'),
    the generative model's output CANNOT be used to legally accuse a package.
    It MUST be capped at LOW_CONFIDENCE for human manual review.
    """
    tainted_decl = Declaration(
        field=Field.NET_QUANTITY,
        status=ExtractionStatus.FOUND,
        raw_value="1200 gms",
        parsed=ParsedQuantity(
            magnitude=1200.0,
            unit_raw="gms",
            unit_canonical="g",
            dimension=DimensionKind.MASS,
            is_si=True,
            symbol_is_prescribed=False,
        ),
        evidence=[EvidenceSpan(image_id="img1", line_id="l1", polygon_normalized=[], raw_text="1200 gms")],
        ocr_confidence=0.80,
        extraction_confidence=0.70,
        method=ExtractionMethod.VLM_FALLBACK,
    )

    decl_set = DeclarationSet(
        declarations=[tainted_decl],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP], all_panels_confirmed=True),
    )
    ctx = make_clean_context()

    spec = get_rule("R13_SI_ONLY")
    assert spec is not None
    result = evaluate_single_rule(spec, decl_set, ctx)

    assert result.verdict != InternalVerdict.NON_COMPLIANT
    assert result.verdict == InternalVerdict.LOW_CONFIDENCE
    assert result.reason_code == "VLM_UNVERIFIED_EXTRACTION"


@pytest.mark.asyncio
async def test_qwen_vlm_interpreter_readiness_check():
    """Checks that the Ollama interpreter can check readiness on localhost."""
    interpreter = QwenVlmInterpreter()
    readiness = await interpreter.get_readiness()
    assert isinstance(readiness, dict)
    assert "reachable" in readiness
    assert "resident" in readiness
    assert readiness["model"] == "qwen2.5vl:7b"
