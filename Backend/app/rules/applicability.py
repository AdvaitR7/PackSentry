"""
Six-Gate Applicability Chain (ADR-0001, ADR-0006).
Evaluates whether a statutory rule applies to a given product inspection context.
Ordered chain: first non-APPLICABLE result wins.
"""

from typing import Optional, Tuple
from lmpc_schema import (
    ApplicabilityGate,
    ApplicabilityResult,
    ApplicabilityStatus,
    CommodityCategory,
    PackageType,
    ProductContext,
)
from .spec import RuleSpec


def check_applicability(spec: RuleSpec, context: ProductContext) -> Tuple[ApplicabilityResult, Optional[str]]:
    """
    Evaluates the six-gate applicability chain for a rule against ProductContext.
    Returns (ApplicabilityResult, error_or_special_flag).
    Special flag "RULE_3_AMBIGUOUS" indicates a contested legal boundary (ADR-0006)
    which produces an INDETERMINATE verdict rather than NOT_APPLICABLE.
    """
    scan_date = context.scan_date

    # Gate 1: TEMPORAL
    if scan_date < spec.effective_from:
        return (
            ApplicabilityResult(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                gate=ApplicabilityGate.TEMPORAL,
                reason_code="RULE_NOT_YET_IN_FORCE",
                message=f"Rule was not in force on scan date {scan_date.isoformat()} (effective from {spec.effective_from.isoformat()}).",
            ),
            None,
        )

    if spec.effective_to and scan_date >= spec.effective_to:
        return (
            ApplicabilityResult(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                gate=ApplicabilityGate.TEMPORAL,
                reason_code="RULE_SUPERSEDED_OR_EXPIRED",
                message=f"Rule expired or was superseded before scan date {scan_date.isoformat()} (effective until {spec.effective_to.isoformat()}).",
            ),
            None,
        )

    # Gate 2: PACKAGE_TYPE
    # Demo covers RETAIL packages. INSTITUTIONAL and INDUSTRIAL packages are excluded
    # while Rule 3(c) is deferred (ADR-0006, §0.1).
    if context.package_type in [PackageType.INSTITUTIONAL, PackageType.INDUSTRIAL]:
        return (
            ApplicabilityResult(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                gate=ApplicabilityGate.PACKAGE_TYPE,
                reason_code="PACKAGE_TYPE_DEFERRED_RULE_3_C",
                message=f"Package type {context.package_type.value} is an institutional/industrial consumer pack under Rule 3(c), which is deferred from this demo scope.",
            ),
            None,
        )

    # Gate 3: RULE_3 (Contested Exclusion Boundary — ADR-0006)
    # Check net quantity > 25 kg / 25 l, or cement/fertilizer/agri produce > 50 kg
    base_qty = context.net_quantity_in_base_units
    base_val = 0.0
    base_unit = ""
    if base_qty is not None:
        if isinstance(base_qty, dict):
            base_val = float(base_qty.get("value", 0.0) or 0.0)
            base_unit = str(base_qty.get("unit", "")).lower()
        else:
            base_val = float(getattr(base_qty, "value", 0.0) or 0.0)
            base_unit = str(getattr(base_qty, "unit", "")).lower()

    is_over_25 = False
    if base_unit in ["kg", "l", "litre", "liter"] and base_val > 25.0:
        is_over_25 = True

    is_cement_fertilizer_agri = context.commodity_category == CommodityCategory.CEMENT_FERTILIZER_AGRI
    is_bulk_bag = is_cement_fertilizer_agri and base_val > 50.0

    if is_over_25 or is_bulk_bag:
        # ADR-0006: Do not silently exclude as NOT_APPLICABLE. The statutory boundary between
        # 3(a) and 3(b) is contested. Return as special ambiguity flag -> yields INDETERMINATE.
        return (
            ApplicabilityResult(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                gate=ApplicabilityGate.RULE_3,
                reason_code="RULE_3_AMBIGUOUS",
                message=(
                    f"Net quantity ({base_val} {base_unit}) exceeds statutory Chapter II threshold. "
                    "Rule 3(a) excludes packages >25 kg/L while Rule 3(b) excludes cement/fertilizer >50 kg. "
                    "Per ADR-0006, this contested boundary is not adjudicated and returns INDETERMINATE."
                ),
            ),
            "RULE_3_AMBIGUOUS",
        )

    # Gate 4: DISPLACEMENT (Statutory provisos deferring to other laws)
    if spec.displaced_for_categories and context.commodity_category in spec.displaced_for_categories:
        reason = spec.displacement_reason_code or "DISPLACED_BY_SPECIALIZED_LAW"
        msg = spec.displacement_message or f"Rule requirement is displaced for {context.commodity_category.value} by specialized statute."
        return (
            ApplicabilityResult(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                gate=ApplicabilityGate.DISPLACEMENT,
                reason_code=reason,
                message=msg,
            ),
            None,
        )

    # Gate 5: CATEGORY (Category-specific declaration rules 14, 16, 17)
    if spec.required_category is not None and context.commodity_category != spec.required_category:
        return (
            ApplicabilityResult(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                gate=ApplicabilityGate.CATEGORY,
                reason_code="CATEGORY_MISMATCH",
                message=f"Rule applies exclusively to commodity category {spec.required_category.value}, not {context.commodity_category.value}.",
            ),
            None,
        )

    # Gate 6: FORM_VARIANT (Rule 12(7) small capacity packages <= 5 cm3)
    # Allows tag/card/tape placement rather than direct package face
    # (Evaluated within specific rules where form layout matters)

    return (
        ApplicabilityResult(
            status=ApplicabilityStatus.APPLICABLE,
            gate=None,
            reason_code=None,
            message=None,
        ),
        None,
    )
