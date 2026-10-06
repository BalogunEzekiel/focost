from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, DateField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange


class ExpenseForm(FlaskForm):
    category = SelectField("Category", choices=[], validators=[DataRequired()])
    merchant = StringField("Merchant / Vendor", validators=[DataRequired(), Length(max=150)])
    description = StringField("Description", validators=[Length(max=255)])
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("Cash", "Cash"), ("Bank Transfer", "Bank Transfer"),
            ("Debit Card", "Debit Card"), ("Credit Card", "Credit Card"),
            ("POS", "POS"), ("Mobile Money", "Mobile Money"),
            ("Cheque", "Cheque"), ("Other", "Other"),
        ],
        validators=[DataRequired()],
    )
    expense_date = DateField("Expense Date", format="%Y-%m-%d", validators=[DataRequired()])
    notes = TextAreaField("Notes", validators=[Length(max=1000)])
    recurring = BooleanField("Recurring Expense")
    submit = SubmitField("Save Expense")
