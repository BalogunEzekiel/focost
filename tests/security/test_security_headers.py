def test_security_headers_present(client):

    response = client.get("/healthz")

    expected = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "Referrer-Policy": (
            "strict-origin-when-cross-origin"
        ),
        "Permissions-Policy": (
            "camera=(), microphone=(), "
            "geolocation=(), payment=()"
        ),
        "Cross-Origin-Opener-Policy": (
            "same-origin-allow-popups"
        ),
    }

    for header, value in expected.items():

        assert response.headers.get(header) == value


def test_hsts_not_forced_on_http(client):

    response = client.get("/healthz")

    assert "Strict-Transport-Security" not in response.headers