"""
Statutory Rule & Citation Catalog Repository (ADR-0008).

Queries active statutory rules and legal citations as of a specific date.
"""

from datetime import date
from typing import Any, Dict, List, Optional
import asyncpg


async def get_rules_catalog_as_of(
    conn: Optional[asyncpg.Connection],
    as_of_date: date,
) -> List[Dict[str, Any]]:
    """
    Queries rules, versions, and citations active on as_of_date.
    Returns structured catalog entries for the /v1/rules endpoint.
    """
    if conn is None:
        return []

    rows = await conn.fetch(
        """
        SELECT r.id AS rule_id,
               r.title,
               r.description,
               r.category,
               rv.id AS version_id,
               rv.effective_from,
               rv.effective_to,
               c.provision,
               c.instrument,
               c.gsr,
               c.gazette_date,
               c.source_url
        FROM app.rule r
        JOIN app.rule_version rv ON r.id = rv.rule_id
        JOIN app.citation c ON rv.citation_id = c.id
        WHERE rv.effective_from <= $1
          AND (rv.effective_to IS NULL OR rv.effective_to >= $1)
        ORDER BY r.id;
        """,
        as_of_date,
    )
    return [dict(r) for r in rows]
