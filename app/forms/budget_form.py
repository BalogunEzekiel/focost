from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    DecimalField,
    SelectField,
    DateField,
    SubmitField,
)
from wtforms.validators import DataRequired, NumberRange


class BudgetForm(FlaskForm):

    category = SelectField(
        "Category",
        choices=[
            ("Food", "Food"),
            ("Transportation", "Transportation"),
            ("Housing", "Housing"),
            ("Telephone", "Telephone"),
            ("Utilities", "Utilities"),
            ("Gas", "Gas"),
            ("Healthcare", "Healthcare"),
            ("Education", "Education"),
            ("Entertainment", "Entertainment"),
            ("Shopping", "Shopping"),
            ("Petrol", "Petrol"),
            ("Petrol Contribution", "Petrol Contribution"),
            ("Insurance", "Insurance"),
            ("Travel", "Travel"),
            ("Rent", "Rent"),
            ("Repairs", "Repairs"),
            ("Family", "Family"),
            ("Toiletries", "Toiletries"),
            ("Investment", "Investment"),
            ("Clothing", "Clothing"),
            ("Grooming/Beauty", "Grooming/Beauty"),
            ("Tax", "Tax"),
            ("Gift", "Gift"),
            ("Salary", "Salary"),
            ("Business", "Business"),
            ("Other", "Other"),
        ],
        validators=[DataRequired()],
    )

    amount = DecimalField(
        "Budget Amount",
        validators=[
            DataRequired(),
            NumberRange(min=1)
        ],
    )

    period = SelectField(
        "Period",
        choices=[
            ("Monthly", "Monthly"),
            ("Weekly", "Weekly"),
            ("Yearly", "Yearly"),
        ],
        default="Monthly",
    )

    start_date = DateField(
        "Start Date",
        validators=[DataRequired()],
    )

    end_date = DateField(
        "End Date",
        validators=[DataRequired()],
    )

    submit = SubmitField("Save Budget")