"""
Test Suite: Citation Non-Nullability Constraint (ADR-0008)
Validates that RuleResult and rule specifications require a non-null Citation.
Adding or evaluating a rule without an authoritative gazette citation must fail.
"""

from datetime import date
import pytest
from pydantic import ValidationError

from lmpc_schema import (
    ApplicabilityResult,
    ApplicabilityStatus,
    Citation,
    ConfidenceSet,
    InternalVerdict,
    RuleResult,
    UiBucket,
)


def test_rule_result_requires_citation():
    """ADR-0008: RuleResult must reject None or missing citation."""
    with pytest.raises(ValidationError) as exc_info:
        RuleResult(
            rule_id="R13_UNIT_THRESHOLD",
            provision="Rule 13(2), 13(3)",
            title="Correct unit for declared magnitude",
            verdict=InternalVerdict.NON_COMPLIANT,
            ui_bucket=UiBucket.POTENTIAL_NON_COMPLIANCE,
            reason_code="TEST_VIOLATION",
            message="Test message",
            confidence=ConfidenceSet(ocr=0.95, extraction=0.95),
            applicability=ApplicabilityResult(status=ApplicabilityStatus.APPLICABLE),
            citation=None,  # Explicitly None -> must fail validation!
        )
    errors = str(exc_info.value)
    assert "citation" in errors or "Input should be a valid dictionary or instance of Citation" in errors


def test_citation_fields_mandatory():
    """ADR-0008: Citation itself requires provision, instrument, gsr, gazette_date, and source_url."""
    with pytest.raises(ValidationError):
        Citation(
            provision="Rule 13(2)",
            instrument="Legal Metrology Rules",
            gsr="G.S.R. 202(E)",
            # Missing gazette_date and source_url!
        )


def test_valid_citation_instantiation():
    """Valid citation passes with full primary-source metadata."""
    cit = Citation(
        provision="Rule 13(5)(ii)",
        instrument="Legal Metrology (Packaged Commodities) Amendment Rules, 2021",
        gsr="G.S.R. 779(E)",
        gazette_date=date(2021, 11, 2),
        effective_from=date(2022, 4, 1),
        source_url="https://egazette.gov.in/WriteReadData/2021/230946.pdf",
    )
    assert cit.provision == "Rule 13(5)(ii)"
    assert cit.gsr == "G.S.R. 779(E)"
    assert cit.effective_from == date(2022, 4, 1)
