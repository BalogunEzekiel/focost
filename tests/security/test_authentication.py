def test_protected_income_requires_login(client):
    response = client.get("/income/")

    assert response.status_code in (302, 401)


def test_protected_expense_requires_login(client):
    response = client.get("/expense/")

    assert response.status_code in (302, 401)


def test_protected_budget_requires_login(client):
    response = client.get("/budget/")

    assert response.status_code in (302, 401)


def test_protected_goal_requires_login(client):
    response = client.get("/goals/")

    assert response.status_code in (302, 401)


def test_protected_notifications_requires_login(client):
    response = client.get("/notifications/")

    assert response.status_code in (302, 401)


def test_protected_account_export_requires_login(client):
    response = client.get("/account/export")

    assert response.status_code in (302, 401)