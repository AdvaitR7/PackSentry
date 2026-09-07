"""
Central Statutory Rule Registry (ADR-0001, ADR-0008).
Maintains all registered LMPC RuleSpec instances and supports temporal querying (GET /v1/rules?as_of=).
"""

from datetime import date
from typing import Dict, List, Optional

from .deferred import DEFERRED_SPECS
from .rule_03 import RULE_03_SPEC
from .rule_04 import RULE_04_EXPLANATION_2_SPEC, RULE_04_SPEC
from .rule_06 import RULE_06_SPECS
from .rule_12 import RULE_12_6_MISLEADING_SPEC, RULE_12_QUANTITY_BASIS_SPEC
from .rule_13 import RULE_13_SPECS
from .rules_14_17 import RULES_14_17_SPECS
from .spec import RuleSpec

_ALL_SPECS: List[RuleSpec] = [
    RULE_03_SPEC,
    RULE_04_SPEC,
    RULE_04_EXPLANATION_2_SPEC,
    *RULE_06_SPECS,
    RULE_12_QUANTITY_BASIS_SPEC,
    RULE_12_6_MISLEADING_SPEC,
    *RULE_13_SPECS,
    *RULES_14_17_SPECS,
    *DEFERRED_SPECS,
]

_RULE_MAP: Dict[str, RuleSpec] = {spec.rule_id: spec for spec in _ALL_SPECS}


def get_all_rules() -> List[RuleSpec]:
    """Returns all registered statutory rules and deferred items."""
    return list(_ALL_SPECS)


def get_rule(rule_id: str) -> Optional[RuleSpec]:
    """Lookup a single RuleSpec by its identifier."""
    return _RULE_MAP.get(rule_id)


def get_rules_as_of(as_of: date) -> List[RuleSpec]:
    """
    Returns rules in effect as of a given date (ADR-0008 temporal ruleset catalog).
    Used by GET /v1/rules?as_of= to demonstrate legal temporal versioning.
    """
    active = []
    for spec in _ALL_SPECS:
        if spec.effective_from <= as_of:
            if spec.effective_to is None or as_of < spec.effective_to:
                active.append(spec)
    return active
