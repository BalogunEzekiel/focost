import json
from datetime import date

from app.extensions import db
from app.models.income import Income
from app.models.expense import Expense


def test_account_export_contains_user_data(
    app,
    authenticated_client,
    user,
):

    with app.app_context():

        db.session.add(
            Income(
                user_id=user.id,
                source="Salary",
                category="Employment",
                amount=500000,
                received_date=date.today(),
            )
        )

        db.session.add(
            Expense(
                user_id=user.id,
                category="Food",
                merchant="Restaurant",
                amount=50000,
                payment_method="Card",
                expense_date=date.today(),
            )
        )

        db.session.commit()

    response = authenticated_client.get(
        "/account/export"
    )

    assert response.status_code == 200

    payload = json.loads(
        response.data.decode("utf-8")
    )

    assert payload["product"] == "FOCOST"
    assert payload["schema_version"] == "1.0"

    assert payload["user"]["email"] == (
        "testuser@example.com"
    )

    assert len(payload["income"]) == 1
    assert len(payload["expenses"]) == 1

    assert payload["income"][0]["amount"] == 500000
    assert payload["expenses"][0]["amount"] == 50000