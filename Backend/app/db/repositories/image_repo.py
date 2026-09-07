"""
Inspection Evidence Image Metadata Repository (ADR-0013).

Manages `app.inspection_image`: pointers to private Supabase Storage evidence,
never the image bytes themselves.
"""

from typing import Any, Dict, List, Optional
import asyncpg


async def record_inspection_images(
    conn: Optional[asyncpg.Connection],
    images: List[Dict[str, Any]],
) -> None:
    """
    Bulk inserts image metadata rows.
    Each image dict requires: id, inspection_id, role, storage_path, sha256, width, height.
    """
    if conn is None or not images:
        return
    await conn.executemany(
        """
        INSERT INTO app.inspection_image (
            id, inspection_id, role, storage_path, sha256, width, height
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7);
        """,
        [
            (
                img["id"],
                img["inspection_id"],
                img["role"],
                img["storage_path"],
                img["sha256"],
                img["width"],
                img["height"],
            )
            for img in images
        ],
    )


async def get_images_for_inspection(
    conn: Optional[asyncpg.Connection],
    inspection_id: str,
) -> List[Dict[str, Any]]:
    """Fetches evidence image metadata for signed URL minting and rendering."""
    if conn is None:
        return []
    rows = await conn.fetch(
        """
        SELECT id, role, storage_path, sha256, width, height
        FROM app.inspection_image
        WHERE inspection_id = $1
        ORDER BY role;
        """,
        inspection_id,
    )
    return [dict(r) for r in rows]
