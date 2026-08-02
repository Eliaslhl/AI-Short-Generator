# Commandes utiles — AI Shorts Generator

À compléter au fur et à mesure. Liste de départ vérifiée dans `Makefile`, `package.json`, `pyproject.toml` et `pytest.ini`.

## Backend (Python 3.11, depuis la racine du dépôt)

- `make back` — lance le serveur FastAPI sur le port 8000 avec reload.
- `make dev` — lance backend + frontend en parallèle.
- `PYTHONPATH=. .venv/bin/pytest -q` — suite de tests backend complète.
- `PYTHONPATH=. .venv/bin/pytest -q tests/test_<feature>.py` — tests ciblés.
- `alembic upgrade head` — applique les migrations.
- `alembic upgrade head --sql` — vérification SQL offline sans toucher la base.
- `rq worker` — lance le worker Redis/RQ (nécessite Redis configuré).
- `ruff check .` / `black .` — lint/format Python (installés localement, à exécuter uniquement si disponibles).

## Frontend (React/TypeScript/Vite, depuis `frontend-react/`)

- `make front` — lance le serveur Vite sur le port 5173.
- `npm run lint` — ESLint.
- `npm run test` / `npm run test -- --run` — tests Vitest.
- `npm run test:coverage` — tests avec couverture.
- `npm run build` — build de production.
- `npx tsc --noEmit` — vérification TypeScript.

## Notes

- Exclure `frontend-react/.venv` (artefact local non versionné) des exécutions ESLint si présent : `npx eslint . --ignore-pattern '.venv/**'`.
- `SESSION_HASH_KEY` doit être défini dans l'environnement pour lancer l'app hors tests (voir `tests/conftest.py` pour la valeur de test).
