"""
main.py – FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # ← Must be called BEFORE any internal module import that reads os.getenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
#  Rate limiter  (slowapi — wraps limits-library)
#  Default: 60 requests / minute per IP
#  Sensitive routes (login, register) use stricter limits defined inline.
# ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ──────────────────────────────────────────────
#  Lifespan  (replaces deprecated @app.on_event)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──
    await create_tables()
    logger.info("AI Shorts Generator is ready 🚀")
    yield
    # ── shutdown ──
    logger.info("Shutting down…")

# ──────────────────────────────────────────────
#  FastAPI app
# ──────────────────────────────────────────────
app = FastAPI(
    title="AI Shorts Generator",
    description="Transform long YouTube videos into viral shorts – 100 % local AI.",
    version="1.0.0",
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Allow the frontend dev server and production origins to call the API.
# NOTE: allow_credentials=True requires explicit origins (not "*").
ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:4173",   # Vite preview
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
]

_frontend_url = os.getenv("FRONTEND_URL", "")
if _frontend_url and _frontend_url not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
#  Static files
# ──────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Serve generated clips directly from /clips/<filename>
app.mount("/clips", StaticFiles(directory=str(DATA_DIR / "clips")), name="clips")

# NOTE: frontend is now served by Vite dev server (port 5173) or its dist/ build


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return a minimal SVG favicon to suppress browser 404s."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text y="26" font-size="28">🎬</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/health", include_in_schema=False)
async def health():
    """Health check endpoint for Railway / Render / load balancers."""
    return JSONResponse({"status": "ok"})


# ──────────────────────────────────────────────
#  API routes
# ──────────────────────────────────────────────
app.include_router(router, prefix="/api")
app.include_router(auth_router)
