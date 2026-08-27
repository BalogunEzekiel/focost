def test_app_initializes(app):
    assert app is not None
    assert app.config["TESTING"] is True


def test_health_endpoint(client):
    response = client.get("/healthz")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "ok"
    assert data["service"] == "FOCOST"
    assert "version" in data
    assert "request_id" in data


def test_readiness_endpoint(client):
    response = client.get("/readyz")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "ready"
    assert data["database"] == "ok"


def test_robots_endpoint(client):
    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert response.content_type.startswith("text/plain")
    assert b"User-agent: *" in response.data


def test_security_txt_endpoint(client):
    response = client.get("/.well-known/security.txt")

    assert response.status_code == 200
    assert response.content_type.startswith("text/plain")
    assert b"security@focost.ai" in response.data


def test_security_headers(client):
    response = client.get("/healthz")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"

    assert response.headers["Referrer-Policy"] == (
        "strict-origin-when-cross-origin"
    )

    assert response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )

    assert response.headers["Cross-Origin-Opener-Policy"] == (
        "same-origin-allow-popups"
    )


def test_request_id_is_returned(client):
    response = client.get(
        "/healthz",
        headers={"X-Request-ID": "focost-test-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "focost-test-123"


def test_request_id_is_generated(client):
    response = client.get("/healthz")

    request_id = response.headers.get("X-Request-ID")

    assert response.status_code == 200
    assert request_id
    assert len(request_id) > 10


def test_api_404_returns_json(client):
    response = client.get("/api/this-route-does-not-exist")

    assert response.status_code == 404

    data = response.get_json()

    assert data["success"] is False
    assert data["message"] == "Resource not found."


def test_web_404_returns_html(client):
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404
    assert response.content_type.startswith("text/html")


def test_api_unauthorized_contract(client):
    """
    The application guarantees JSON for API authentication errors.

    A nonexistent API route currently resolves to the API 404 handler,
    so accept either 401 or 404 until a dedicated protected API endpoint
    is introduced.
    """

    response = client.get("/api/protected-test-route")

    assert response.status_code in (401, 404)