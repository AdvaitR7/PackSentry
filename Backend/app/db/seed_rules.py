"""
Statutory Rule & Citation Database Synchronizer (ADR-0008, ADR-0013).

Synchronizes the in-memory Python RuleSpec registry with Supabase Postgres tables:
- app.citation
- app.rule
- app.rule_version

Ensures that foreign key constraints on `app.inspection_rule_result` are always satisfied
without needing manual SQL seed scripts or risking code-vs-database drift.
"""

import json
import logging
from typing import Any
from app.rules.registry import get_all_rules

logger = logging.getLogger("packsentry.db.seed_rules")


def get_citation_id_for_rule(rule_id: str) -> str:
    """Generates the canonical citation ID for a given rule_id."""
    return f"cit_{rule_id.lower()}"


def get_version_id_for_rule(rule_id: str) -> str:
    """Generates the canonical rule_version ID for a given rule_id."""
    return f"ver_{rule_id.lower()}_v1"


async def sync_rule_registry(conn: Any) -> int:
    """
    Upserts all active RuleSpec definitions and citations into the app schema.
    Returns the count of rules synchronized.
    """
    if conn is None:
        logger.debug("Database connection unavailable; skipping rule registry sync.")
        return 0

    all_specs = get_all_rules()
    synced_count = 0

    for spec in all_specs:
        citation_id = get_citation_id_for_rule(spec.rule_id)
        version_id = get_version_id_for_rule(spec.rule_id)
        cit = spec.citation

        # 1. Upsert Citation
        await conn.execute(
            """
            INSERT INTO app.citation (
                id, provision, instrument, gsr, gazette_date,
                effective_from, effective_to, source_url, source_sha256
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO UPDATE SET
                provision = EXCLUDED.provision,
                instrument = EXCLUDED.instrument,
                gsr = EXCLUDED.gsr,
                gazette_date = EXCLUDED.gazette_date,
                effective_from = EXCLUDED.effective_from,
                effective_to = EXCLUDED.effective_to,
                source_url = EXCLUDED.source_url,
                source_sha256 = EXCLUDED.source_sha256;
            """,
            citation_id,
            cit.provision,
            cit.instrument,
            cit.gsr,
            cit.gazette_date,
            cit.effective_from or spec.effective_from,
            cit.effective_to or spec.effective_to,
            cit.source_url,
            cit.source_sha256 or "",
        )

        # 2. Upsert Rule
        category = spec.required_category.value if spec.required_category else "GENERAL"
        await conn.execute(
            """
            INSERT INTO app.rule (id, title, description, category)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                category = EXCLUDED.category;
            """,
            spec.rule_id,
            spec.title,
            spec.title,
            category,
        )

        # 3. Upsert Rule Version
        await conn.execute(
            """
            INSERT INTO app.rule_version (
                id, rule_id, citation_id, effective_from, effective_to, required_fields
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                citation_id = EXCLUDED.citation_id,
                effective_from = EXCLUDED.effective_from,
                effective_to = EXCLUDED.effective_to,
                required_fields = EXCLUDED.required_fields;
            """,
            version_id,
            spec.rule_id,
            citation_id,
            spec.effective_from,
            spec.effective_to,
            json.dumps([]),
        )

        synced_count += 1

    logger.info("Synchronized %d statutory rules with app schema.", synced_count)
    return synced_count
