"""
PackSentry Legal Metrology Backend Service (ADR-0007, ADR-0009, ADR-0013, ADR-0015).

Provides:
- POST /v1/inspections: async intake, validation, scratch staging, and 202 Accepted return.
- GET /v1/inspections/{id}: in-flight polling (<5ms) from in-memory registry, terminal persistence from Postgres.
- GET /v1/inspections: inspection history.
- GET /v1/rules?as_of=: statutory rules catalog.
- GET /healthz: honest readiness across dependencies.
"""

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.db.scratch import get_scratch_dir
from app.db.seed_rules import sync_rule_registry
from app.db.session import acquire_connection, close_pool, init_pool
from app.routers import health_router, inspections_router, rules_router
from app.worker import InspectionWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("packsentry.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application lifecycle: database pool, rule sync, and background worker."""
    logger.info("Initializing PackSentry Backend Service...")

    # 1. Initialize Supabase Postgres Connection Pool
    pool = await init_pool()
    if pool:
        try:
            async with acquire_connection() as conn:
                await sync_rule_registry(conn)
        except Exception as exc:
            logger.warning("Rule registry synchronization failed: %s", exc)

    # 2. Initialize and start the bounded single-capacity background worker
    worker = InspectionWorker()
    app.state.worker = worker
    await worker.start()

    logger.info("PackSentry Backend Service ready.")
    yield

    # 3. Shutdown
    logger.info("Shutting down PackSentry Backend Service...")
    await worker.stop()
    await close_pool()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="PackSentry Legal Metrology Scanner API",
    version="1.0.0",
    description="Statutory packaging compliance analysis service under the Legal Metrology (Packaged Commodities) Rules, 2011.",
    lifespan=lifespan,
)

# Local demo & inspector client CORS policy per ADR-0009 and ADR-0015
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount /v1 API routers
app.include_router(inspections_router, prefix="/v1")
app.include_router(rules_router, prefix="/v1")
app.include_router(health_router)


@app.get("/v1/inspections/{inspection_id}/images/{role}/{kind}", tags=["Inspections"])
async def get_inspection_image_fallback(inspection_id: str, role: str, kind: str):
    """
    Fallback endpoint to serve evidence images directly from local scratch disk
    when external cloud storage is unavailable or operating in local test mode.
    """
    scratch_dir = get_scratch_dir(inspection_id)
    filename = f"{role.lower()}_{kind.lower()}.jpg"
    file_path = scratch_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Image {filename} not found.")

    return FileResponse(file_path, media_type="image/jpeg")
