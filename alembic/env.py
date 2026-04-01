"""
alembic/env.py – Migration environment wired to our async SQLAlchemy setup.

Run migrations:
    alembic upgrade head          # apply all pending migrations
    alembic revision --autogenerate -m "description"   # generate new migration
    alembic downgrade -1          # roll back one step
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── pull in all models so autogenerate can detect them ────────────────────────
from backend.database import Base  # noqa: F401 — Base.metadata
import backend.models.user  # noqa: F401 — registers User, Job, etc.

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from environment (DATABASE_URL) if set,
# falling back to the value in alembic.ini
_db_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
_using_public_proxy = False

_db_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))

# Convert postgres:// or postgresql:// -> postgresql+asyncpg:// for async engine
if _db_url and _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _db_url and _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

config.set_main_option("sqlalchemy.url", _db_url or "")


# ── Offline mode (generate SQL script without connecting) ─────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connect and run against DB) ──────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # detect column type changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # use NullPool for migrations
    )

    # Retry loop: the DB may not be available immediately on container start.
    # Configure with env vars for flexibility in CI / deploy environments.
    max_retries = int(os.getenv("MIGRATION_DB_CONNECT_RETRIES", "12"))
    delay_seconds = float(os.getenv("MIGRATION_DB_CONNECT_DELAY", "5"))

    for attempt in range(1, max_retries + 1):
        try:
            async with connectable.connect() as connection:
                # HOTFIX: Clean orphaned migration references before running migrations
                # Some databases may have stale alembic_version entries from failed deployments
                await connection.run_sync(_cleanup_orphaned_migrations)
                await connection.run_sync(do_run_migrations)
            break
        except Exception as exc:  # pragma: no cover - runtime network issues
            # store and retry
            if attempt >= max_retries:
                raise
            # simple backoff
            #
            print(
                f"[alembic] DB connect attempt {attempt}/{max_retries} failed: {exc}; retrying in {delay_seconds}s"
            )
            await asyncio.sleep(delay_seconds)

    await connectable.dispose()


def _cleanup_orphaned_migrations(connection: Connection) -> None:
    """
    Clean up orphaned migration references that may exist from failed deployments.
    Deletes entries that reference non-existent revisions.
    """
    from sqlalchemy import text
    
    try:
        # Check if alembic_version table exists
        result = connection.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )
        result.close()
        
        # If it exists, try to clean orphaned entries
        # This is safe: we only delete entries that don't correspond to actual migration files
        orphaned_revisions = [
            '20260329_idempotent_add_plan_and_override_columns',  # filename, not revision ID
        ]
        for rev in orphaned_revisions:
            connection.execute(
                text(f"DELETE FROM alembic_version WHERE version_num = '{rev}'")
            )
        connection.commit()
    except Exception:
        # Table doesn't exist or cleanup failed—no problem, continue
        # The migrations will create it if needed
        pass


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
