"""
Evidence Retention and Scratch Pruning Maintenance Utility (ADR-0015).

Statutory & Privacy Compliance Invariants:
1. Retains prototype inspection evidence for a bounded window (default: 30 days)
   while building the evaluation corpus.
2. Evidence objects are purged through the Supabase Storage API (delete_evidence),
   never through raw `storage.objects` table manipulation.
3. Transient scratch directories older than 24 hours are reclaimed to prevent disk exhaustion.
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import shutil
import time
from typing import List, Optional, Tuple

from app.db.scratch import DEFAULT_SCRATCH_ROOT
from app.db.session import acquire_connection, get_pool, init_pool
from app.db.storage import delete_evidence, is_configured as is_storage_configured

logger = logging.getLogger("packsentry.tasks.retention")


def prune_local_scratch(
    max_age_hours: float = 24.0,
    scratch_root: Optional[Path] = None,
    dry_run: bool = False,
) -> int:
    """
    Scans local scratch disk root and removes directories modified longer ago
    than max_age_hours.

    Returns count of pruned directories.
    """
    root = scratch_root or DEFAULT_SCRATCH_ROOT
    if not root.exists():
        logger.debug("Scratch root directory does not exist: %s", root)
        return 0

    cutoff_timestamp = time.time() - (max_age_hours * 3600)
    pruned_count = 0

    for item in root.iterdir():
        if not item.is_dir():
            continue

        try:
            stat_info = item.stat()
            if stat_info.st_mtime < cutoff_timestamp:
                logger.info(
                    "%s old scratch directory: %s (mtime: %s)",
                    "[DRY-RUN] Would remove" if dry_run else "Removing",
                    item,
                    datetime.fromtimestamp(stat_info.st_mtime, timezone.utc).isoformat(),
                )
                if not dry_run:
                    shutil.rmtree(item, ignore_errors=True)
                pruned_count += 1
        except Exception as exc:
            logger.warning("Error inspecting or pruning scratch dir %s: %s", item, exc)

    return pruned_count


async def prune_storage_evidence(
    older_than_days: int = 30,
    pool=None,
    dry_run: bool = False,
) -> int:
    """
    Queries inspections created prior to (now - older_than_days) that have terminal status,
    collects associated image storage paths, and deletes them via the Supabase Storage API.

    Returns count of deleted storage objects.
    """
    if not is_storage_configured():
        logger.info("Supabase storage not configured; skipping storage evidence pruning.")
        return 0

    active_pool = pool or get_pool()
    if active_pool is None:
        logger.info("Database pool not initialized; skipping DB-linked storage retention.")
        return 0

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    pruned_objects_count = 0

    try:
        async with acquire_connection() as conn:
            # 1. Find images for inspections completed before cutoff date
            query = """
                SELECT ii.image_id, ii.storage_path
                FROM app.inspection_image ii
                JOIN app.inspection i ON ii.inspection_id = i.inspection_id
                WHERE i.created_at < $1
                  AND i.status IN ('COMPLETE', 'FAILED')
                  AND ii.storage_path IS NOT NULL
                LIMIT 500;
            """
            rows = await conn.fetch(query, cutoff_date)

            if not rows:
                logger.info("No expired storage evidence found older than %d days.", older_than_days)
                return 0

            storage_paths = [r["storage_path"] for r in rows if r["storage_path"]]
            image_ids = [r["image_id"] for r in rows]

            logger.info(
                "%s %d evidence image objects from Supabase Storage.",
                "[DRY-RUN] Would delete" if dry_run else "Deleting",
                len(storage_paths),
            )

            if not dry_run and storage_paths:
                # Execute deletion via Supabase Storage API
                delete_evidence(storage_paths)

                # Null out storage_path in database to reflect retention purge
                await conn.execute(
                    """
                    UPDATE app.inspection_image
                    SET storage_path = NULL
                    WHERE image_id = ANY($1::text[]);
                    """,
                    image_ids,
                )

            pruned_objects_count = len(storage_paths)

    except Exception as exc:
        logger.error("Error executing storage evidence retention prune: %s", exc)

    return pruned_objects_count


async def run_retention_maintenance(
    scratch_max_age_hours: float = 24.0,
    storage_retention_days: int = 30,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Executes both local scratch pruning and cloud storage retention cleanup.
    Returns (pruned_scratch_dirs, pruned_storage_objects).
    """
    logger.info(
        "Starting PackSentry retention maintenance (scratch_cutoff=%sh, storage_cutoff=%sd, dry_run=%s)",
        scratch_max_age_hours,
        storage_retention_days,
        dry_run,
    )

    # 1. Prune local temporary scratch files
    pruned_scratch = prune_local_scratch(
        max_age_hours=scratch_max_age_hours,
        dry_run=dry_run,
    )

    # 2. Prune expired cloud storage evidence
    pruned_storage = await prune_storage_evidence(
        older_than_days=storage_retention_days,
        dry_run=dry_run,
    )

    logger.info(
        "Retention maintenance completed: %d scratch dirs cleaned, %d storage objects pruned.",
        pruned_scratch,
        pruned_storage,
    )
    return pruned_scratch, pruned_storage


def main():
    """CLI entrypoint for retention cleanup."""
    parser = argparse.ArgumentParser(description="PackSentry Evidence & Scratch Retention Maintenance")
    parser.add_argument("--dry-run", action="store_true", help="Report expired items without deleting them.")
    parser.add_argument("--days", type=int, default=30, help="Retention period for storage evidence in days (default: 30)")
    parser.add_argument("--scratch-hours", type=float, default=24.0, help="Local scratch directory age in hours (default: 24)")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    async def _async_main():
        pool = await init_pool()
        try:
            await run_retention_maintenance(
                scratch_max_age_hours=args.scratch_hours,
                storage_retention_days=args.days,
                dry_run=args.dry_run,
            )
        finally:
            if pool:
                await pool.close()

    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
