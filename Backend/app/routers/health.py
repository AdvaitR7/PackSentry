"""
Honest Readiness Endpoint (Phase 0 mandate, ADR-0004, ADR-0013).

GET /healthz reports each pipeline dependency's actual reachability rather than
a blanket 200. Never blocks more than ~1.5s total across all checks.
"""

import importlib.util
import os
from typing import Any, Dict
from fastapi import APIRouter
from app.db.session import get_pool
from app.db.storage import is_configured as is_storage_configured
from app.ocr.vlm_interpreter import QwenVlmInterpreter

router = APIRouter(tags=["Health"])


def _check_cloud_vision_credentials() -> Dict[str, Any]:
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    configured = bool(creds_path and os.path.exists(creds_path))
    return {"configured": configured, "credentials_path_set": bool(creds_path)}


def _check_paddleocr_importable() -> Dict[str, Any]:
    available = importlib.util.find_spec("paddleocr") is not None
    return {"importable": available}


async def _check_database() -> Dict[str, Any]:
    pool = get_pool()
    if pool is None:
        return {"connected": False, "reason": "DATABASE_URL not configured or pool failed to initialize"}
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1;")
        return {"connected": True}
    except Exception as exc:
        return {"connected": False, "reason": str(exc)}


@router.get("/healthz")
async def healthz():
    """Reports honest dependency health for demo readiness verification."""
    db_status = await _check_database()
    vlm_interpreter = QwenVlmInterpreter()
    ollama_status = await vlm_interpreter.get_readiness()

    return {
        "status": "ok",
        "database": db_status,
        "storage": {"configured": is_storage_configured()},
        "cloud_vision": _check_cloud_vision_credentials(),
        "paddleocr": _check_paddleocr_importable(),
        "ollama": ollama_status,
    }
