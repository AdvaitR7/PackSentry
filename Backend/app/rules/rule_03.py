"""
Rule 3: Chapter II Scope Gate (ADR-0006).
Nothing downstream is meaningful until Chapter II applicability is settled.
Ambiguity (net quantity > 25 kg/L, or cement/fertilizer/agri produce > 50 kg)
is handled generically by the Gate 3 (RULE_3) check inside applicability.py,
which is applied to every rule in the registry -- including this one.
"""

from datetime import date
from lmpc_schema import DeclarationSet, InternalVerdict, ProductContext

from .citations import CIT_RULE_03
from .spec import RuleOutcome, RuleSpec


def evaluate_rule_03(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    """
    Reached only when Gate 3 (RULE_3) in the applicability chain did NOT flag
    ambiguity -- i.e. net quantity is within the ordinary Chapter II scope.
    """
    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="CHAPTER_II_SCOPE_CONFIRMED",
        message="Package falls within ordinary Chapter II scope under Rule 3; no exclusion boundary is contested.",
    )


RULE_03_SPEC = RuleSpec(
    rule_id="R03_CHAPTER_II_SCOPE",
    title="Chapter II applicability gate (Rule 3(a), 3(b))",
    citation=CIT_RULE_03,
    effective_from=date(2011, 3, 7),
    evaluate_fn=evaluate_rule_03,
)
