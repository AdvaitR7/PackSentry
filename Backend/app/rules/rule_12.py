"""
Rule 12: Basis of declaration of net quantity, and the Fourth Schedule exceptions.
Also includes Rule 12(6) misleading-wording keyword check.
"""

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from lmpc_schema import (
    CommodityCategory,
    DeclarationSet,
    DimensionKind,
    Field,
    InternalVerdict,
    ParsedQuantity,
    ProductContext,
)

from .citations import CIT_RULE_12_6, CIT_RULE_12_BASE
from .helpers import declaration_found, find_declaration, methods_used_for, raw_text_of
from .spec import RuleOutcome, RuleSpec


_FOURTH_SCHEDULE_PATH = Path(__file__).resolve().parent.parent / "data" / "fourth_schedule.yaml"

# Rule 12(2) ordinary basis mapping (used when no Fourth Schedule override applies)
_ORDINARY_CATEGORY_BASIS: Dict[CommodityCategory, DimensionKind] = {
    CommodityCategory.TEXTILE: DimensionKind.NUMBER,
    CommodityCategory.SHEET_PRODUCT: DimensionKind.NUMBER,
    CommodityCategory.CONTAINER_TYPE: DimensionKind.NUMBER,
    CommodityCategory.FOOD: DimensionKind.MASS,
    CommodityCategory.COSMETIC: DimensionKind.MASS,
    CommodityCategory.ALCOHOL: DimensionKind.VOLUME,
    CommodityCategory.SEEDS: DimensionKind.MASS,
    CommodityCategory.CEMENT_FERTILIZER_AGRI: DimensionKind.MASS,
    CommodityCategory.GENERAL: DimensionKind.MASS,
}

_MISLEADING_KEYWORDS = ["minimum", "not less than", "average", "about", "approximately"]


def _load_fourth_schedule() -> dict:
    if not _FOURTH_SCHEDULE_PATH.exists():
        return {"commodities": {}}
    with open(_FOURTH_SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"commodities": {}}


def _permitted_bases(context: ProductContext) -> Optional[List[str]]:
    """Returns permitted bases from the Fourth Schedule for the context's
    fourth_schedule_key, or None if no override applies (fall through to Rule 12(2))."""
    if not context.fourth_schedule_key:
        return None
    schedule = _load_fourth_schedule()
    entry = schedule.get("commodities", {}).get(context.fourth_schedule_key)
    if entry:
        return entry.get("permitted_bases")
    return None


def evaluate_r12_quantity_basis(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.NET_QUANTITY)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="NET_QUANTITY_ABSENT_FOR_BASIS_CHECK",
            message="Cannot evaluate quantity basis: net quantity declaration is absent.",
            expected="Net quantity in a permitted statutory basis",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    parsed = decl.parsed

    permitted = _permitted_bases(context)
    if permitted is None:
        # Fall through to Rule 12(2) ordinary mapping
        expected_basis = _ORDINARY_CATEGORY_BASIS.get(context.commodity_category)
        permitted = [expected_basis.value] if expected_basis else None

    if isinstance(parsed, ParsedQuantity) and permitted:
        declared_basis = parsed.dimension.value
        if declared_basis not in permitted:
            return RuleOutcome(
                verdict=InternalVerdict.NON_COMPLIANT,
                reason_code="IMPERMISSIBLE_QUANTITY_BASIS",
                message=(
                    f"Quantity declared by {declared_basis}, but Rule 12 permits only "
                    f"{'/'.join(permitted)} for this commodity."
                ),
                observed=raw_val,
                expected=f"Quantity basis: {'/'.join(permitted)}",
                evidence=decl.evidence,
                ocr_confidence=decl.ocr_confidence,
                extraction_confidence=decl.extraction_confidence,
                methods_used=methods,
            )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="QUANTITY_BASIS_COMPLIANT",
        message="Net quantity declared using a permitted basis under Rule 12.",
        observed=raw_val,
        expected="Permitted quantity basis",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


def evaluate_r12_6_misleading(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.NET_QUANTITY)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.NOT_CAPTURED,
            reason_code="NET_QUANTITY_ABSENT_FOR_MISLEADING_CHECK",
            message="Cannot check for misleading wording: net quantity declaration is absent.",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    lower_raw = raw_val.lower()
    found_keywords = [kw for kw in _MISLEADING_KEYWORDS if kw in lower_raw]

    if found_keywords:
        return RuleOutcome(
            verdict=InternalVerdict.NON_COMPLIANT,
            reason_code="MISLEADING_QUANTITY_WORDING",
            message=f"Quantity declaration contains prohibited qualifying language: {', '.join(found_keywords)} (Rule 12(6)).",
            observed=raw_val,
            expected="Definite, unqualified quantity declaration",
            evidence=decl.evidence,
            ocr_confidence=decl.ocr_confidence,
            extraction_confidence=decl.extraction_confidence,
            methods_used=methods,
        )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="NO_MISLEADING_WORDING",
        message="Quantity declaration is free of misleading qualifying words.",
        observed=raw_val,
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


RULE_12_QUANTITY_BASIS_SPEC = RuleSpec(
    rule_id="R12_QUANTITY_BASIS",
    title="Basis of quantity declaration (mass/volume/length/area/number)",
    citation=CIT_RULE_12_BASE,
    effective_from=date(2011, 3, 7),
    evaluate_fn=evaluate_r12_quantity_basis,
)

RULE_12_6_MISLEADING_SPEC = RuleSpec(
    rule_id="R12_6_MISLEADING",
    title="Prohibition of misleading quantity wording",
    citation=CIT_RULE_12_6,
    effective_from=date(2011, 3, 7),
    evaluate_fn=evaluate_r12_6_misleading,
)
