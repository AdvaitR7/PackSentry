"""
Rule 6: Declarations on Principal Display Panel and Other Panels.
Split into eight independent statutory checks per Task E5 and ADR-0005.
"""

from datetime import date
import re
from typing import List, Optional
from lmpc_schema import (
    CommodityCategory,
    DeclarationSet,
    Field,
    ImportStatus,
    InternalVerdict,
    ParsedAddress,
    ParsedDate,
    ParsedPrice,
    PricePrefixForm,
    ProductContext,
)

from .citations import (
    CIT_RULE_06_1_A,
    CIT_RULE_06_1_B,
    CIT_RULE_06_1_C,
    CIT_RULE_06_1_D,
    CIT_RULE_06_1_E,
    CIT_RULE_06_1_F,
    CIT_RULE_06_2,
    CIT_RULE_06_COUNTRY_OF_ORIGIN,
)
from .helpers import declaration_found, find_declaration, methods_used_for, raw_text_of
from .spec import RuleOutcome, RuleSpec


# -------------------------------------------------------------------------
# 1. R6_1_A_IDENTITY: Manufacturer, Packer or Importer Name and Address
# -------------------------------------------------------------------------
def evaluate_r6_1_a(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl_mfg = find_declaration(declarations, Field.MANUFACTURER_NAME_ADDRESS)
    decl_pkr = find_declaration(declarations, Field.PACKER_NAME_ADDRESS)
    decl_imp = find_declaration(declarations, Field.IMPORTER_NAME_ADDRESS)

    candidates = [d for d in [decl_imp, decl_mfg, decl_pkr] if declaration_found(d)]

    if not candidates:
        for d in declarations.declarations:
            txt = (d.raw_value or "").lower()
            if any(k in txt for k in ["import", "mfd", "mfg", "manufactur", "packed by", "pkd", "mkd", "mfr"]):
                candidates.append(d)
                break

    methods = methods_used_for(candidates) if candidates else []

    if not candidates:
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="MANUFACTURER_IDENTITY_ABSENT",
            message="Package fails to declare name and complete address of the manufacturer, packer, or importer.",
            expected="Name and complete address of manufacturer/packer/importer",
            methods_used=methods,
        )

    # Check candidates in order: if ANY candidate (importer, manufacturer, packer)
    # provides a compliant address, Rule 6(1)(a) is satisfied!
    compliant_candidate = None
    last_failure: Optional[RuleOutcome] = None

    for candidate in candidates:
        raw_val = raw_text_of(candidate) or ""
        parsed = candidate.parsed

        if isinstance(parsed, ParsedAddress):
            has_location = (parsed.has_city or parsed.has_state) or (parsed.pin_code is not None)
            has_details = (
                parsed.has_premises_number
                or parsed.has_street
                or len(raw_val.split(",")) >= 2
                or len(raw_val.strip()) >= 15
            )
            if has_location or has_details:
                compliant_candidate = candidate
                break
            else:
                last_failure = RuleOutcome(
                    verdict=InternalVerdict.NON_COMPLIANT,
                    reason_code="INCOMPLETE_ADDRESS_RULE_10",
                    message="Address declaration is incomplete under Rule 10 (missing premises/street or city/PIN).",
                    observed=raw_val,
                    expected="Complete postal address with premises/street and city/PIN code",
                    evidence=candidate.evidence,
                    ocr_confidence=candidate.ocr_confidence,
                    extraction_confidence=candidate.extraction_confidence,
                    methods_used=methods,
                )
        elif len(raw_val.strip()) >= 10:
            compliant_candidate = candidate
            break

    if compliant_candidate:
        raw_val = raw_text_of(compliant_candidate) or ""
        return RuleOutcome(
            verdict=InternalVerdict.COMPLIANT,
            reason_code="IDENTITY_AND_ADDRESS_COMPLIANT",
            message="Name and address of responsible commercial entity declared in compliance with Rule 6(1)(a) and Rule 10.",
            observed=raw_val,
            expected="Name and address of manufacturer/packer/importer",
            evidence=compliant_candidate.evidence,
            ocr_confidence=compliant_candidate.ocr_confidence,
            extraction_confidence=compliant_candidate.extraction_confidence,
            methods_used=methods,
        )

    if last_failure:
        return last_failure

    primary = candidates[0]
    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="IDENTITY_AND_ADDRESS_COMPLIANT",
        message="Name and address declared in compliance with Rule 6(1)(a).",
        observed=raw_text_of(primary) or "",
        expected="Name and address of manufacturer/packer/importer",
        evidence=primary.evidence,
        ocr_confidence=primary.ocr_confidence,
        extraction_confidence=primary.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 2. R6_1_B_GENERIC_NAME: Common or Generic Name
# -------------------------------------------------------------------------
def evaluate_r6_1_b(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.COMMON_GENERIC_NAME)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="GENERIC_NAME_ABSENT",
            message="Common or generic name of the pre-packaged commodity is missing (Rule 6(1)(b)).",
            expected="Common or generic name of commodity",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="GENERIC_NAME_DECLARED",
        message="Common or generic name declared on package.",
        observed=raw_val,
        expected="Common or generic name",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 3. R6_1_C_NET_QUANTITY: Net Quantity Presence
# -------------------------------------------------------------------------
def evaluate_r6_1_c(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.NET_QUANTITY)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="NET_QUANTITY_ABSENT",
            message="Net quantity declaration is absent from the package (Rule 6(1)(c)).",
            expected="Net quantity in standard SI units",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="NET_QUANTITY_DECLARED",
        message="Net quantity declared on package.",
        observed=raw_val,
        expected="Net quantity declaration",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 4. R6_1_D_DATE: Month and Year of Manufacture/Packing/Import
# -------------------------------------------------------------------------
def evaluate_r6_1_d(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.DATE_OF_MANUFACTURE_PACKING_IMPORT)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="MANUFACTURE_DATE_ABSENT",
            message="Month and year of manufacture, packing, or import is absent (Rule 6(1)(d)).",
            expected="Month and year of manufacture/packing/import",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    parsed = decl.parsed

    if isinstance(parsed, ParsedDate):
        if parsed.month < 1 or parsed.month > 12 or parsed.year < 2000 or parsed.year > 2040:
            return RuleOutcome(
                verdict=InternalVerdict.NON_COMPLIANT,
                reason_code="INVALID_DATE_FORMAT",
                message=f"Date declaration '{raw_val}' contains invalid month or year values.",
                observed=raw_val,
                expected="Valid MM/YYYY or Month Year",
                evidence=decl.evidence,
                ocr_confidence=decl.ocr_confidence,
                extraction_confidence=decl.extraction_confidence,
                methods_used=methods,
            )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="MANUFACTURE_DATE_COMPLIANT",
        message="Date of manufacture/packing declared in compliance with Rule 6(1)(d).",
        observed=raw_val,
        expected="Month and year of manufacture/packing",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 5. R6_1_E_RSP_FORM: Retail Sale Price (MRP Form)
# -------------------------------------------------------------------------
def evaluate_r6_1_e(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    """
    Rule 6(1)(e) read with Rule 2(m) retail sale price verification is disabled; evaluated as compliant.
    """
    decl = find_declaration(declarations, Field.RETAIL_SALE_PRICE)
    methods = methods_used_for([decl]) if decl else []

    raw_val = raw_text_of(decl) if decl else None

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="MRP_RULE_DISABLED",
        message="Rule 6(1)(e) read with Rule 2(m) retail sale price verification is disabled; evaluated as compliant.",
        observed=raw_val or "MRP verification bypassed (evaluated as compliant)",
        expected="MRP in prescribed form",
        evidence=decl.evidence if decl else [],
        ocr_confidence=decl.ocr_confidence if decl else 1.0,
        extraction_confidence=decl.extraction_confidence if decl else 1.0,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 6. R6_1_F_DIMENSIONS: Commodity Dimensions (where applicable)
# -------------------------------------------------------------------------
def evaluate_r6_1_f(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    # Applies to commodities where dimensions are relevant (textiles, sheets, containers, etc.)
    decl = find_declaration(declarations, Field.COMMODITY_DIMENSIONS)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        # Only required for dimensional commodity categories
        if context.commodity_category in [
            CommodityCategory.TEXTILE,
            CommodityCategory.SHEET_PRODUCT,
            CommodityCategory.CONTAINER_TYPE,
        ]:
            return RuleOutcome(
                verdict=InternalVerdict.MISSING_DECLARATION,
                reason_code="DIMENSIONS_ABSENT",
                message=f"Commodity dimensions are required for {context.commodity_category.value} but absent (Rule 6(1)(f)).",
                expected="Dimensions in standard SI units",
                methods_used=methods,
            )
        return RuleOutcome(
            verdict=InternalVerdict.COMPLIANT,
            reason_code="DIMENSIONS_NOT_MANDATORY_FOR_CATEGORY",
            message="Commodity category does not mandate separate dimension declaration under Rule 6(1)(f).",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="DIMENSIONS_DECLARED",
        message="Commodity dimensions declared on package.",
        observed=raw_val,
        expected="Dimensions declaration",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 7. R6_2_CONSUMER_CARE: Consumer Care Details
# -------------------------------------------------------------------------
def evaluate_r6_2(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.CONSUMER_CARE)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        # Fallback check across all declarations for customer care information
        for d in declarations.declarations:
            txt = (d.raw_value or "").lower()
            if any(k in txt for k in ["care", "helpline", "feedback", "consumer", "customer", "@", "toll", "contact", "call"]):
                decl = d
                break

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.MISSING_DECLARATION,
            reason_code="CONSUMER_CARE_ABSENT",
            message="Consumer care cell details are absent from the package (Rule 6(2)).",
            expected="Consumer care contact details (name/designation, address, telephone, email)",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    lower_raw = raw_val.lower()

    # Must contain at least telephone number or email address or care contact
    has_contact = any(marker in lower_raw for marker in [
        "tel", "phone", "@", "email", "toll free", "helpline", "care", "call", "write to", "feedback", "contact", "reach us"
    ])
    if not has_contact:
        return RuleOutcome(
            verdict=InternalVerdict.NON_COMPLIANT,
            reason_code="CONSUMER_CARE_CONTACT_INCOMPLETE",
            message="Consumer care declaration lacks specific telephone number or email address.",
            observed=raw_val,
            expected="Consumer care cell with telephone and/or email address",
            evidence=decl.evidence,
            ocr_confidence=decl.ocr_confidence,
            extraction_confidence=decl.extraction_confidence,
            methods_used=methods,
        )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="CONSUMER_CARE_COMPLIANT",
        message="Consumer care details declared in compliance with Rule 6(2).",
        observed=raw_val,
        expected="Consumer care contact details",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 8. R6_COUNTRY_OF_ORIGIN: Country of Origin for Imported Goods
# -------------------------------------------------------------------------
def evaluate_r6_country_of_origin(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.COUNTRY_OF_ORIGIN)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        if context.import_status == ImportStatus.IMPORTED:
            return RuleOutcome(
                verdict=InternalVerdict.MISSING_DECLARATION,
                reason_code="COUNTRY_OF_ORIGIN_ABSENT",
                message="Imported package fails to declare country of origin/manufacture (Rule 6(1)(a) import proviso & Rule 6(10)).",
                expected="Country of origin declaration",
                methods_used=methods,
            )
        # For domestic or unknown, country of origin is not legally mandatory under LMPC
        return RuleOutcome(
            verdict=InternalVerdict.COMPLIANT,
            reason_code="DOMESTIC_NOT_MANDATED",
            message="Country of origin is not mandatory for domestic commodities.",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="COUNTRY_OF_ORIGIN_DECLARED",
        message="Country of origin declared on package.",
        observed=raw_val,
        expected="Country of origin",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# Rule Specifications
RULE_06_SPECS: List[RuleSpec] = [
    RuleSpec(
        rule_id="R6_1_A_IDENTITY",
        title="Manufacturer, packer or importer identity and complete address",
        citation=CIT_RULE_06_1_A,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r6_1_a,
    ),
    RuleSpec(
        rule_id="R6_1_B_GENERIC_NAME",
        title="Common or generic name of commodity",
        citation=CIT_RULE_06_1_B,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r6_1_b,
    ),
    RuleSpec(
        rule_id="R6_1_C_NET_QUANTITY",
        title="Net quantity declaration on package",
        citation=CIT_RULE_06_1_C,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r6_1_c,
    ),
    RuleSpec(
        rule_id="R6_1_D_DATE",
        title="Month and year of manufacture, packing or import",
        citation=CIT_RULE_06_1_D,
        effective_from=date(2011, 3, 7),
        displaced_for_categories=(
            CommodityCategory.FOOD,
            CommodityCategory.COSMETIC,
            CommodityCategory.SEEDS,
        ),
        displacement_reason_code="DATE_DISPLACED_BY_SPECIALIZED_STATUTE",
        displacement_message="Under Rule 6(1)(d) provisos, date declaration is governed by food law (FSSAI), Drugs & Cosmetics Rules 1945, or Seeds Act 1966.",
        evaluate_fn=evaluate_r6_1_d,
    ),
    RuleSpec(
        rule_id="R6_1_E_RSP_FORM",
        title="Retail sale price form (MRP incl. of all taxes)",
        citation=CIT_RULE_06_1_E,
        effective_from=date(2011, 3, 7),
        displaced_for_categories=(CommodityCategory.ALCOHOL,),
        displacement_reason_code="RSP_DISPLACED_BY_STATE_EXCISE",
        displacement_message="Under Rule 6(1)(e) proviso, retail sale price of alcoholic liquor is governed by State excise laws.",
        evaluate_fn=evaluate_r6_1_e,
    ),
    RuleSpec(
        rule_id="R6_1_F_DIMENSIONS",
        title="Commodity dimensions where applicable",
        citation=CIT_RULE_06_1_F,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r6_1_f,
    ),
    RuleSpec(
        rule_id="R6_2_CONSUMER_CARE",
        title="Consumer care cell contact details",
        citation=CIT_RULE_06_2,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r6_2,
    ),
    RuleSpec(
        rule_id="R6_COUNTRY_OF_ORIGIN",
        title="Country of origin on imported pre-packaged goods",
        citation=CIT_RULE_06_COUNTRY_OF_ORIGIN,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r6_country_of_origin,
    ),
]
