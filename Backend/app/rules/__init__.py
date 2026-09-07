"""
PackSentry LMPC Rule Engine Package (ADR-0001).

Adjudicates statutory compliance against extracted DeclarationSet and ProductContext.
Strictly adheres to:
- ADR-0002: Adjudication on raw_text, never on normalized_text.
- ADR-0004 & ADR-0005: Transitive provenance taint neutralization (LOW_CONFIDENCE cap).
- ADR-0005: Absence-evidence gate (no MISSING_DECLARATION on unconfirmed coverage).
- ADR-0006: Rule 3 contested ambiguity handled as INDETERMINATE.
- ADR-0008: Non-nullable statutory citations.
- ADR-0011: Rule 13(5)(ii) amended 2021 text for count units (20 pieces lawful).
- ADR-0012: Deferred Rules 7 & 8 as NOT_EVALUATED.
"""

from typing import List, Optional, Tuple
from lmpc_schema import (
    DeclarationSet,
    InternalVerdict,
    ProductContext,
    RuleResult,
    SummaryCounts,
    UiBucket,
)

from .engine import aggregate_inspection_results, evaluate_single_rule
from .registry import get_all_rules, get_rule, get_rules_as_of
from .spec import RuleOutcome, RuleSpec


class RuleEngine:
    """
    State-isolated Legal Metrology Rule Engine.
    Evaluates an inspection's declarations against statutory rule specifications.
    """

    def __init__(self, rules: Optional[List[RuleSpec]] = None):
        self.rules = rules if rules is not None else get_all_rules()

    def evaluate(
        self,
        declarations: DeclarationSet,
        context: ProductContext,
    ) -> Tuple[List[RuleResult], InternalVerdict, UiBucket, SummaryCounts]:
        """
        Runs all registered rules against the declaration set and product context.
        Returns:
            (rule_results, overall_verdict, overall_ui_bucket, summary_counts)
        """
        results: List[RuleResult] = []
        for spec in self.rules:
            res = evaluate_single_rule(spec, declarations, context)
            results.append(res)

        overall_verdict, overall_ui_bucket, summary = aggregate_inspection_results(results)
        return results, overall_verdict, overall_ui_bucket, summary


def evaluate_inspection(
    declarations: DeclarationSet,
    context: ProductContext,
    rules: Optional[List[RuleSpec]] = None,
) -> Tuple[List[RuleResult], InternalVerdict, UiBucket, SummaryCounts]:
    """Convenience functional interface for evaluating an inspection."""
    engine = RuleEngine(rules=rules)
    return engine.evaluate(declarations, context)


__all__ = [
    "RuleEngine",
    "RuleSpec",
    "RuleOutcome",
    "evaluate_inspection",
    "evaluate_single_rule",
    "aggregate_inspection_results",
    "get_all_rules",
    "get_rule",
    "get_rules_as_of",
]
