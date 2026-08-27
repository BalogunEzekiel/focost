def test_notifications_requires_authentication(client):
    response = client.get("/notifications/")

    assert response.status_code in (302, 401)


def test_notifications_api_requires_authentication(client):
    response = client.get("/notifications/api")

    assert response.status_code in (302, 401)


def test_notifications_authenticated(authenticated_client):
    response = authenticated_client.get("/notifications/")

    assert response.status_code == 200


def test_notifications_api_authenticated(authenticated_client):
    response = authenticated_client.get("/notifications/api")

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None