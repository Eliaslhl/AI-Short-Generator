"""
email_service.py – Transactional email sending via SMTP (fastapi-mail).

Configuration (in .env):
    MAIL_USERNAME   = you@gmail.com
    MAIL_PASSWORD   = your_16_char_app_password   (no spaces)
    MAIL_FROM       = you@gmail.com
    MAIL_SERVER     = smtp.gmail.com
    MAIL_PORT       = 587
    MAIL_STARTTLS   = true
    MAIL_SSL_TLS    = false
    MAIL_SUPPRESS_SEND = false   # set true to only log, not send
"""

import logging
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig

logger = logging.getLogger(__name__)

# Load .env with absolute path so it works regardless of cwd
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
_env = dotenv_values(_ENV_PATH)
logger.debug(f"Email service loaded .env from: {_ENV_PATH} (exists: {_ENV_PATH.exists()})")


def _v(key: str, default: str = "") -> str:
    """Read a value from .env file, falling back to default."""
    return _env.get(key) or default


FRONTEND_URL = _v("FRONTEND_URL", "http://localhost:5173")


@lru_cache(maxsize=1)
def _get_mailer() -> tuple[FastMail, bool]:
    """Build the FastMail instance once and cache it."""
    suppress = _v("MAIL_SUPPRESS_SEND", "false").lower() == "true"

    conf = ConnectionConfig(
        MAIL_USERNAME=_v("MAIL_USERNAME"),
        MAIL_PASSWORD=_v("MAIL_PASSWORD"),
        MAIL_FROM=_v("MAIL_FROM", _v("MAIL_USERNAME", "noreply@aishorts.app")),
        MAIL_FROM_NAME=_v("MAIL_FROM_NAME", "AI Shorts Generator"),
        MAIL_PORT=int(_v("MAIL_PORT", "587")),
        MAIL_SERVER=_v("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_STARTTLS=_v("MAIL_STARTTLS", "true").lower() == "true",
        MAIL_SSL_TLS=_v("MAIL_SSL_TLS", "false").lower() == "true",
        USE_CREDENTIALS=bool(_v("MAIL_USERNAME")),
        VALIDATE_CERTS=True,
        SUPPRESS_SEND=suppress,
    )
    return FastMail(conf), suppress


async def send_reset_email(to_email: str, reset_token: str) -> None:
    """Send a password-reset link to the user."""
    mailer, suppress = _get_mailer()
    reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    if suppress:
        logger.info(f"[DEV] Password reset email suppressed. URL: {reset_url}")
        return

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#0f0f0f;color:#fff;border-radius:12px">
      <h1 style="font-size:24px;font-weight:700;margin-bottom:8px">Reset your password</h1>
      <p style="color:#9ca3af;margin-bottom:24px">
        Click the button below to set a new password.<br>
        This link expires in <strong style="color:#fff">1 hour</strong>.
      </p>
      <a href="{reset_url}"
         style="display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#7c3aed,#db2777);color:#fff;font-weight:600;border-radius:8px;text-decoration:none">
        Reset password
      </a>
      <p style="margin-top:24px;font-size:12px;color:#6b7280">
        If you didn't request this, ignore this email — your password won't change.<br>
        Link: <a href="{reset_url}" style="color:#a78bfa">{reset_url}</a>
      </p>
    </div>
    """

    message = MessageSchema(
        subject="Reset your AI Shorts password",
        recipients=[to_email],
        body=html,
        subtype=MessageType.html,
    )

    try:
        await mailer.send_message(message)
        logger.info(f"Password reset email sent to {to_email}")
    except Exception as exc:
        logger.error(f"Failed to send reset email to {to_email}: {exc}")
        raise
