def test_expense_requires_authentication(client):
    response = client.get("/expense/")

    assert response.status_code in (302, 401)


def test_expense_add_requires_authentication(client):
    response = client.get("/expense/add")

    assert response.status_code in (302, 401)


def test_expense_authenticated(authenticated_client):
    response = authenticated_client.get("/expense/")

    assert response.status_code == 200


def test_expense_add_authenticated(authenticated_client):
    response = authenticated_client.get("/expense/add")

    assert response.status_code == 200