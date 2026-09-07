"""FastAPI v1 API Routers."""

from .health import router as health_router
from .inspections import router as inspections_router
from .rules import router as rules_router

__all__ = ["inspections_router", "rules_router", "health_router"]
