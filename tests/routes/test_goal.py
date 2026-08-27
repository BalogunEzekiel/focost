def test_goals_require_authentication(client):
    response = client.get("/goals/")

    assert response.status_code in (302, 401)


def test_goal_add_requires_authentication(client):
    response = client.get("/goals/add")

    assert response.status_code in (302, 401)


def test_goals_authenticated(authenticated_client):
    response = authenticated_client.get("/goals/")

    assert response.status_code == 200


def test_goal_add_authenticated(authenticated_client):
    response = authenticated_client.get("/goals/add")

    assert response.status_code == 200