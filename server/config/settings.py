"""Django settings.

Everything that differs between machines (secrets, debug mode, allowed hosts)
comes from environment variables, which are loaded from server/.env in
development. See .env.example for the full list.

Complaints are stored in a CSV file, not a database, so the database, admin,
auth and session apps are left out.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    return default if not value else [item.strip() for item in value.split(",") if item.strip()]


# --- Core ---------------------------------------------------------------------

DEBUG = env_bool("DJANGO_DEBUG")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is not set. For local development, copy server/.env.example "
            "to server/.env (it turns on DJANGO_DEBUG, which allows a built-in development key)."
        )
    SECRET_KEY = "development-only-key-do-not-use-in-production"  # noqa: S105 (only reachable in debug mode)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "rest_framework",
    "complaints",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES: dict = {}

# Complaint times in the CSV file are written in this time zone.
USE_TZ = True
TIME_ZONE = os.getenv("TIME_ZONE") or "UTC"

# --- REST framework -----------------------------------------------------------

REST_FRAMEWORK = {
    # A JSON-only API with no accounts: no browsable API, no authentication.
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    # Stops one client from flooding the complaint file. Students in a hostel often
    # share one network address, so the default is generous.
    "DEFAULT_THROTTLE_RATES": {"complaints": os.getenv("COMPLAINT_RATE_LIMIT") or "30/min"},
}

# The throttle counters live in the cache; an in-process cache is enough for one server.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Complaints ---------------------------------------------------------------

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL") or "claude-opus-5-5"

# Where complaints are saved. A relative path is taken from the server folder.
COMPLAINTS_FILE = BASE_DIR / (os.getenv("COMPLAINTS_FILE") or "data/complaints.csv")

# These limits are mirrored in client/src/limits.ts.
NAME_MAX_CHARS = 80
ROOM_MAX_CHARS = 20
COMPLAINT_MIN_CHARS = 5
COMPLAINT_MAX_CHARS = 1_000

# --- Logging ------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
