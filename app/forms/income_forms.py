from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    DecimalField,
    DateField,
    TextAreaField,
    BooleanField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange


class IncomeForm(FlaskForm):

    source = StringField(
        "Income Source",
        validators=[
            DataRequired(),
            Length(max=150)
        ]
    )

    category = SelectField(
        "Category",
        choices=[
            ("Salary", "Salary"),
            ("Business", "Business"),
            ("Freelance", "Freelance"),
            ("Investment", "Investment"),
            ("Rental", "Rental Income"),
            ("Commission", "Commission"),
            ("Ride Business", "Ride Business"),
            ("Gift", "Gift"),
            ("Bonus", "Bonus"),
            ("Dividend", "Dividend"),
            ("Other", "Other"),
        ],
        validators=[DataRequired()]
    )

    amount = DecimalField(
        "Amount",
        places=2,
        validators=[
            DataRequired(),
            NumberRange(min=0.01)
        ]
    )

    received_date = DateField(
        "Received Date",
        format="%Y-%m-%d",
        validators=[DataRequired()]
    )

    notes = TextAreaField(
        "Notes",
        validators=[Length(max=1000)]
    )

    recurring = BooleanField(
        "Recurring Income"
    )

    submit = SubmitField("Save Income")