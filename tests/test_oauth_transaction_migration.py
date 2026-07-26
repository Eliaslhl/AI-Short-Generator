"""Migration contract for OAuth transaction state."""

from sqlalchemy import create_engine, inspect

from tests.test_auth_session_migration import _run_alembic


def test_oauth_transaction_migration_upgrades_downgrades_and_upgrades_again(tmp_path):
    path = tmp_path / "oauth-migration.db"
    url = f"sqlite+aiosqlite:///{path}"
    _run_alembic(url, "stamp", "20260726_add_auth_sessions")
    _run_alembic(url, "upgrade", "20260726_add_oauth_transactions")
    engine = create_engine(f"sqlite:///{path}")
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("oauth_transactions")}
    assert columns == {"id", "state_hash", "provider", "redirect_uri", "created_at", "expires_at", "consumed_at"}
    indexes = {index["name"]: index for index in inspector.get_indexes("oauth_transactions")}
    assert indexes["ix_oauth_transactions_state_hash"]["unique"] == 1
    _run_alembic(url, "downgrade", "-1")
    assert "oauth_transactions" not in inspect(engine).get_table_names()
    _run_alembic(url, "upgrade", "head")
    assert "oauth_transactions" in inspect(engine).get_table_names()
    engine.dispose()
