"""
Integration Test Suite: Supabase `app` Schema (ADR-0008 & ADR-0013)
Verifies the live migration enforces citation_id NOT NULL on app.rule_version
and that the app schema carries no anon/authenticated grants.

Requires DATABASE_URL (direct or Supavisor session-mode connection string) in
the environment. Skipped automatically when absent -- no credentials are
fabricated or committed (see Backend/.env.example once created in a later phase).
"""

import os
import pytest

asyncpg = pytest.importorskip("asyncpg")

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set; live Supabase schema checks are opt-in.",
)


@pytest.fixture
async def conn():
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        yield connection
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_app_schema_exists(conn):
    row = await conn.fetchrow(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'app'"
    )
    assert row is not None, "app schema must exist"


@pytest.mark.asyncio
async def test_expected_tables_exist(conn):
    expected = {
        "citation",
        "rule",
        "rule_version",
        "inspection",
        "inspection_image",
        "inspection_rule_result",
    }
    rows = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'app'"
    )
    found = {r["table_name"] for r in rows}
    assert expected.issubset(found), f"Missing tables: {expected - found}"


@pytest.mark.asyncio
async def test_rule_version_citation_id_not_nullable(conn):
    row = await conn.fetchrow(
        """
        SELECT is_nullable FROM information_schema.columns
        WHERE table_schema = 'app' AND table_name = 'rule_version' AND column_name = 'citation_id'
        """
    )
    assert row is not None, "rule_version.citation_id column must exist"
    assert row["is_nullable"] == "NO", "ADR-0008: citation_id must be NOT NULL"


@pytest.mark.asyncio
async def test_no_anon_or_authenticated_grants_on_app_schema(conn):
    rows = await conn.fetch(
        """
        SELECT grantee, privilege_type FROM information_schema.role_usage_grants
        WHERE object_schema = 'app' AND grantee IN ('anon', 'authenticated')
        """
    )
    assert len(rows) == 0, f"app schema must have zero anon/authenticated grants, found: {rows}"


@pytest.mark.asyncio
async def test_rls_enabled_on_all_app_tables(conn):
    rows = await conn.fetch(
        """
        SELECT c.relname, c.relrowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'app' AND c.relkind = 'r'
        """
    )
    assert len(rows) > 0
    for r in rows:
        assert r["relrowsecurity"] is True, f"RLS must be enabled on app.{r['relname']}"


@pytest.mark.asyncio
async def test_inspection_evidence_bucket_is_private(conn):
    row = await conn.fetchrow(
        "SELECT public FROM storage.buckets WHERE id = 'inspection-evidence'"
    )
    assert row is not None, "inspection-evidence bucket must exist"
    assert row["public"] is False, "inspection-evidence bucket must be private"
