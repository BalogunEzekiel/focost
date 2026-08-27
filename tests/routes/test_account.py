def test_account_export_requires_authentication(client):
    response = client.get("/account/export")

    assert response.status_code in (302, 401)


def test_account_export_authenticated(authenticated_client):
    response = authenticated_client.get("/account/export")

    assert response.status_code == 200

    assert (
        response.content_type.startswith("application/json")
        or response.content_type.startswith("application/octet-stream")
    )