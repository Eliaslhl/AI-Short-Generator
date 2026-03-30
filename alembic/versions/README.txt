```plaintext
Toutes les anciennes migrations ont été supprimées pour repartir sur une base propre. Génère une nouvelle migration avec alembic revision --autogenerate -m "initial schema with all columns".

NOTE: A previous non-idempotent migration (20260328_add_youtube_twitch_limit_overrides.py, revision rev20260328b)
was intentionally converted to a no-op in the codebase to avoid duplicate-column failures. The idempotent
migration (20260329_idempotent_add_plan_and_override_columns.py) is the canonical migration to add the
related columns and enums. Keep migrations idempotent when modifying production schemas.
```
Toutes les anciennes migrations ont été supprimées pour repartir sur une base propre. Génère une nouvelle migration avec alembic revision --autogenerate -m "initial schema with all columns".