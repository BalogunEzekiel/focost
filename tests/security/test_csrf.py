def test_csrf_is_enabled_in_application_config(app):

    assert app.config["WTF_CSRF_ENABLED"] is True


def test_csrf_time_limit_is_positive(app):

    assert app.config["WTF_CSRF_TIME_LIMIT"] > 0