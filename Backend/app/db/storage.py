"""
Supabase Storage Client for Private Evidence Bucket (ADR-0013).

Handles upload, signed URL minting, and deletion against the private
`inspection-evidence` bucket. Uses the SUPABASE_SERVICE_ROLE_KEY, which
must never leave the FastAPI server process.
"""

import logging
import os
from typing import Any, List, Optional

logger = logging.getLogger("packsentry.db.storage")

EVIDENCE_BUCKET = "inspection-evidence"
DEFAULT_SIGNED_URL_TTL_SECONDS = 120

_storage_client: Optional[Any] = None


class StorageUnavailableError(Exception):
    """Raised when Supabase Storage credentials are not configured."""


def get_storage_client() -> Any:
    """Lazily initializes and returns the Supabase Python SDK client."""
    global _storage_client
    if _storage_client is not None:
        return _storage_client

    supabase_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_role_key:
        raise StorageUnavailableError(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not configured."
        )

    from supabase import create_client

    _storage_client = create_client(supabase_url, service_role_key)
    return _storage_client


def upload_evidence(storage_path: str, file_bytes: bytes, mime_type: str) -> str:
    """Uploads a single evidence image to the private bucket. Returns the storage path."""
    client = get_storage_client()
    client.storage.from_(EVIDENCE_BUCKET).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": mime_type, "upsert": "true"},
    )
    return storage_path


def mint_signed_url(storage_path: str, expires_in_seconds: int = DEFAULT_SIGNED_URL_TTL_SECONDS) -> Optional[str]:
    """Mints a short-lived signed URL for evidence playback. Never persisted."""
    try:
        client = get_storage_client()
        res = client.storage.from_(EVIDENCE_BUCKET).create_signed_url(
            path=storage_path,
            expires_in=expires_in_seconds,
        )
        if isinstance(res, dict):
            return res.get("signedURL") or res.get("signedUrl")
        return getattr(res, "signed_url", None)
    except Exception as exc:
        logger.warning("Failed to mint signed URL for %s: %s", storage_path, exc)
        return None


def delete_evidence(storage_paths: List[str]) -> None:
    """Deletes evidence objects via the Storage API (never raw storage.objects DELETE)."""
    if not storage_paths:
        return
    client = get_storage_client()
    client.storage.from_(EVIDENCE_BUCKET).remove(storage_paths)


def is_configured() -> bool:
    """Returns True if Supabase Storage credentials are present, for /healthz checks."""
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
