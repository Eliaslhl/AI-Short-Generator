"""Migration smoke tests for the isolated auth_sessions revision."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "20260404_remove_email_constraint"


def _run_alembic(database_url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": database_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_auth_session_migration_upgrades_downgrades_and_upgrades_again(tmp_path):
    database_path = tmp_path / "migration.db"
    async_url = f"sqlite+aiosqlite:///{database_path}"

    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE users (id VARCHAR(36) NOT NULL PRIMARY KEY)"
        )
    _run_alembic(async_url, "stamp", PREVIOUS_REVISION)
    _run_alembic(async_url, "upgrade", "head")
    inspector = inspect(engine)
    assert "auth_sessions" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("auth_sessions")}
    assert columns == {
        "id",
        "user_id",
        "token_hash",
        "created_at",
        "expires_at",
        "revoked_at",
        "last_seen_at",
    }
    foreign_keys = inspector.get_foreign_keys("auth_sessions")
    assert foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["user_id"],
            "referred_schema": None,
            "referred_table": "users",
            "referred_columns": ["id"],
            "options": {},
        }
    ]
    indexes = {index["name"]: index for index in inspector.get_indexes("auth_sessions")}
    assert {
        "ix_auth_sessions_token_hash",
        "ix_auth_sessions_user_id",
        "ix_auth_sessions_expires_at",
        "ix_auth_sessions_user_id_revoked_at",
    } <= indexes.keys()
    assert indexes["ix_auth_sessions_token_hash"]["unique"] == 1

    _run_alembic(async_url, "downgrade", "-1")
    inspector = inspect(engine)
    assert "auth_sessions" not in inspector.get_table_names()
    _run_alembic(async_url, "upgrade", "head")
    assert "auth_sessions" in inspect(engine).get_table_names()
    engine.dispose()
