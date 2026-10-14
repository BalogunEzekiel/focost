import os
from pathlib import Path
from datetime import timedelta

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

    # ---------------------------------------------------------
    # PERMANENT LOGIN SESSION
    # ---------------------------------------------------------

    # A permanent session expires after 30 days.
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # Refresh the permanent session cookie during activity.
    SESSION_REFRESH_EACH_REQUEST = True

    # Keep authentication cookies secure.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Set SESSION_COOKIE_SECURE=true in production when using HTTPS.
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower()
        == "true"
    )

    # Flask-Login remember-me cookie settings.
    # The login route can use this duration if remember-me is enabled.
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower()
        == "true"
    )

    MAX_CONTENT_LENGTH = int(
        os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
    )

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = int(
        os.getenv("WTF_CSRF_TIME_LIMIT", 3600)
    )

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Read-only Mono Open Banking Connect. Private keys are environment-only.
    MONO_PUBLIC_KEY = os.getenv("MONO_PUBLIC_KEY", "").strip()
    MONO_SECRET_KEY = os.getenv("MONO_SECRET_KEY", "").strip()

    APP_NAME = "FOCOST"
    APP_VERSION = os.getenv("APP_VERSION", "2.2.0")
    APP_ENV = os.getenv("FLASK_ENV", "production")

    APP_BASE_URL = os.getenv(
        "APP_BASE_URL",
        "http://127.0.0.1:5000"
    ).rstrip("/")

    # ---------------------------------------------------------
    # WEB PUSH NOTIFICATIONS
    # ---------------------------------------------------------

    WEB_PUSH_ENABLED = (
        os.getenv("WEB_PUSH_ENABLED", "false").strip().lower()
        == "true"
    )

    WEB_PUSH_VAPID_PUBLIC_KEY = os.getenv(
        "WEB_PUSH_VAPID_PUBLIC_KEY", ""
    ).strip()

    WEB_PUSH_VAPID_PRIVATE_KEY = os.getenv(
        "WEB_PUSH_VAPID_PRIVATE_KEY", ""
    ).strip()

    WEB_PUSH_VAPID_CLAIMS_SUB = os.getenv(
        "WEB_PUSH_VAPID_CLAIMS_SUB",
        "mailto:focostsecurity@gmail.com"
    ).strip()

    # ---------------------------------------------------------
    # EMAIL VERIFICATION
    # ---------------------------------------------------------

    AUTH_EMAIL_VERIFICATION_REQUIRED = (
        os.getenv(
            "AUTH_EMAIL_VERIFICATION_REQUIRED",
            "true"
        ).strip().lower() == "true"
    )

    AUTH_EMAIL_VERIFICATION_TTL_MINUTES = int(
        os.getenv(
            "AUTH_EMAIL_VERIFICATION_TTL_MINUTES",
            "1440"
        )
    )

    # ---------------------------------------------------------
    # PASSWORD RECOVERY
    # ---------------------------------------------------------

    AUTH_PASSWORD_RESET_TTL_MINUTES = int(
        os.getenv(
            "AUTH_PASSWORD_RESET_TTL_MINUTES",
            "60"
        )
    )

    # ---------------------------------------------------------
    # LOGIN RATE LIMITING
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # PASSWORD RESET RATE LIMITING
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # DOCUMENT AND INTEGRATION UPLOADS
    # ---------------------------------------------------------

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

    INTEGRATION_UPLOAD_DIR = os.getenv(
        "INTEGRATION_UPLOAD_DIR",
        str(INSTANCE_DIR / "private_imports")
    )

    INTEGRATION_UPLOAD_RETENTION_DAYS = max(
        1,
        int(os.getenv("INTEGRATION_UPLOAD_RETENTION_DAYS", "365"))
    )

    # ---------------------------------------------------------
    # FOCOST CONTACT / COMPLIANCE EMAILS
    # ---------------------------------------------------------
    # Environment variables take precedence.
    # Defaults apply only when the corresponding variable is absent.

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
