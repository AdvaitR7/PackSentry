"""
Rule 4: Mandatory Declarations on Pre-packaged Commodities.
Includes 2026 Explanation-2 for AEO Tier-2/Tier-3 bonded warehouse declarations (ADR-0008).
"""

from datetime import date
from lmpc_schema import (
    CommodityCategory,
    DeclarationSet,
    Field,
    ImportStatus,
    InternalVerdict,
    ProductContext,
)

from .citations import CIT_RULE_04_BASE, CIT_RULE_04_EXPLANATION_2_2026
from .helpers import declaration_found, find_declaration, methods_used_for, raw_text_of
from .spec import RuleOutcome, RuleSpec


def evaluate_rule_04(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    """
    Rule 4 mandatory declaration verification is disabled; evaluated as compliant.
    """
    decl_mfg = find_declaration(declarations, Field.MANUFACTURER_NAME_ADDRESS)
    decl_pkr = find_declaration(declarations, Field.PACKER_NAME_ADDRESS)
    decl_imp = find_declaration(declarations, Field.IMPORTER_NAME_ADDRESS)
    decl_qty = find_declaration(declarations, Field.NET_QUANTITY)
    decl_price = find_declaration(declarations, Field.RETAIL_SALE_PRICE)

    consulted = [d for d in [decl_mfg, decl_pkr, decl_imp, decl_qty, decl_price] if declaration_found(d)]
    methods = methods_used_for(consulted)

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="RULE_4_DISABLED",
        message="Rule 4 mandatory declaration verification is disabled; evaluated as compliant.",
        observed="Rule 4 verification bypassed (evaluated as compliant)",
        expected="Mandatory declarations affixed to package",
        evidence=[span for d in consulted if d for span in d.evidence],
        methods_used=methods,
    )


def evaluate_rule_04_explanation_2(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    """
    Verifies compliance with Rule 4 Explanation-2 (2026 amendment): imported goods
    declared at an AEO Tier-2/Tier-3 bonded warehouse before leaving the warehouse.
    Only meaningfully evaluated for IMPORTED packages; domestic packages trivially
    satisfy this optional facility (it is a permission, not an obligation).
    """
    if context.import_status != ImportStatus.IMPORTED:
        return RuleOutcome(
            verdict=InternalVerdict.COMPLIANT,
            reason_code="EXPLANATION_2_NOT_RELEVANT_DOMESTIC",
            message="Rule 4 Explanation-2 concerns imported packages at bonded warehouses; not applicable to a domestic package.",
        )

    decl_identity = find_declaration(declarations, Field.MANUFACTURER_NAME_ADDRESS) or find_declaration(declarations, Field.IMPORTER_NAME_ADDRESS)
    decl_country = find_declaration(declarations, Field.COUNTRY_OF_ORIGIN)
    consulted = [d for d in [decl_identity, decl_country] if d]
    methods = methods_used_for(consulted)

    if declaration_found(decl_identity) and declaration_found(decl_country):
        return RuleOutcome(
            verdict=InternalVerdict.COMPLIANT,
            reason_code="BONDED_WAREHOUSE_DECLARATIONS_AFFIXED",
            message="Imported package bears required declarations consistent with Rule 4 Explanation-2 (AEO bonded warehouse facility).",
            evidence=[span for d in consulted if d for span in d.evidence],
            methods_used=methods,
        )

    return RuleOutcome(
        verdict=InternalVerdict.MISSING_DECLARATION,
        reason_code="BONDED_WAREHOUSE_DECLARATIONS_ABSENT",
        message="Imported package fails to bear declarations required under Rule 4 Explanation-2 before leaving the bonded warehouse.",
        expected="Identity and country of origin declarations affixed before leaving bonded warehouse",
        methods_used=methods,
    )


RULE_04_SPEC = RuleSpec(
    rule_id="R04_MANDATORY_LABEL",
    title="Mandatory declarations on pre-packaged commodity",
    citation=CIT_RULE_04_BASE,
    effective_from=date(2011, 3, 7),
    evaluate_fn=evaluate_rule_04,
)

RULE_04_EXPLANATION_2_SPEC = RuleSpec(
    rule_id="R04_EXPLANATION_2_BONDED",
    title="Bonded warehouse declaration for AEO certified importers",
    citation=CIT_RULE_04_EXPLANATION_2_2026,
    effective_from=date(2026, 6, 1),
    evaluate_fn=evaluate_rule_04_explanation_2,
)
