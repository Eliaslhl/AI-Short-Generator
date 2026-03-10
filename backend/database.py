"""
database.py – SQLAlchemy async engine + session factory.

Local dev  : SQLite  (sqlite+aiosqlite:///./data/app.db)
Production : PostgreSQL (postgresql+asyncpg://user:pass@host/db)

Switch via DATABASE_URL in .env — no code change needed.
"""

import os
import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

logger = logging.getLogger(__name__)

_raw_url: str = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./data/app.db",
)

# Railway injecte postgresql:// ou postgres:// — on convertit en asyncpg
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql://") and "+asyncpg" not in _raw_url:
    _raw_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

DATABASE_URL: str = _raw_url

_is_sqlite    = DATABASE_URL.startswith("sqlite")
_is_postgres  = DATABASE_URL.startswith("postgres")

# ──────────────────────────────────────────────────────────────────────────────
#  Engine
#  - SQLite  : NullPool (no persistent pool — file-based, single-writer)
#  - Postgres: AsyncAdaptedQueuePool with sane prod defaults
# ──────────────────────────────────────────────────────────────────────────────
_connect_args: dict = {"check_same_thread": False} if _is_sqlite else {}

_pool_kwargs: dict = (
    {
        "poolclass":     NullPool,          # SQLite: no pool needed
    }
    if _is_sqlite
    else {
        "poolclass":         AsyncAdaptedQueuePool,
        "pool_size":         10,            # base connections always open
        "max_overflow":      20,            # extra burst connections
        "pool_timeout":      30,            # seconds to wait for a connection
        "pool_recycle":      1800,          # recycle every 30 min (avoid stale)
        "pool_pre_ping":     True,          # verify connection before use
    }
)

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,      # set True only for query debugging
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────────────────────────────────────
#  FastAPI dependency
# ──────────────────────────────────────────────────────────────────────────────
async def get_db():
    """Yield an async DB session; rolls back on unhandled exception."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ──────────────────────────────────────────────────────────────────────────────
#  Dev-only table creation  (skipped when Alembic is in use)
# ──────────────────────────────────────────────────────────────────────────────
async def create_tables():
    """
    Create all tables on first boot (dev convenience).
    In production, run:  alembic upgrade head
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(f"DB tables ready  [{DATABASE_URL.split('://')[0]}]")
