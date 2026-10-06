def test_feedback_page_is_public(client):
    response = client.get("/feedback/")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b"Send feedback" in response.data


def test_feedback_can_be_submitted_without_account(client, app):
    app.config["WTF_CSRF_ENABLED"] = False

    response = client.post(
        "/feedback/",
        data={
            "submitted_name": "Public Visitor",
            "submitted_email": "visitor@example.com",
            "category": "feature",
            "subject": "Add a cash-flow view",
            "message": "A dedicated cash-flow view would make the dashboard more useful.",
            "rating": "5",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/feedback/")

    from app.models.feedback import Feedback

    with app.app_context():
        item = Feedback.query.filter_by(
            submitted_email="visitor@example.com"
        ).first()

        assert item is not None
        assert item.category == "feature"
        assert item.status == "new"
        assert item.priority == "normal"
        assert item.rating == 5
