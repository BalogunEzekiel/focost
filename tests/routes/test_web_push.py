from html.parser import HTMLParser

from app.extensions import db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.web_push_subscription import WebPushSubscription


VALID_SUBSCRIPTION = {
    "endpoint": "https://push.example.test/subscription/test-001",
    "keys": {
        "p256dh": "test-public-encryption-key",
        "auth": "test-authentication-secret",
    },
}


class CSRFTokenParser(HTMLParser):
    """Extract a CSRF token from a meta tag or hidden form field."""

    def __init__(self):
        super().__init__()
        self.token = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if (
            tag == "meta"
            and attrs.get("name") == "csrf-token"
        ):
            self.token = attrs.get("content")

        elif (
            tag == "input"
            and attrs.get("name") == "csrf_token"
        ):
            self.token = attrs.get("value")


def csrf_headers(client, authenticated=True):
    """Return request headers containing a valid application CSRF token."""

    page = "/dashboard" if authenticated else "/auth/login"
    response = client.get(page)

    assert response.status_code == 200, (
        f"Could not load {page} to obtain a CSRF token. "
        f"Received HTTP {response.status_code}."
    )

    parser = CSRFTokenParser()
    parser.feed(response.get_data(as_text=True))

    assert parser.token, (
        f"No CSRF token was found on {page}. "
        "Check the page's CSRF meta tag or hidden form field."
    )

    return {"X-CSRFToken": parser.token}


def enable_test_web_push(app):
    """Enable Web Push using test-only configuration values."""

    app.config.update(
        WEB_PUSH_ENABLED=True,
        WEB_PUSH_VAPID_PUBLIC_KEY="test-public-vapid-key",
        WEB_PUSH_VAPID_PRIVATE_KEY="test-private-vapid-key",
    )


def test_web_push_public_key_requires_authentication(client):
    response = client.get("/notifications/web-push/public-key")

    assert response.status_code in (302, 401)


def test_web_push_public_key_returns_503_when_disabled(
    authenticated_client,
):
    response = authenticated_client.get(
        "/notifications/web-push/public-key"
    )

    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_web_push_public_key_returns_configured_key(
    authenticated_client,
):
    enable_test_web_push(authenticated_client.application)

    response = authenticated_client.get(
        "/notifications/web-push/public-key"
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "publicKey": "test-public-vapid-key",
    }


def test_web_push_subscribe_returns_503_when_disabled(
    authenticated_client,
):
    response = authenticated_client.post(
        "/notifications/web-push/subscribe",
        json={"subscription": VALID_SUBSCRIPTION},
        headers=csrf_headers(authenticated_client),
    )

    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_web_push_subscribe_rejects_invalid_endpoint(
    authenticated_client,
):
    enable_test_web_push(authenticated_client.application)

    invalid_subscription = {
        "endpoint": "http://push.example.test/subscription/test-001",
        "keys": VALID_SUBSCRIPTION["keys"],
    }

    response = authenticated_client.post(
        "/notifications/web-push/subscribe",
        json={"subscription": invalid_subscription},
        headers=csrf_headers(authenticated_client),
    )

    assert response.status_code == 400


def test_web_push_subscribe_saves_subscription_and_opt_in(
    authenticated_client,
    user,
    app,
):
    enable_test_web_push(app)

    response = authenticated_client.post(
        "/notifications/web-push/subscribe",
        json={"subscription": VALID_SUBSCRIPTION},
        headers=csrf_headers(authenticated_client),
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True

    with app.app_context():
        saved = WebPushSubscription.query.filter_by(
            endpoint=VALID_SUBSCRIPTION["endpoint"]
        ).one()

        assert saved.user_id == user.id
        assert saved.p256dh == VALID_SUBSCRIPTION["keys"]["p256dh"]
        assert saved.auth == VALID_SUBSCRIPTION["keys"]["auth"]
        assert saved.is_enabled is True
        assert saved.is_active is True
        assert saved.last_seen_at is not None

        settings = UserSettings.query.filter_by(
            user_id=user.id
        ).one()

        assert settings.get_preferences()["notifications"]["push"] is True


def test_web_push_subscribe_rejects_endpoint_owned_by_another_user(
    authenticated_client,
    user,
    app,
):
    enable_test_web_push(app)

    with app.app_context():
        other_user = User(
            first_name="Other",
            last_name="User",
            email="other-push-user@example.com",
        )
        other_user.set_password("OtherPassword123!")

        db.session.add(other_user)
        db.session.flush()

        existing = WebPushSubscription(
            user_id=other_user.id,
            endpoint=VALID_SUBSCRIPTION["endpoint"],
            p256dh="existing-public-key",
            auth="existing-auth-key",
            is_enabled=True,
            is_active=True,
        )

        db.session.add(existing)
        db.session.commit()

    response = authenticated_client.post(
        "/notifications/web-push/subscribe",
        json={"subscription": VALID_SUBSCRIPTION},
        headers=csrf_headers(authenticated_client),
    )

    assert response.status_code == 409
    assert response.get_json()["success"] is False

    with app.app_context():
        saved = WebPushSubscription.query.filter_by(
            endpoint=VALID_SUBSCRIPTION["endpoint"]
        ).one()

        assert saved.user_id != user.id


def test_web_push_unsubscribe_requires_authentication(client):
    response = client.post(
        "/notifications/web-push/unsubscribe",
        json={"endpoint": VALID_SUBSCRIPTION["endpoint"]},
        headers=csrf_headers(client, authenticated=False),
    )

    assert response.status_code in (302, 401)


def test_web_push_unsubscribe_disables_subscription_and_opt_out(
    authenticated_client,
    user,
    app,
):
    with app.app_context():
        subscription = WebPushSubscription(
            user_id=user.id,
            endpoint=VALID_SUBSCRIPTION["endpoint"],
            p256dh=VALID_SUBSCRIPTION["keys"]["p256dh"],
            auth=VALID_SUBSCRIPTION["keys"]["auth"],
            is_enabled=True,
            is_active=True,
        )

        db.session.add(subscription)

        settings = UserSettings(user_id=user.id)
        settings.set_preferences({
            "notifications": {"push": True}
        })

        db.session.add(settings)
        db.session.commit()

    response = authenticated_client.post(
        "/notifications/web-push/unsubscribe",
        json={"endpoint": VALID_SUBSCRIPTION["endpoint"]},
        headers=csrf_headers(authenticated_client),
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True

    with app.app_context():
        saved = WebPushSubscription.query.filter_by(
            endpoint=VALID_SUBSCRIPTION["endpoint"]
        ).one()

        assert saved.is_enabled is False
        assert saved.is_active is False

        settings = UserSettings.query.filter_by(
            user_id=user.id
        ).one()

        assert settings.get_preferences()["notifications"]["push"] is False


def test_web_push_unsubscribe_rejects_missing_endpoint(
    authenticated_client,
):
    response = authenticated_client.post(
        "/notifications/web-push/unsubscribe",
        json={},
        headers=csrf_headers(authenticated_client),
    )

    assert response.status_code == 400
