"""
main.py – FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

from backend.api.routes import router
from backend.auth.router import router as auth_router
from backend.database import create_tables

# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  FastAPI app
# ──────────────────────────────────────────────
app = FastAPI(
    title="AI Shorts Generator",
    description="Transform long YouTube videos into viral shorts – 100 % local AI.",
    version="1.0.0",
)

# Allow the frontend dev server and production origins to call the API.
# NOTE: allow_credentials=True requires explicit origins (not "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
#  Static files
# ──────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DATA_DIR     = Path(__file__).resolve().parent.parent / "data"

# Serve generated clips directly from /clips/<filename>
app.mount("/clips", StaticFiles(directory=str(DATA_DIR / "clips")), name="clips")

# NOTE: frontend is now served by Vite dev server (port 5173) or its dist/ build


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return a minimal SVG favicon to suppress browser 404s."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text y="26" font-size="28">🎬</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")


# ──────────────────────────────────────────────
#  API routes
# ──────────────────────────────────────────────
app.include_router(router, prefix="/api")
app.include_router(auth_router)


# ──────────────────────────────────────────────
#  Startup event
# ──────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    await create_tables()
    logger.info("AI Shorts Generator is ready 🚀")
    logger.info("Open http://localhost:8000 in your browser.")
