"""
Statutory Rules Catalog API Router (ADR-0008).

Exposes GET /v1/rules?as_of= for temporal ruleset inspection.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.rules.registry import get_rules_as_of

router = APIRouter(tags=["Rules"])


class RuleCatalogEntry(BaseModel):
    rule_id: str
    title: str
    provision: str
    instrument: str
    gsr: str
    gazette_date: date
    effective_from: date
    effective_to: Optional[date] = None
    source_url: str


@router.get("/rules", response_model=List[RuleCatalogEntry])
async def list_rules(
    as_of: Optional[date] = Query(
        default=None,
        description="Temporal date filter for statutory rules in force (ISO YYYY-MM-DD)",
    ),
):
    """
    Returns the legal rules in effect as of the specified date.
    Defaults to today's date if omitted.
    """
    query_date = as_of or date.today()
    active_specs = get_rules_as_of(query_date)

    entries = []
    for spec in active_specs:
        cit = spec.citation
        entries.append(
            RuleCatalogEntry(
                rule_id=spec.rule_id,
                title=spec.title,
                provision=cit.provision,
                instrument=cit.instrument,
                gsr=cit.gsr,
                gazette_date=cit.gazette_date,
                effective_from=spec.effective_from,
                effective_to=spec.effective_to,
                source_url=cit.source_url,
            )
        )

    return entries
