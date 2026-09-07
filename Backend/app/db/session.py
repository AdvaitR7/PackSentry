"""
Asyncpg Database Session and Connection Pool Management (ADR-0013).

Provides:
- Native asyncpg connection pool to Supabase Postgres.
- Enforces `search_path=app,public` on all connections.
- Lifespan management for FastAPI startup and shutdown.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None

logger = logging.getLogger("packsentry.db.session")

_pool: Optional[Any] = None


async def init_connection(conn: Any) -> None:
    """Configures each connection with the dedicated non-public app search path."""
    await conn.execute("SET search_path TO app, public;")


async def init_pool(database_url: Optional[str] = None) -> Optional[Any]:
    """
    Initializes the asyncpg connection pool.
    Returns None if asyncpg is not installed or DATABASE_URL is not configured.
    """
    global _pool
    if asyncpg is None:
        logger.warning(
            "asyncpg library not installed. Database pool disabled (running in memory/offline mode)."
        )
        return None

    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        logger.warning(
            "DATABASE_URL not configured. Running with in-memory persistence only."
        )
        return None

    try:
        _pool = await asyncpg.create_pool(
            dsn=url,
            min_size=2,
            max_size=10,
            init=init_connection,
            command_timeout=15.0,
        )
        logger.info("Supabase Postgres asyncpg connection pool initialized successfully.")
        return _pool
    except Exception as exc:
        logger.error("Failed to initialize database pool: %s", exc)
        _pool = None
        return None


async def close_pool() -> None:
    """Terminates the asyncpg connection pool cleanly on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


def get_pool() -> Optional[asyncpg.Pool]:
    """Returns the current connection pool, if initialized."""
    return _pool


@asynccontextmanager
async def acquire_connection() -> AsyncGenerator[Optional[asyncpg.Connection], None]:
    """Context manager for safely acquiring and releasing a connection from the pool."""
    pool = get_pool()
    if pool is None:
        yield None
        return

    async with pool.acquire() as conn:
        yield conn
