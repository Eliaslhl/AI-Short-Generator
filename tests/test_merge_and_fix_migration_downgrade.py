"""20260401_merge_and_fix's downgrade() used to be a silent `pass` (audit
P1-9) despite upgrade() creating a Postgres ENUM type and adding a NOT NULL
column. This migration's own upgrade() steps are conditional ("IF NOT
EXISTS"), inherited from merging two branches — there is no way to know from
here alone whether THIS migration owns the `plan` column/enum type versus an
earlier one, so a real downgrade cannot safely drop them (plan_youtube/
plan_twitch already depend on the same enum type, and dropping `plan` would
destroy every user's plan assignment). This only verifies the part that *is*
safely reversible actually gets reversed, and confirms the unsafe part is
deliberately left alone rather than silently doing nothing at all.

The migration is Postgres-only (DO $$ blocks, CREATE TYPE ... AS ENUM) and
cannot be executed against SQLite at all, so — unlike this repo's other
migration smoke tests (test_auth_session_migration.py) which run real
upgrade/downgrade against a temp SQLite DB — this only validates the static
offline SQL Alembic generates, the same validation this repo already relies
on everywhere for this migration (see the project's own `alembic ... --sql`
checks).
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGE_REVISION = "20260401_merge_and_fix"
PARENT_REVISION = "3b526031a41b"  # one branch of the merge point's down_revision


def _alembic_sql(*args: str) -> str:
    env = {**os.environ, "SESSION_HASH_KEY": "test-session-key-not-for-production"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args, "--sql"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_downgrade_generates_valid_sql_without_error():
    # Exercises the exact code path pytest can't run directly against
    # SQLite: this raises CalledProcessError (failing the test) if the
    # downgrade() function has a syntax error or raises.
    _alembic_sql("downgrade", f"{MERGE_REVISION}:{PARENT_REVISION}")


def test_downgrade_drops_the_is_active_default():
    sql = _alembic_sql("downgrade", f"{MERGE_REVISION}:{PARENT_REVISION}")

    assert "ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT" in sql


def test_downgrade_never_drops_the_plan_column_or_shared_enum_type():
    """The unsafe operations this migration deliberately does NOT attempt:
    dropping `plan` would destroy user data, and dropping the `plan` enum
    type would break plan_youtube/plan_twitch, which depend on it too."""
    sql = _alembic_sql("downgrade", f"{MERGE_REVISION}:{PARENT_REVISION}")

    assert "DROP COLUMN plan" not in sql
    assert "DROP TYPE" not in sql


def test_full_offline_chain_upgrades_and_downgrades_cleanly():
    """Sanity check that this migration's downgrade() doesn't break the
    surrounding chain when walking the entire history in both directions."""
    _alembic_sql("upgrade", "head")
    _alembic_sql("downgrade", "20260726_add_oauth_transactions:base")
