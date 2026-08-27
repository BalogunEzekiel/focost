def test_login_page_is_public(client):
    response = client.get("/auth/login")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_register_page_is_public(client):
    response = client.get("/auth/register")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_no_access_page_is_public(client):
    response = client.get("/auth/no-access")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_logout_route_is_available(client):
    response = client.get("/auth/logout")

    assert response.status_code in (302, 401)