# Repository Guidelines

## Project Structure & Module Organization

`backend/` contains the FastAPI application: HTTP endpoints live in `api/`, authentication in `auth/`, persistence models in `models/`, and processing logic in `services/`, `ai/`, and `video/`. Keep route handlers thin and put reusable business logic in the appropriate service.

`frontend-react/` is the Vite, React, and TypeScript client. Place page-level views in `src/pages/`, reusable UI in `src/components/`, API calls in `src/api/`, and shared helpers in `src/utils/`. Alembic database migrations live in `alembic/versions/`; do not edit an applied migration. Generated videos and local runtime data belong under `data/` and should not be committed.

## Build, Test, and Development Commands

From the repository root, create a Python 3.11 virtual environment and install `requirements.txt`; install frontend dependencies with `cd frontend-react && npm install`.

- `make back` — run the FastAPI server at port 8000 with reload.
- `make front` — run the Vite client at port 5173.
- `make dev` — start both development servers.
- `PYTHONPATH=. .venv/bin/pytest -q` — run the backend suite.
- `alembic upgrade head` — apply database migrations; use `--sql` for an offline SQL check.
- `rq worker` — start the Redis/RQ worker when the queue is configured.
- `cd frontend-react && npm run lint` — run ESLint.
- `cd frontend-react && npm run test` or `npm run test:coverage` — run Vitest tests (with coverage when requested).
- `cd frontend-react && npm run build` — produce a production frontend build.

## Coding Style & Naming Conventions

Python targets 3.11. The repository configures Black and Ruff with an 88-character line length; run them only when installed. Use `snake_case` for Python modules, functions, and variables; use `PascalCase` for classes. Follow existing async patterns for database and external-service calls.

Use TypeScript for frontend additions. Name components and pages `PascalCase` (for example, `GeneratorForm.tsx`), hooks `useSomething`, and tests `*.test.ts` or `*.test.tsx`. Run ESLint before submitting frontend changes.

## Testing Guidelines

Add backend tests as `tests/test_<feature>.py`; pytest is configured to discover that directory. Keep tests deterministic: mock external services such as YouTube, Stripe, SMTP, and model providers. Put frontend tests beside their source or in the related feature directory and use Testing Library/Vitest.

## Commit & Pull Request Guidelines

Recent history uses short imperative Conventional Commit-style subjects such as `feat: add email verification` and `fix: add correction`; emojis are also used for operational fixes. Keep each commit focused. PRs should explain the behavior change, list validation commands, link the relevant issue when available, and include screenshots for visible frontend changes. Run `git diff --check` before handoff. Never commit `.env`, API keys, cookies, or production media.

## Security and Scope

Use opaque cookie sessions for browser authentication; do not introduce browser Bearer/JWT storage. Preserve CSRF checks, origin validation, and job ownership checks. Generated media is private: expose it only through the authenticated job media endpoint, never a static `/clips` mount or a public filesystem path.

Keep pull requests narrow and do not stage unrelated worktree changes. Avoid broad rewrites; preserve local changes unless they are explicitly in scope. Do not commit generated media, caches, virtual environments, secrets, or local configuration.
