def test_budget_requires_authentication(client):
    response = client.get("/budget/")

    assert response.status_code in (302, 401)


def test_budget_add_requires_authentication(client):
    response = client.get("/budget/add")

    assert response.status_code in (302, 401)


def test_budget_authenticated(authenticated_client):
    response = authenticated_client.get("/budget/")

    assert response.status_code == 200


def test_budget_add_authenticated(authenticated_client):
    response = authenticated_client.get("/budget/add")

    assert response.status_code == 200