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
import os
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig

logger = logging.getLogger(__name__)

# Load .env file for local dev; on Railway env vars are already in os.environ
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
_file_env = dotenv_values(_ENV_PATH) if _ENV_PATH.exists() else {}


def _v(key: str, default: str = "") -> str:
    """Read from os.environ first (Railway), then .env file (local), then default."""
    return os.environ.get(key) or _file_env.get(key) or default


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


async def send_welcome_email(to_email: str, full_name: str = "") -> None:
    """Send a welcome email after registration."""
    mailer, suppress = _get_mailer()
    dashboard_url = f"{FRONTEND_URL}/generate"
    name = full_name.split()[0] if full_name else "there"

    if suppress:
        logger.info(f"[DEV] Welcome email suppressed for {to_email}")
        return

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#0f0f0f;color:#fff;border-radius:12px">
      <div style="text-align:center;margin-bottom:24px">
        <span style="font-size:32px">🎬</span>
        <h1 style="font-size:24px;font-weight:700;margin:8px 0">Welcome to AI Shorts Generator!</h1>
      </div>
      <p style="color:#9ca3af;margin-bottom:16px">
        Hey {name} 👋<br><br>
        Your account is ready. You can now turn any YouTube video into viral short clips with AI.
      </p>
      <div style="background:#1a1a2e;border:1px solid #7c3aed33;border-radius:8px;padding:16px;margin-bottom:24px">
        <p style="margin:0;font-size:14px;color:#a78bfa;font-weight:600">🎁 Your free plan includes:</p>
        <ul style="color:#d1d5db;font-size:14px;margin:8px 0 0 0;padding-left:20px">
          <li>1 video per month</li>
          <li>3 shorts per video</li>
          <li>1080p export</li>
          <li>Auto captions</li>
        </ul>
      </div>
      <a href="{dashboard_url}"
         style="display:block;text-align:center;padding:14px 28px;background:linear-gradient(135deg,#7c3aed,#db2777);color:#fff;font-weight:600;border-radius:8px;text-decoration:none;font-size:16px">
        Start generating →
      </a>
      <p style="margin-top:24px;font-size:12px;color:#6b7280;text-align:center">
        AI Shorts Generator · <a href="{FRONTEND_URL}" style="color:#a78bfa">aishortsgenerator.com</a>
      </p>
    </div>
    """

    message = MessageSchema(
        subject="Welcome to AI Shorts Generator 🎬",
        recipients=[to_email],
        body=html,
        subtype=MessageType.html,
    )

    try:
        await mailer.send_message(message)
        logger.info(f"Welcome email sent to {to_email}")
    except Exception as exc:
        # Don't block registration if welcome email fails
        logger.error(f"Failed to send welcome email to {to_email}: {exc}")
