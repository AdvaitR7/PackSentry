"""
Tests for Evidence Retention and Scratch Directory Cleanup (ADR-0015).
"""

import os
from pathlib import Path
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.tasks.retention import (
    prune_local_scratch,
    prune_storage_evidence,
    run_retention_maintenance,
)


def test_prune_local_scratch_cleans_only_expired(tmp_path: Path):
    """Verifies scratch cleanup removes directories older than cutoff and retains recent ones."""
    old_dir = tmp_path / "old_inspection_1"
    old_dir.mkdir()
    (old_dir / "pdp_original.jpg").write_bytes(b"old")

    new_dir = tmp_path / "new_inspection_2"
    new_dir.mkdir()
    (new_dir / "pdp_original.jpg").write_bytes(b"new")

    # Set old_dir mtime to 48 hours ago
    past_time = time.time() - (48 * 3600)
    os.utime(old_dir, (past_time, past_time))

    # Test Dry-Run: reports 1 pruned, but does not delete
    pruned_dry = prune_local_scratch(max_age_hours=24.0, scratch_root=tmp_path, dry_run=True)
    assert pruned_dry == 1
    assert old_dir.exists()
    assert new_dir.exists()

    # Test Real Run: deletes old_dir, preserves new_dir
    pruned_real = prune_local_scratch(max_age_hours=24.0, scratch_root=tmp_path, dry_run=False)
    assert pruned_real == 1
    assert not old_dir.exists()
    assert new_dir.exists()


def test_prune_local_scratch_nonexistent_root(tmp_path: Path):
    """Gracefully handles nonexistent scratch directory."""
    nonexistent = tmp_path / "does_not_exist"
    assert prune_local_scratch(scratch_root=nonexistent) == 0


@pytest.mark.asyncio
async def test_prune_storage_evidence_unconfigured_skips():
    """Returns 0 when Supabase Storage is not configured."""
    with patch("app.tasks.retention.is_storage_configured", return_value=False):
        pruned = await prune_storage_evidence(older_than_days=30)
        assert pruned == 0


@pytest.mark.asyncio
async def test_prune_storage_evidence_executes_delete():
    """Verifies that expired storage evidence is deleted through the Storage API and DB updated."""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {"image_id": "img1", "storage_path": "inspections/insp1/pdp_original.jpg"},
        {"image_id": "img2", "storage_path": "inspections/insp1/back_original.jpg"},
    ]
    mock_conn.execute.return_value = None

    class MockPoolContext:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc, tb):
            pass

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockPoolContext()

    with patch("app.tasks.retention.is_storage_configured", return_value=True), \
         patch("app.tasks.retention.get_pool", return_value=mock_pool), \
         patch("app.tasks.retention.acquire_connection", return_value=MockPoolContext()), \
         patch("app.tasks.retention.delete_evidence") as mock_delete:

        # Dry run
        pruned_dry = await prune_storage_evidence(older_than_days=30, pool=mock_pool, dry_run=True)
        assert pruned_dry == 2
        mock_delete.assert_not_called()

        # Real run
        pruned_real = await prune_storage_evidence(older_than_days=30, pool=mock_pool, dry_run=False)
        assert pruned_real == 2
        mock_delete.assert_called_once_with([
            "inspections/insp1/pdp_original.jpg",
            "inspections/insp1/back_original.jpg",
        ])
        assert mock_conn.execute.called


@pytest.mark.asyncio
async def test_run_retention_maintenance_orchestration(tmp_path: Path):
    """Verifies run_retention_maintenance coordinates both cleanup phases."""
    with patch("app.tasks.retention.prune_local_scratch", return_value=3) as mock_scratch, \
         patch("app.tasks.retention.prune_storage_evidence", new_callable=AsyncMock) as mock_storage:
        mock_storage.return_value = 5

        s_count, st_count = await run_retention_maintenance(
            scratch_max_age_hours=12.0,
            storage_retention_days=15,
            dry_run=True,
        )

        assert s_count == 3
        assert st_count == 5
        mock_scratch.assert_called_once_with(max_age_hours=12.0, dry_run=True)
        mock_storage.assert_called_once_with(older_than_days=15, dry_run=True)
