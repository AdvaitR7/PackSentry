"""
Rule 13: Units of Weight and Measure, Prescribed Symbols, and Thresholds.
Includes ADR-0011 legal currency implementation of Rule 13(5)(ii) per G.S.R. 779(E) (2021 amendment).
"""

import re
from datetime import date
from lmpc_schema import (
    DeclarationSet,
    DimensionKind,
    Field,
    InternalVerdict,
    ParsedQuantity,
    ProductContext,
)

from .citations import (
    CIT_RULE_13_NO_ARCHAIC_COUNT,
    CIT_RULE_13_NUMBER_SYMBOL_2021,
    CIT_RULE_13_SI_ONLY,
    CIT_RULE_13_UNIT_THRESHOLD,
)
from .helpers import declaration_found, find_declaration, methods_used_for, raw_text_of
from .spec import RuleOutcome, RuleSpec


_ARCHAIC_COUNT_WORDS = ["dozen", "doz", "score", "gross"]
_NON_SI_OR_INVALID_SYMBOLS = ["gms", "gm", "oz", "lb", "lbs", "ltr", "ltrs", "kilo", "kilos"]
_LAWFUL_COUNT_TERMS = ["number", "unit", "piece", "pieces", "pair", "pairs", "set", "sets", "n", "u"]


# -------------------------------------------------------------------------
# 1. R13_UNIT_THRESHOLD: Mass and Volume Magnitude Thresholds
# -------------------------------------------------------------------------
def evaluate_r13_unit_threshold(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.NET_QUANTITY)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.NOT_CAPTURED,
            reason_code="NET_QUANTITY_ABSENT_FOR_THRESHOLD_CHECK",
            message="Cannot evaluate unit threshold: net quantity declaration is absent.",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    parsed = decl.parsed

    if isinstance(parsed, ParsedQuantity):
        dim = parsed.dimension
        mag = parsed.magnitude
        u_raw = parsed.unit_raw.strip().lower()

        # Rule 13(2)(a) & 13(3)(a): Mass
        if dim == DimensionKind.MASS:
            # Check if magnitude in grams is >= 1000
            if u_raw in ["g", "gm", "gms", "gram", "grams"] and mag >= 1000.0:
                expected_kg = f"{mag / 1000.0:g} kg"
                return RuleOutcome(
                    verdict=InternalVerdict.NON_COMPLIANT,
                    reason_code="MAGNITUDE_AT_OR_ABOVE_THRESHOLD_IN_SUBMULTIPLE",
                    message=(
                        f"Net quantity is declared as {mag:g} {u_raw}. Rule 13(3)(a) requires "
                        f"quantities of one kilogram or more to be expressed in kilograms."
                    ),
                    observed=raw_val,
                    expected=expected_kg,
                    evidence=decl.evidence,
                    ocr_confidence=decl.ocr_confidence,
                    extraction_confidence=decl.extraction_confidence,
                    methods_used=methods,
                )

        # Rule 13(2)(f) & 13(3)(e): Volume
        elif dim == DimensionKind.VOLUME:
            if u_raw in ["ml", "millilitre", "milliliter", "millilitres"] and mag >= 1000.0:
                expected_l = f"{mag / 1000.0:g} L"
                return RuleOutcome(
                    verdict=InternalVerdict.NON_COMPLIANT,
                    reason_code="VOLUME_AT_OR_ABOVE_THRESHOLD_IN_SUBMULTIPLE",
                    message=(
                        f"Net volume is declared as {mag:g} {u_raw}. Rule 13(3)(e) requires "
                        f"quantities of one litre or more to be expressed in litres (L)."
                    ),
                    observed=raw_val,
                    expected=expected_l,
                    evidence=decl.evidence,
                    ocr_confidence=decl.ocr_confidence,
                    extraction_confidence=decl.extraction_confidence,
                    methods_used=methods,
                )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="UNIT_THRESHOLD_COMPLIANT",
        message="Net quantity unit respects prescribed statutory magnitude thresholds (Rule 13(2), 13(3)).",
        observed=raw_val,
        expected="Prescribed unit according to declared magnitude",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 2. R13_NO_ARCHAIC_COUNT: Prohibition of Archaic Count Units
# -------------------------------------------------------------------------
def evaluate_r13_no_archaic_count(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.NET_QUANTITY)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.NOT_CAPTURED,
            reason_code="NET_QUANTITY_ABSENT_FOR_COUNT_CHECK",
            message="Cannot check archaic count units: net quantity declaration is absent.",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    lower_raw = raw_val.lower()

    for archaic in _ARCHAIC_COUNT_WORDS:
        # Match whole word
        if re.search(rf"\b{re.escape(archaic)}\b", lower_raw):
            return RuleOutcome(
                verdict=InternalVerdict.NON_COMPLIANT,
                reason_code="PROHIBITED_ARCHAIC_COUNT_UNIT",
                message=f"Quantity contains archaic count unit '{archaic}' prohibited by Rule 13(4).",
                observed=raw_val,
                expected="Standard metric count units or number terms",
                evidence=decl.evidence,
                ocr_confidence=decl.ocr_confidence,
                extraction_confidence=decl.extraction_confidence,
                methods_used=methods,
            )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="NO_ARCHAIC_COUNT_UNITS",
        message="Quantity declaration avoids prohibited archaic count units (Rule 13(4)).",
        observed=raw_val,
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 3. R13_SI_ONLY: Prescribed SI Symbols Only
# -------------------------------------------------------------------------
def evaluate_r13_si_only(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.NET_QUANTITY)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.NOT_CAPTURED,
            reason_code="NET_QUANTITY_ABSENT_FOR_SI_CHECK",
            message="Cannot check SI units: net quantity declaration is absent.",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    lower_raw = raw_val.lower()

    # Search for non-SI / non-prescribed symbols
    for non_si in _NON_SI_OR_INVALID_SYMBOLS:
        if re.search(rf"\b{re.escape(non_si)}\b", lower_raw):
            prescribed = "g" if "gm" in non_si else ("L" if "ltr" in non_si else "kg")
            return RuleOutcome(
                verdict=InternalVerdict.NON_COMPLIANT,
                reason_code="NON_PRESCRIBED_UNIT_SYMBOL",
                message=(
                    f"Unit notation contains '{non_si}'. Rule 13(5)(i) mandates strict SI symbols "
                    f"(prescribed symbol: '{prescribed}')."
                ),
                observed=raw_val,
                expected=f"Prescribed SI symbol '{prescribed}'",
                evidence=decl.evidence,
                ocr_confidence=decl.ocr_confidence,
                extraction_confidence=decl.extraction_confidence,
                methods_used=methods,
            )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="SI_UNITS_COMPLIANT",
        message="Net quantity expressed strictly in prescribed SI unit symbols (Rule 13(5)(i)).",
        observed=raw_val,
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


# -------------------------------------------------------------------------
# 4. R13_NUMBER_SYMBOL: Number Terminology (2021 Text — ADR-0011)
# -------------------------------------------------------------------------
def evaluate_r13_number_symbol(declarations: DeclarationSet, context: ProductContext) -> RuleOutcome:
    decl = find_declaration(declarations, Field.NET_QUANTITY)
    methods = methods_used_for([decl])

    if not declaration_found(decl):
        return RuleOutcome(
            verdict=InternalVerdict.NOT_CAPTURED,
            reason_code="NET_QUANTITY_ABSENT_FOR_NUMBER_SYMBOL_CHECK",
            message="Cannot verify number symbol: net quantity declaration is absent.",
            methods_used=methods,
        )

    raw_val = raw_text_of(decl) or ""
    lower_raw = raw_val.lower()

    # ADR-0011: Rule 12 must first resolve the quantity basis to NUMBER.
    # If the declaration is mass or volume, this specific check is NOT_APPLICABLE.
    parsed = decl.parsed
    if isinstance(parsed, ParsedQuantity) and parsed.dimension != DimensionKind.NUMBER:
        return RuleOutcome(
            verdict=InternalVerdict.COMPLIANT,
            reason_code="NOT_SOLD_BY_NUMBER",
            message="Commodity is sold by mass/volume/length, not number; Rule 13(5)(ii) count check is satisfied.",
            observed=raw_val,
            methods_used=methods,
        )

    # If sold by number, verify it mentions one of the 2021 amended statutory terms
    has_lawful_term = any(
        re.search(rf"\b{re.escape(term)}\b", lower_raw) for term in _LAWFUL_COUNT_TERMS
    )

    if not has_lawful_term:
        # Check if raw value has a standalone number without unit
        if re.search(r"^\d+$", raw_val.strip()):
            return RuleOutcome(
                verdict=InternalVerdict.NON_COMPLIANT,
                reason_code="COUNT_WORD_OMITTED",
                message=(
                    "For items sold by number, Rule 13(5)(ii) (as amended by G.S.R. 779(E)) requires "
                    "mentioning the word 'number', 'unit', 'piece', 'pair', 'set' or equivalent representation."
                ),
                observed=raw_val,
                expected="Quantity followed by 'piece', 'pair', 'set', 'unit', or 'number'",
                evidence=decl.evidence,
                ocr_confidence=decl.ocr_confidence,
                extraction_confidence=decl.extraction_confidence,
                methods_used=methods,
            )

    return RuleOutcome(
        verdict=InternalVerdict.COMPLIANT,
        reason_code="COUNT_TERMINOLOGY_COMPLIANT",
        message="Count-based quantity uses lawful statutory terminology per Rule 13(5)(ii) (2021 amendment).",
        observed=raw_val,
        expected="Lawful count word (piece, pair, set, unit, number)",
        evidence=decl.evidence,
        ocr_confidence=decl.ocr_confidence,
        extraction_confidence=decl.extraction_confidence,
        methods_used=methods,
    )


RULE_13_SPECS: List[RuleSpec] = [
    RuleSpec(
        rule_id="R13_UNIT_THRESHOLD",
        title="Prescribed unit according to declared magnitude",
        citation=CIT_RULE_13_UNIT_THRESHOLD,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r13_unit_threshold,
    ),
    RuleSpec(
        rule_id="R13_NO_ARCHAIC_COUNT",
        title="Prohibition of archaic count units (dozen, gross, score)",
        citation=CIT_RULE_13_NO_ARCHAIC_COUNT,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r13_no_archaic_count,
    ),
    RuleSpec(
        rule_id="R13_SI_ONLY",
        title="Mandatory use of prescribed SI unit symbols",
        citation=CIT_RULE_13_SI_ONLY,
        effective_from=date(2011, 3, 7),
        evaluate_fn=evaluate_r13_si_only,
    ),
    RuleSpec(
        rule_id="R13_NUMBER_SYMBOL",
        title="Count-based quantity terminology (amended in 2021)",
        citation=CIT_RULE_13_NUMBER_SYMBOL_2021,
        effective_from=date(2022, 4, 1),
        evaluate_fn=evaluate_r13_number_symbol,
    ),
]
