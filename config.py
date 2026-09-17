"""Centralized, environment-driven runtime configuration for AegisMind.

This project intentionally defaults to a local, in-memory demo mode.  Set the
production integration variables below before exposing the service publicly.
"""

import os


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value, default: int, minimum: int = 1) -> int:
    try:
        return max(int(value or default), minimum)
    except (TypeError, ValueError):
        return default


class Config:
    """Settings read once at application start; never return secret values to clients."""

    ENV = os.environ.get("FLASK_ENV", "development").strip().lower()
    IS_PRODUCTION = ENV == "production"
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY")

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    TELE_MANAS_API_URL = os.environ.get("TELE_MANAS_API_URL", "")
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")

    # Persistence and worker URLs are deliberate integration points.  The app
    # stays in demo memory mode until a repository implementation is enabled.
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    REDIS_URL = os.environ.get("REDIS_URL", "")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "")
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    COUNSELOR_API_KEY = os.environ.get("COUNSELOR_API_KEY", "")

    RATE_LIMIT_WINDOW_SECONDS = _as_int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS"), 60)
    CHECKIN_RATE_LIMIT = _as_int(os.environ.get("CHECKIN_RATE_LIMIT"), 10)
    CHAT_RATE_LIMIT = _as_int(os.environ.get("CHAT_RATE_LIMIT"), 20)
    FORUM_RATE_LIMIT = _as_int(os.environ.get("FORUM_RATE_LIMIT"), 8)
    MAX_REQUEST_BYTES = _as_int(os.environ.get("MAX_REQUEST_BYTES"), 32 * 1024)
    GROQ_TIMEOUT_SECONDS = _as_int(os.environ.get("GROQ_TIMEOUT_SECONDS"), 12)
    FORCE_HTTPS = _as_bool(os.environ.get("FORCE_HTTPS"), IS_PRODUCTION)

    # Optional extension points for a native WebView / hosted backend.
    PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "")
    API_BASE_URL = os.environ.get("API_BASE_URL", "")

    # PWA Configuration
    PWA_APP_NAME = os.environ.get("PWA_APP_NAME", "AegisMind")
    PWA_APP_SHORT_NAME = os.environ.get("PWA_APP_SHORT_NAME", "AegisMind")

    # Audit Logging
    AUDIT_LOG_ENABLED = _as_bool(os.environ.get("AUDIT_LOG_ENABLED"), True)

    # Database Migration Control
    DB_MIGRATION_ENABLED = _as_bool(os.environ.get("DB_MIGRATION_ENABLED"), False)

    # Sentry DSN for error tracking (set in production)
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
