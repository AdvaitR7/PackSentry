"""
Rule Specification Types (ADR-0001, ADR-0008).

`normalized_text` MUST NOT be imported anywhere under Backend/app/rules/.
Rules adjudicate strictly on raw_text and parsed values derived from it.
No module under Backend/app/rules/ may import polygon/geometry types (ADR-0012).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, List, Optional

from lmpc_schema import (
    Citation,
    CommodityCategory,
    ConfidenceSet,
    DeclarationSet,
    EvidenceSpan,
    ExtractionMethod,
    InternalVerdict,
    ProductContext,
)


@dataclass
class RuleOutcome:
    """
    The result of a single rule's raw evaluation, before the engine applies
    provenance neutralization (ADR-0004/0005) and applicability gating.
    """
    verdict: InternalVerdict
    reason_code: str
    message: str
    observed: Optional[str] = None
    expected: Optional[str] = None
    evidence: List[EvidenceSpan] = field(default_factory=list)
    ocr_confidence: Optional[float] = None
    extraction_confidence: Optional[float] = None
    # Extraction methods of every declaration this outcome relied upon.
    # The engine caps the outcome at LOW_CONFIDENCE if any is VLM_FALLBACK.
    methods_used: List[ExtractionMethod] = field(default_factory=list)


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    title: str
    citation: Citation
    effective_from: date
    effective_to: Optional[date] = None
    # Rule only applies for this commodity category (CATEGORY gate). None = all categories.
    required_category: Optional[CommodityCategory] = None
    # Rule is displaced (NOT_APPLICABLE) for these categories (DISPLACEMENT gate proviso).
    displaced_for_categories: tuple = ()
    displacement_reason_code: Optional[str] = None
    displacement_message: Optional[str] = None
    # The core evaluation function: (DeclarationSet, ProductContext) -> RuleOutcome
    evaluate_fn: Optional[Callable[[DeclarationSet, ProductContext], RuleOutcome]] = None
    # True for Rules 7 & 8, which never evaluate (ADR-0012); always NOT_EVALUATED.
    deferred: bool = False
    deferred_reason_code: Optional[str] = None
    deferred_message: Optional[str] = None
