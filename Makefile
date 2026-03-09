VENV = .venv/bin/python3.11

back:
	$(VENV) -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend

front:
	cd frontend-react && npm run dev

dev:
	$(VENV) -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend & cd frontend-react && npm run dev
