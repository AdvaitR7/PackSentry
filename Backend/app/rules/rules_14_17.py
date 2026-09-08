"""
Rules 14, 15, 16, 17: Category-Gated Declaration Rules.
Covers Textiles & Household articles (Rule 14), Price-related dimensions (Rule 15),
Usable sheets (Rule 16), and Containers sold as containers (Rule 17).
"""

from datetime import date
from typing import List
from lmpc_schema import (
    CommodityCategory,
    DeclarationSet,
    Field,
    InternalVerdict,
    ProductContext,
)

from .citations import (
    CIT_RULE_14,
    CIT_RULE_15,
    CIT_RULE_16,
    CIT_RULE_17,
)
from .helpers import declaration_found, find_declaration, methods_used_for, raw_text_of
from .spec import RuleOutcome, RuleSpec


def _merge_evidence(*declarations) -> List:
    """Concatenates evidence from each present declaration, preserving order."""
    return [span for decl in declarations if decl for span in decl.evidence]


# -------------------------------------------------------------------------
# Rule 14: Textile and Household Commodities (Number + Finished Dimensions)
# -------------------------------------------------------------------------
def evaluate_r14_textile(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl_dim = find_declaration(declarations, Field.COMMODITY_DIMENSIONS)
    decl_piece = find_declaration(declarations, Field.PIECE_COUNT)
    decl_entries = find_declaration(declarations, Field.PER_PIECE_ENTRIES)

    consulted = [decl_dim, decl_piece, decl_entries]
    methods = methods_used_for(consulted)

    has_dim = declaration_found(decl_dim) or declaration_found(decl_entries)
    has_count = declaration_found(decl_piece)

    if not has_count and not has_dim:
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="TEXTILE_DECLARATIONS_ABSENT",
            message="Rule 14 mandates declaration of piece count and finished dimensions on textile packages.",
            expected="Piece count and finished dimensions (e.g. '1 Bedsheet 2.25 m x 2.50 m')",
            methods_used=methods,
        )

    if not has_dim:
        return RuleOutcome(
            verdict=InternalVerdict.NON_COMPLIANT,
            reason_code="TEXTILE_FINISHED_DIMENSIONS_MISSING",
            message="Textile product specifies count but omits finished dimensions required by Rule 14.",
            observed=raw_text_of(decl_piece),
            expected="Finished dimensions of the textile article",
            evidence=decl_piece.evidence if decl_piece else [],
            methods_used=methods,
        )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="TEXTILE_DECLARATIONS_COMPLIANT",
        message="Textile product declares piece count and finished dimensions in compliance with Rule 14.",
        observed=raw_text_of(decl_entries) or raw_text_of(decl_dim),
        expected="Number of pieces and finished dimensions",
        evidence=_merge_evidence(*consulted),
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# Rule 15: Price-Related Dimensions / Weight
# -------------------------------------------------------------------------
def evaluate_r15_price_related_dimensions(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl_dim = find_declaration(declarations, Field.COMMODITY_DIMENSIONS)
    decl_qty = find_declaration(declarations, Field.NET_QUANTITY)
    consulted = [decl_dim, decl_qty]
    methods = methods_used_for(consulted)

    if declaration_found(decl_dim) or declaration_found(decl_qty):
        return RuleOutcome(
            verdict=InternalVerdict.COMPLIANT,
            reason_code="PRICE_DIMENSIONS_DECLARED",
            message="Relevant dimensions or net weight bearing upon commodity price are declared.",
            observed=raw_text_of(decl_dim) or raw_text_of(decl_qty),
            evidence=_merge_evidence(decl_dim, decl_qty),
            methods_used=methods,
        )

    return RuleOutcome(
        verdict=InternalVerdict.MISSING_DECLARATION,
        reason_code="PRICE_DIMENSIONS_ABSENT",
        message="Commodities whose price depends on size or weight must declare relevant dimensions or weight (Rule 15).",
        expected="Dimensions or weight declaration",
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# Rule 16: Usable Sheets and Sheet Dimensions
# -------------------------------------------------------------------------
def evaluate_r16_usable_sheets(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl_sheets = find_declaration(declarations, Field.USABLE_SHEET_COUNT)
    decl_dims = find_declaration(declarations, Field.SHEET_DIMENSIONS)
    consulted = [decl_sheets, decl_dims]
    methods = methods_used_for(consulted)

    has_sheets = declaration_found(decl_sheets)
    has_dims = declaration_found(decl_dims)

    if not has_sheets and not has_dims:
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="SHEET_DECLARATIONS_ABSENT",
            message="Rule 16 mandates declaration of usable sheet count and sheet dimensions for sheet commodities.",
            expected="Number of usable sheets and dimensions of each sheet",
            methods_used=methods,
        )

    if not has_sheets:
        return RuleOutcome(
            verdict=InternalVerdict.NON_COMPLIANT,
            reason_code="USABLE_SHEET_COUNT_ABSENT",
            message="Sheet product declares dimensions but fails to declare the number of usable sheets (Rule 16).",
            observed=raw_text_of(decl_dims),
            expected="Usable sheet count (e.g. '100 Usable Sheets')",
            evidence=decl_dims.evidence if decl_dims else [],
            methods_used=methods,
        )

    if not has_dims:
        return RuleOutcome(
            verdict=InternalVerdict.NON_COMPLIANT,
            reason_code="SHEET_DIMENSIONS_ABSENT",
            message="Sheet product declares sheet count but fails to declare dimensions of each sheet (Rule 16).",
            observed=raw_text_of(decl_sheets),
            expected="Dimensions of each sheet (e.g. '21 cm x 21 cm')",
            evidence=decl_sheets.evidence if decl_sheets else [],
            methods_used=methods,
        )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="SHEET_DECLARATIONS_COMPLIANT",
        message="Usable sheet count and per-sheet dimensions declared in compliance with Rule 16.",
        observed=f"{raw_text_of(decl_sheets)}, {raw_text_of(decl_dims)}",
        expected="Number of usable sheets and dimensions of each sheet",
        evidence=_merge_evidence(*consulted),
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# Rule 17: Container-Type Commodities Sold as Containers
# -------------------------------------------------------------------------
def evaluate_r17_container_type(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl_count = find_declaration(declarations, Field.PIECE_COUNT)
    decl_dim = find_declaration(declarations, Field.COMMODITY_DIMENSIONS)
    consulted = [decl_count, decl_dim]
    methods = methods_used_for(consulted)

    has_count = declaration_found(decl_count)
    has_dim = declaration_found(decl_dim)

    if not has_count or not has_dim:
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="CONTAINER_DECLARATIONS_ABSENT",
            message="Commodities sold as containers must declare number of containers and dimensions/capacity (Rule 17).",
            expected="Number of containers and dimensions (length, width, depth or diameter)",
            methods_used=methods,
        )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="CONTAINER_DECLARATIONS_COMPLIANT",
        message="Container count and dimensions declared in compliance with Rule 17.",
        observed=f"{raw_text_of(decl_count)}, {raw_text_of(decl_dim)}",
        expected="Number of containers and dimensions",
        evidence=_merge_evidence(decl_count, decl_dim),
        methods_used=methods,
    )


# Rule Specifications
RULES_14_17_SPECS: List[RuleSpec] = [
    RuleSpec(
        rule_id="R14_TEXTILE",
        title="Number of pieces and finished dimensions for textile commodities",
        citation=CIT_RULE_14,
        effective_from=date(2011, 3, 7),
        required_category=CommodityCategory.TEXTILE,
        evaluate_fn=evaluate_r14_textile,
    ),
    RuleSpec(
        rule_id="R15_PRICE_RELATED_DIMENSIONS",
        title="Dimensions and weight where relevant to price",
        citation=CIT_RULE_15,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r15_price_related_dimensions,
    ),
    RuleSpec(
        rule_id="R16_USABLE_SHEETS",
        title="Number of usable sheets and dimensions of each sheet",
        citation=CIT_RULE_16,
        effective_from=date(2011, 3, 7),
        required_category=CommodityCategory.SHEET_PRODUCT,
        evaluate_fn=evaluate_r16_usable_sheets,
    ),
    RuleSpec(
        rule_id="R17_CONTAINER_TYPE",
        title="Number of containers and dimensions for container commodities",
        citation=CIT_RULE_17,
        effective_from=date(2011, 3, 7),
        required_category=CommodityCategory.CONTAINER_TYPE,
        evaluate_fn=evaluate_r17_container_type,
    ),
]
