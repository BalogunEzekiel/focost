def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard")

    assert response.status_code in (302, 401)


def test_dashboard_home_route_exists(client):
    response = client.get("/")

    assert response.status_code in (200, 302, 401)


def test_dashboard_authenticated(authenticated_client):
    response = authenticated_client.get("/dashboard")

    assert response.status_code in (200, 302)