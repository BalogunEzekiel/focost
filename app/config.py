import os
from pathlib import Path
from dotenv import load_dotenv


# ==========================================================
# BASE DIRECTORIES
# ==========================================================

# app/config.py
# Project root = one directory above /app
BASE_DIR = Path(__file__).resolve().parent.parent

INSTANCE_DIR = BASE_DIR / "instance"

# Make sure instance directory exists
INSTANCE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================================
# ENVIRONMENT
# ==========================================================

load_dotenv(
    BASE_DIR / ".env"
)


# ==========================================================
# DATABASE
# ==========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    ""
).strip()


def resolve_database_url(database_url):
    """
    Resolve SQLite database URLs safely.

    Supports:

        sqlite:///instance/focost
        sqlite:///instance/focost.db
        sqlite:///C:/absolute/path/focost.db

    Non-SQLite URLs are returned unchanged.
    """

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL must be configured."
        )

    # ------------------------------------------------------
    # Non-SQLite database
    # ------------------------------------------------------

    if not database_url.startswith("sqlite:///"):
        return database_url

    # ------------------------------------------------------
    # Extract SQLite path
    # ------------------------------------------------------

    sqlite_path = database_url[len("sqlite:///"):]

    # ------------------------------------------------------
    # Absolute Windows / Unix path
    # ------------------------------------------------------

    path = Path(sqlite_path)

    if path.is_absolute():
        database_path = path

    else:
        # Resolve relative SQLite paths against project root
        database_path = BASE_DIR / path

    # Ensure parent directory exists
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # SQLAlchemy SQLite URL
    return f"sqlite:///{database_path.as_posix()}"


SQLALCHEMY_DATABASE_URI = resolve_database_url(
    DATABASE_URL
)


# ==========================================================
# APPLICATION CONFIGURATION
# ==========================================================

class Config:
    """Central application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ------------------------------------------------------
    # Authentication / Session
    # ------------------------------------------------------

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = (
        os.getenv(
            "SESSION_COOKIE_SECURE",
            "false"
        ).lower() == "true"
    )

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    REMEMBER_COOKIE_SECURE = (
        os.getenv(
            "SESSION_COOKIE_SECURE",
            "false"
        ).lower() == "true"
    )

    # ------------------------------------------------------
    # Request limits
    # ------------------------------------------------------

    MAX_CONTENT_LENGTH = int(
        os.getenv(
            "MAX_CONTENT_LENGTH",
            2 * 1024 * 1024
        )
    )

    # ------------------------------------------------------
    # CSRF
    # ------------------------------------------------------

    WTF_CSRF_ENABLED = True

    WTF_CSRF_TIME_LIMIT = int(
        os.getenv(
            "WTF_CSRF_TIME_LIMIT",
            3600
        )
    )

    # ------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------

    OPENAI_API_KEY = os.getenv(
        "OPENAI_API_KEY"
    )

    # ------------------------------------------------------
    # Application
    # ------------------------------------------------------

    APP_NAME = "FOCOST"

    APP_VERSION = os.getenv(
        "APP_VERSION",
        "2.0.0"
    )

    APP_ENV = os.getenv(
        "FLASK_ENV",
        "production"
    )