def test_application_configuration(app):
    assert app.config["APP_NAME"] == "FOCOST"
    assert app.config["APP_VERSION"]
    assert app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] is False


def test_session_security_configuration(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"

    assert app.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert app.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"


def test_request_limit_is_configured(app):
    assert app.config["MAX_CONTENT_LENGTH"] > 0


def test_csrf_configuration_exists(app):
    assert "WTF_CSRF_ENABLED" in app.config
    assert "WTF_CSRF_TIME_LIMIT" in app.config


def test_database_configuration_exists(app):
    assert app.config["SQLALCHEMY_DATABASE_URI"]