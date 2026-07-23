"""
Django settings for the Vivah project.

Architecture note (FSD-2 — folder-separated frontend):
  vivah/
  ├── backend/    <- this Django project (settings, views, Mongo access)
  └── frontend/   <- all templates + static assets (html/css/js) live here,
                     completely separate from backend Python code.

Data store: MongoDB only (see accounts/db.py). Django's relational
DATABASES setting is left pointed at an unused local SQLite file purely
because Django's startup machinery expects a DATABASES dict to exist —
no table in it is ever created or migrated, and no app in this project
touches it. Every real record (users, sessions data you choose to persist,
etc.) lives in MongoDB.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# backend/vivah_project/settings.py -> backend/ -> vivah/ (project root)
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-dev-only-change-this-in-production"
)

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# ---------------------------------------------------------------------------
# Apps — intentionally minimal. No django.contrib.auth / admin / contenttypes
# since user accounts live in MongoDB, not Django's ORM.
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "vivah_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "vivah_project.wsgi.application"

# Unused placeholder DB — see module docstring above.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "unused.sqlite3",
    }
}

# Sessions are stored in a signed cookie, NOT a database table, so the
# only persistent store this project ever talks to is MongoDB.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [FRONTEND_DIR / "static"]

# Media files (user-uploaded content)
MEDIA_URL = "/media/"
MEDIA_ROOT = FRONTEND_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# MongoDB connection (read by accounts/db.py)
# ---------------------------------------------------------------------------
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "vivah_db")

LOGIN_URL = "login"
