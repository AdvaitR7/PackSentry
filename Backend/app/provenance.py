"""
Transitive Provenance Taint Enforcement (ADR-0004 & ADR-0005).

Core Architectural Invariant:
Any declaration, span, or relationship derived from or influenced by generative
VLM fallback carries immutable provenance taint. Taint propagates through all stages.
Tainted evidence CANNOT support COMPLIANT, NON_COMPLIANT, or MISSING_DECLARATION.
The rule engine evaluator force-neutralizes tainted evaluations to LOW_CONFIDENCE
with reason_code = "VLM_UNVERIFIED_EXTRACTION".
"""

from typing import List, Optional
from lmpc_schema import (
    Declaration,
    EvidenceSpan,
    ExtractionMethod,
    InternalVerdict,
    RuleResult,
)

FORBIDDEN_TAINTED_VERDICTS = {
    InternalVerdict.COMPLIANT,
    InternalVerdict.NON_COMPLIANT,
    InternalVerdict.MISSING_DECLARATION,
}


def is_tainted_declaration(declaration: Optional[Declaration]) -> bool:
    """Returns True if the declaration was derived from or influenced by VLM fallback."""
    if declaration is None:
        return False
    return declaration.method == ExtractionMethod.VLM_FALLBACK


def is_any_tainted(declarations: List[Optional[Declaration]]) -> bool:
    """Returns True if any consulted declaration in the list carries VLM taint."""
    return any(is_tainted_declaration(d) for d in declarations)


def tag_as_vlm_fallback(
    declaration: Declaration,
    confidence_cap: float = 0.75,
) -> Declaration:
    """
    Applies immutable VLM fallback provenance tag to a declaration.
    Enforces that extraction_confidence is bounded by the confidence cap.
    """
    declaration.method = ExtractionMethod.VLM_FALLBACK
    if declaration.extraction_confidence is not None:
        declaration.extraction_confidence = min(declaration.extraction_confidence, confidence_cap)
    else:
        declaration.extraction_confidence = confidence_cap
    return declaration


def verify_taint_neutralization(rule_result: RuleResult, consulted_declarations: List[Optional[Declaration]]) -> None:
    """
    Safety invariant assertion.
    Asserts that if any consulted declaration carried VLM taint, the rule result
    is strictly neutralized (verdict is LOW_CONFIDENCE and reason_code is VLM_UNVERIFIED_EXTRACTION).
    """
    if is_any_tainted(consulted_declarations):
        if rule_result.verdict in FORBIDDEN_TAINTED_VERDICTS:
            raise AssertionError(
                f"ADR-0004/0005 VIOLATION: Rule '{rule_result.rule_id}' produced verdict "
                f"'{rule_result.verdict}' using VLM-tainted evidence! "
                f"Generative outputs must never accuse or clear a package."
            )
        if rule_result.reason_code != "VLM_UNVERIFIED_EXTRACTION":
            raise AssertionError(
                f"ADR-0004/0005 VIOLATION: Tainted rule result reason_code must be "
                f"'VLM_UNVERIFIED_EXTRACTION', got '{rule_result.reason_code}'."
            )
