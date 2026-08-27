def test_income_requires_authentication(client):
    response = client.get("/income/")

    assert response.status_code in (302, 401)


def test_income_add_requires_authentication(client):
    response = client.get("/income/add")

    assert response.status_code in (302, 401)


def test_income_authenticated(authenticated_client):
    response = authenticated_client.get("/income/")

    assert response.status_code == 200


def test_income_add_authenticated(authenticated_client):
    response = authenticated_client.get("/income/add")

    assert response.status_code == 200