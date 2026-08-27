def test_platform_page(client):
    response = client.get("/showcase/platform")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_security_page(client):
    response = client.get("/showcase/security")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")