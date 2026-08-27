def test_reports_transactions_requires_authentication(client):
    response = client.get("/reports/transactions")

    assert response.status_code in (302, 401)


def test_reports_transactions_authenticated(authenticated_client):
    response = authenticated_client.get("/reports/transactions")

    assert response.status_code == 200