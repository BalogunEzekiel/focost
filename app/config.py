import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")


def resolve_database_url(database_url):
    """
    Resolve SQLite database URLs safely.

    Supports:
        sqlite:///:memory:
        sqlite:///instance/focost
        sqlite:///instance/focost.db
        sqlite:///C:/absolute/path/focost.db

    Non-SQLite URLs are returned unchanged.
    """
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured.")

    if not database_url.startswith("sqlite:///"):
        return database_url

    sqlite_path = database_url[len("sqlite:///"):]

    # SQLite in-memory database must remain exactly in-memory.
    if sqlite_path == ":memory:":
        return "sqlite:///:memory:"

    path = Path(sqlite_path)

    if path.is_absolute():
        database_path = path
    else:
        database_path = BASE_DIR / path

    database_path.parent.mkdir(parents=True, exist_ok=True)

    return f"sqlite:///{database_path.as_posix()}"


# Keep environment-derived defaults here for normal application startup.
# The application factory may override these values for testing BEFORE
# SQLAlchemy is initialized.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    SQLALCHEMY_DATABASE_URI = resolve_database_url(DATABASE_URL)
else:
    SQLALCHEMY_DATABASE_URI = None


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    APP_ENCRYPTION_KEY = os.getenv("APP_ENCRYPTION_KEY")

    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )

    MAX_CONTENT_LENGTH = int(
        os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
    )

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = int(
        os.getenv("WTF_CSRF_TIME_LIMIT", 3600)
    )

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    APP_NAME = "FOCOST"
    APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
    APP_ENV = os.getenv("FLASK_ENV", "production")

    APP_BASE_URL = os.getenv(
        "APP_BASE_URL",
        "http://127.0.0.1:5000"
    ).rstrip("/")

    AUTH_EMAIL_VERIFICATION_REQUIRED = (
        os.getenv(
            "AUTH_EMAIL_VERIFICATION_REQUIRED",
            "true"
        ).lower() == "true"
    )

    AUTH_EMAIL_VERIFICATION_TTL_MINUTES = int(
        os.getenv(
            "AUTH_EMAIL_VERIFICATION_TTL_MINUTES",
            "1440"
        )
    )

    AUTH_PASSWORD_RESET_TTL_MINUTES = int(
        os.getenv(
            "AUTH_PASSWORD_RESET_TTL_MINUTES",
            "60"
        )
    )

    AUTH_LOGIN_LIMIT = int(
        os.getenv(
            "AUTH_LOGIN_LIMIT",
            "8"
        )
    )

    AUTH_LOGIN_WINDOW_SECONDS = int(
        os.getenv(
            "AUTH_LOGIN_WINDOW_SECONDS",
            "900"
        )
    )

    AUTH_LOGIN_BLOCK_SECONDS = int(
        os.getenv(
            "AUTH_LOGIN_BLOCK_SECONDS",
            "900"
        )
    )

    AUTH_PASSWORD_RESET_LIMIT = int(
        os.getenv(
            "AUTH_PASSWORD_RESET_LIMIT",
            "5"
        )
    )

    AUTH_PASSWORD_RESET_WINDOW_SECONDS = int(
        os.getenv(
            "AUTH_PASSWORD_RESET_WINDOW_SECONDS",
            "900"
        )
    )

    AUTH_PASSWORD_RESET_BLOCK_SECONDS = int(
        os.getenv(
            "AUTH_PASSWORD_RESET_BLOCK_SECONDS",
            "900"
        )
    )

    AUTH_DOCUMENT_MAX_BYTES = int(
        os.getenv(
            "AUTH_DOCUMENT_MAX_BYTES",
            "10485760"
        )
    )

    DOCUMENT_ARCHIVE_DIR = os.getenv(
        "DOCUMENT_ARCHIVE_DIR",
        str(INSTANCE_DIR / "document_archive")
    )

    # ---------------------------------------------------------
    # FOCOST Contact / Compliance Emails
    # ---------------------------------------------------------
    # Environment variables take precedence.
    # The defaults below are used only when the corresponding
    # variable is not defined in .env.
    FOCOST_SUPPORT_EMAIL = os.getenv(
        "FOCOST_SUPPORT_EMAIL",
        "focostsupport@gmail.com"
    )

    FOCOST_PRIVACY_EMAIL = os.getenv(
        "FOCOST_PRIVACY_EMAIL",
        "focostprivacy@gmail.com"
    )

    FOCOST_SECURITY_EMAIL = os.getenv(
        "FOCOST_SECURITY_EMAIL",
        "focostsecurity@gmail.com"
    )