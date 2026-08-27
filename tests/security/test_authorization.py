def test_authenticated_user_can_access_income(
    authenticated_client,
):

    response = authenticated_client.get(
        "/income/"
    )

    assert response.status_code == 200


def test_authenticated_user_can_access_expense(
    authenticated_client,
):

    response = authenticated_client.get(
        "/expense/"
    )

    assert response.status_code == 200


def test_authenticated_user_can_access_budget(
    authenticated_client,
):

    response = authenticated_client.get(
        "/budget/"
    )

    assert response.status_code == 200


def test_authenticated_user_can_access_goals(
    authenticated_client,
):

    response = authenticated_client.get(
        "/goals/"
    )

    assert response.status_code == 200