"""
Deferred Rules (ADR-0012).
Rules 7 and 8 are deliberately deferred from Prototype A and return NOT_EVALUATED
with distinct, truthful reason codes.
"""

from datetime import date
from typing import List

from .citations import CIT_RULE_07, CIT_RULE_08
from .spec import RuleSpec

DEFERRED_SPECS: List[RuleSpec] = [
    RuleSpec(
        rule_id="R07_FONT_HEIGHT",
        title="Minimum height of numerals and letters",
        citation=CIT_RULE_07,
        effective_from=date(2011, 3, 7),
        deferred=True,
        deferred_reason_code="ABSOLUTE_SCALE_UNAVAILABLE",
        deferred_message=(
            "Minimum character height verification in millimeters is deferred: "
            "monocular photographs cannot recover absolute millimeter scale without "
            "a physical reference target (e.g. ArUco card) per ADR-0012."
        ),
    ),
    RuleSpec(
        rule_id="R08_CLEAR_SPACE",
        title="Clear space surrounding net quantity numerals",
        citation=CIT_RULE_08,
        effective_from=date(2011, 3, 7),
        deferred=True,
        deferred_reason_code="GEOMETRY_CAPABILITY_DEFERRED",
        deferred_message=(
            "Clear space verification as a multiple of numeral height is deferred: "
            "numeral exclusion-zone polygon estimation is sequenced after core prototype (ADR-0012)."
        ),
    ),
]
