VENV = .venv/bin/python

back:
	$(VENV) -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --reload-delay 2

front:
	cd frontend-react && npm run dev

dev:
	$(VENV) -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --reload-delay 2 & cd frontend-react && npm run dev

back-no-reload:
	$(VENV) -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
