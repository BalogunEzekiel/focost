def test_platform_page(client):
    response = client.get("/showcase/platform")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_security_page(client):
    response = client.get("/showcase/security")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_about_page(client):
    response = client.get("/showcase/about")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b"Ezekiel Balogun" in response.data


def test_support_page(client):
    response = client.get("/showcase/support")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b"Feedback" in response.data
