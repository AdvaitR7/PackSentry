"""
Rule Engine Evaluator (ADR-0001, ADR-0002, ADR-0004, ADR-0005).

Coordinates:
- Six-gate applicability chain execution
- Pure raw-text evaluation (ADR-0002)
- Evaluator-owned provenance taint neutralization (ADR-0004/0005)
- Absence-evidence gating (ADR-0005)
- Nine-state internal verdict to six truthful UI buckets mapping
- Overall inspection verdict aggregation
"""

from typing import List, Optional, Tuple
from lmpc_schema import (
    ApplicabilityResult,
    ApplicabilityStatus,
    ConfidenceSet,
    DeclarationSet,
    ExtractionMethod,
    InternalVerdict,
    ProductContext,
    RuleResult,
    SummaryCounts,
    UiBucket,
)

from .applicability import check_applicability
from .spec import RuleOutcome, RuleSpec


VERDICT_TO_UI_BUCKET = {
    InternalVerdict.COMPLIANT: UiBucket.COMPLIANT,
    InternalVerdict.NON_COMPLIANT: UiBucket.POTENTIAL_NON_COMPLIANCE,
    InternalVerdict.MISSING_DECLARATION: UiBucket.POTENTIAL_NON_COMPLIANCE,
    InternalVerdict.NOT_CAPTURED: UiBucket.INSUFFICIENT_EVIDENCE,
    InternalVerdict.LOW_CONFIDENCE: UiBucket.MANUAL_REVIEW,
    InternalVerdict.UNVERIFIABLE: UiBucket.MANUAL_REVIEW,
    InternalVerdict.INDETERMINATE: UiBucket.MANUAL_REVIEW,
    InternalVerdict.NOT_APPLICABLE: UiBucket.NOT_APPLICABLE,
    InternalVerdict.NOT_EVALUATED: UiBucket.NOT_EVALUATED,
}

# Strict severity precedence for evaluated rules (ADR-0005)
SEVERITY_ORDER = [
    InternalVerdict.NON_COMPLIANT,
    InternalVerdict.MISSING_DECLARATION,
    InternalVerdict.LOW_CONFIDENCE,
    InternalVerdict.INDETERMINATE,
    InternalVerdict.UNVERIFIABLE,
    InternalVerdict.NOT_CAPTURED,
    InternalVerdict.COMPLIANT,
]


def _make_result(
    spec: RuleSpec,
    verdict: InternalVerdict,
    ui_bucket: UiBucket,
    reason_code: str,
    message: str,
    applicability: ApplicabilityResult,
    *,
    observed: Optional[str] = None,
    expected: Optional[str] = None,
    evidence: Optional[List] = None,
    confidence: Optional[ConfidenceSet] = None,
) -> RuleResult:
    """Builds a RuleResult, filling the registry-owned fields from the spec."""
    return RuleResult(
        rule_id=spec.rule_id,
        provision=spec.citation.provision,
        title=spec.title,
        verdict=verdict,
        ui_bucket=ui_bucket,
        reason_code=reason_code,
        message=message,
        observed=observed,
        expected=expected,
        evidence=evidence if evidence is not None else [],
        confidence=confidence or ConfidenceSet(ocr=1.0, extraction=1.0, rule=1.0),
        applicability=applicability,
        citation=spec.citation,
    )


def evaluate_single_rule(
    spec: RuleSpec,
    declarations: DeclarationSet,
    context: ProductContext,
) -> RuleResult:
    """Evaluates one RuleSpec against the provided declarations and product context."""
    # 1. Check if rule is deferred (ADR-0012)
    if spec.deferred:
        return _make_result(
            spec,
            InternalVerdict.NOT_EVALUATED,
            UiBucket.NOT_EVALUATED,
            spec.deferred_reason_code or "RULE_DEFERRED",
            spec.deferred_message or "Rule capability is deferred in this demo scope.",
            ApplicabilityResult(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                gate=None,
                reason_code=spec.deferred_reason_code,
                message=spec.deferred_message,
            ),
        )

    # 2. Check Applicability Chain
    app_res, special_flag = check_applicability(spec, context)

    # Special handling for Rule 3 contested ambiguity (ADR-0006)
    if special_flag == "RULE_3_AMBIGUOUS":
        return _make_result(
            spec,
            InternalVerdict.INDETERMINATE,
            UiBucket.MANUAL_REVIEW,
            "RULE_3_AMBIGUOUS",
            app_res.message or "Rule 3 boundary is contested.",
            app_res,
        )

    if app_res.status == ApplicabilityStatus.NOT_APPLICABLE:
        return _make_result(
            spec,
            InternalVerdict.NOT_APPLICABLE,
            UiBucket.NOT_APPLICABLE,
            app_res.reason_code or "NOT_APPLICABLE",
            app_res.message or "Rule is not applicable to this inspection context.",
            app_res,
        )

    # 3. Applicable rule: execute core evaluation function
    if not spec.evaluate_fn:
        return _make_result(
            spec,
            InternalVerdict.UNVERIFIABLE,
            UiBucket.MANUAL_REVIEW,
            "EVALUATION_FUNCTION_MISSING",
            "No evaluation routine registered for this rule.",
            app_res,
        )

    outcome: RuleOutcome = spec.evaluate_fn(declarations, context)

    verdict = outcome.verdict
    reason_code = outcome.reason_code
    message = outcome.message

    # 4. Absence-Evidence Gate (ADR-0005)
    # If a rule returned MISSING_DECLARATION, verify that all panels were confirmed captured.
    if verdict == InternalVerdict.MISSING_DECLARATION:
        if not declarations.panel_coverage.all_panels_confirmed:
            # Reclassify to NOT_CAPTURED
            verdict = InternalVerdict.NOT_CAPTURED
            reason_code = "PANEL_NOT_CONFIRMED_CAPTURED"
            message = (
                "Required declaration was not detected, but all package panels were not confirmed captured. "
                "Per ADR-0005 absence-evidence gate, missing evidence cannot be inferred as an offense."
            )

    # 5. Provenance Taint Neutralization Gate (ADR-0004 & ADR-0005)
    # Generative fallback evidence can assist review but cannot accuse or clear.
    if ExtractionMethod.VLM_FALLBACK in outcome.methods_used:
        verdict = InternalVerdict.LOW_CONFIDENCE
        reason_code = "VLM_UNVERIFIED_EXTRACTION"
        message = (
            f"Extraction relied on generative VLM fallback. Per ADR-0004/0005 safety controls, "
            f"generative outputs cannot support an accusation or clean clearance: {outcome.message}"
        )

    ui_bucket = VERDICT_TO_UI_BUCKET.get(verdict, UiBucket.MANUAL_REVIEW)

    ocr_c = outcome.ocr_confidence if outcome.ocr_confidence is not None else 1.0
    ext_c = outcome.extraction_confidence if outcome.extraction_confidence is not None else 1.0

    return _make_result(
        spec,
        verdict,
        ui_bucket,
        reason_code,
        message,
        app_res,
        observed=outcome.observed,
        expected=outcome.expected,
        evidence=outcome.evidence,
        confidence=ConfidenceSet(ocr=ocr_c, extraction=ext_c, rule=1.0),
    )


def aggregate_inspection_results(
    results: List[RuleResult],
) -> Tuple[InternalVerdict, UiBucket, SummaryCounts]:
    """
    Computes summary counts and aggregates overall verdict according to
    strict legal severity order (ADR-0005).
    """
    counts = SummaryCounts()

    for r in results:
        if r.ui_bucket == UiBucket.COMPLIANT:
            counts.compliant += 1
        elif r.ui_bucket == UiBucket.POTENTIAL_NON_COMPLIANCE:
            counts.potential_non_compliance += 1
        elif r.ui_bucket == UiBucket.MANUAL_REVIEW:
            counts.manual_review += 1
        elif r.ui_bucket == UiBucket.INSUFFICIENT_EVIDENCE:
            counts.insufficient_evidence += 1
        elif r.ui_bucket == UiBucket.NOT_APPLICABLE:
            counts.not_applicable += 1
        elif r.ui_bucket == UiBucket.NOT_EVALUATED:
            counts.not_evaluated += 1

    # Severity aggregation among evaluated results
    evaluated_verdicts = {
        r.verdict
        for r in results
        if r.verdict not in [InternalVerdict.NOT_APPLICABLE, InternalVerdict.NOT_EVALUATED]
    }

    overall_verdict = InternalVerdict.COMPLIANT
    for v in SEVERITY_ORDER:
        if v in evaluated_verdicts:
            overall_verdict = v
            break

    # If no rules were evaluated at all (e.g. all NOT_APPLICABLE)
    if not evaluated_verdicts:
        if any(r.verdict == InternalVerdict.NOT_EVALUATED for r in results):
            overall_verdict = InternalVerdict.NOT_EVALUATED
        else:
            overall_verdict = InternalVerdict.NOT_APPLICABLE

    overall_ui_bucket = VERDICT_TO_UI_BUCKET.get(overall_verdict, UiBucket.MANUAL_REVIEW)

    return overall_verdict, overall_ui_bucket, counts
