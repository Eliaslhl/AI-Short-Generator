"""Safe, centralized redaction for application log records."""

import logging
import re
from collections.abc import Mapping
from typing import Any


REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "secret_key",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "authorization",
        "cookie",
        "set_cookie",
        "jwt",
        "client_secret",
    }
)
_DATABASE_URL_RE = re.compile(
    r"(?i)\b(?:postgres(?:ql)?(?:\+\w+)?|mysql(?:\+\w+)?|sqlite(?:\+\w+)?)"
    r"://[^\s'\"]+"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
_JWT_RE = re.compile(r"\b[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_USER_PATH_RE = re.compile(r"/(?:Users|home|private/var/folders)/[^\s'\"]+")


def _normalized_key(value: object) -> str:
    try:
        return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    except Exception:
        return ""


def _is_sensitive_key(value: object) -> bool:
    return _normalized_key(value) in _SENSITIVE_KEYS


def _redact_key_values(text: str) -> str:
    names = "|".join(re.escape(key).replace("_", "[-_ ]?") for key in _SENSITIVE_KEYS)
    pattern = re.compile(
        rf"(?i)(?P<prefix>[\"']?(?:{names})[\"']?\s*[:=]\s*[\"']?)"
        r"(?P<value>[^\s,;\"'}&]+)"
    )
    return pattern.sub(lambda match: f"{match.group('prefix')}{REDACTED}", text)


def _redact_query_values(text: str) -> str:
    names = "|".join(re.escape(key).replace("_", "[-_ ]?") for key in _SENSITIVE_KEYS)
    pattern = re.compile(rf"(?i)([?&](?:{names})=)[^&#\s]+")
    return pattern.sub(rf"\1{REDACTED}", text)


def _safe_text(value: object) -> str:
    try:
        return str(value)
    except Exception:
        return f"[UNPRINTABLE {type(value).__name__}]"


def sanitize_value(value: Any) -> Any:
    """Return a sanitized copy suitable for logs without mutating ``value``."""
    try:
        if isinstance(value, Mapping):
            return {
                _safe_text(key): REDACTED if _is_sensitive_key(key) else sanitize_value(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [sanitize_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(sanitize_value(item) for item in value)
        if isinstance(value, set):
            return {sanitize_value(item) for item in value}
        if isinstance(value, BaseException):
            return f"{type(value).__name__}: {sanitize_value(_safe_text(value))}"

        text = _safe_text(value)
        text = _DATABASE_URL_RE.sub("[REDACTED DATABASE URL]", text)
        text = _redact_query_values(text)
        text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
        text = _redact_key_values(text)
        text = _JWT_RE.sub(REDACTED, text)
        return _USER_PATH_RE.sub("[REDACTED LOCAL PATH]", text)
    except Exception:
        return f"[UNPRINTABLE {type(value).__name__}]"


def redact_sensitive_data(value: Any) -> str:
    """Backward-compatible string helper for call sites that need safe text."""
    return str(sanitize_value(value))


def sanitize_log_record(record: logging.LogRecord) -> None:
    """Make a log record safe for every current and future handler."""
    try:
        message = record.getMessage()
    except Exception:
        message = _safe_text(record.msg)

    record.msg = sanitize_value(message)
    record.args = ()
    if record.exc_info:
        exception = record.exc_info[1]
        record.msg = f"{record.msg} | exception={sanitize_value(exception)}"
        record.exc_info = None
        record.exc_text = None


class SensitiveDataFilter(logging.Filter):
    """Defense-in-depth filter for handlers configured outside this module."""

    def filter(self, record: logging.LogRecord) -> bool:
        sanitize_log_record(record)
        return True


class SensitiveDataFormatter(logging.Formatter):
    """Formatter that protects records created before logging was configured."""

    def format(self, record: logging.LogRecord) -> str:
        sanitize_log_record(record)
        return super().format(record)


_configured = False
_previous_factory = logging.getLogRecordFactory()


def configure_logging() -> None:
    """Configure a process-wide safe record factory and default root handler."""
    global _configured
    if _configured:
        return

    def safe_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = _previous_factory(*args, **kwargs)
        sanitize_log_record(record)
        return record

    logging.setLogRecordFactory(safe_record_factory)
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            SensitiveDataFormatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )
        )
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    _configured = True
