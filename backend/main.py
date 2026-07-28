"""
main.py – FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv, find_dotenv

# Load the project's top-level .env file (searches parent directories).
import asyncio
# This makes behaviour deterministic whether you run uvicorn from the repo root
# or from the backend folder. Prefer a single root `.env` for secrets/config.
if os.getenv("APP_ENVIRONMENT") in {"development", "test"}:
    _dotenv_path = find_dotenv()
    if _dotenv_path:
        load_dotenv(_dotenv_path)
    else:
        load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import Response, JSONResponse  # noqa: E402
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.requests import Request  # noqa: E402

from backend.security_logging import configure_logging  # noqa: E402

configure_logging()

from backend.api.routes import router  # noqa: E402
from backend.auth.router import router as auth_router  # noqa: E402
from backend.auth.origin_policy import CanonicalCORSMiddleware  # noqa: E402
from backend.auth.session_cookie import allowed_origins, validate_session_cookie_configuration  # noqa: E402
from backend.services.session_service import validate_session_hash_key  # noqa: E402
from backend.api.advanced_routes import advanced_router  # noqa: E402
from backend.database import create_tables  # noqa: E402

# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Rate limiter  (slowapi — wraps limits-library)
#  Default: 60 requests / minute per IP
#  Sensitive routes (login, register) use stricter limits defined inline.
# ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# ──────────────────────────────────────────────
#  Security Headers Middleware
# ──────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses (except preflight OPTIONS)."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip security headers for OPTIONS (CORS preflight) requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection (older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # Referrer Policy: Only send referrer to same-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
        
        # Content Security Policy (strict)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests"
        )
        
        # Strict Transport Security (HSTS) - 1 year
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        
        return response



# ──────────────────────────────────────────────
#  Lifespan  (replaces deprecated @app.on_event)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──
    await create_tables()
    
    logger.info(
        "Email delivery configured=%s suppressed=%s",
        bool(os.getenv("MAIL_USERNAME")),
        os.getenv("MAIL_SUPPRESS_SEND", "false").lower() == "true",
    )
    
    logger.info("AI Shorts Generator is ready 🚀")
    yield
    # ── shutdown ──
    logger.info("Shutting down…")
    # Run DB initialization in background so the HTTP server can become
    # healthy quickly even if the DB is slow or migrations take time.
    # This avoids failing container healthchecks when DB is temporarily
    # unavailable. Use MIGRATE_ON_START=false to fully skip this behavior.
    migrate_on_start = os.getenv("MIGRATE_ON_START", "true").lower() == "true"
    if migrate_on_start:
        async def _init_db():
            try:
                await create_tables()
                logger.info("DB initialization completed")
            except Exception as exc:
                logger.error(
                    "Background DB initialization failed: exception_type=%s",
                    type(exc).__name__,
                )

        # schedule background init and don't await it
        asyncio.create_task(_init_db())
    else:
        logger.info("Skipping DB initialization at startup (MIGRATE_ON_START=false)")



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
# ⚠️  IMPORTANT: CORS middleware MUST be added FIRST (before other middlewares)
validate_session_cookie_configuration()
validate_session_hash_key()
ALLOWED_ORIGINS = allowed_origins()

app.add_middleware(
    CanonicalCORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods instead of "*"
    allow_headers=[
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],  # Explicit headers instead of "*"
    expose_headers=["Content-Length", "Content-Range"],
    max_age=86400,  # Cache CORS preflight for 24 hours
)

# Add security headers middleware (AFTER CORS)
app.add_middleware(SecurityHeadersMiddleware)

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
app.include_router(advanced_router, prefix="/api", tags=["advanced"])
