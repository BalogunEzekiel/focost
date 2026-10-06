from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class BudgetForm(FlaskForm):
    category = SelectField("Expense Category", choices=[], validators=[DataRequired()])
    amount = DecimalField("Budget Amount", validators=[DataRequired(), NumberRange(min=1)])
    period = SelectField(
        "Period",
        choices=[("Monthly", "Monthly"), ("Weekly", "Weekly"), ("Yearly", "Yearly")],
        default="Monthly",
    )
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[DataRequired()])
    submit = SubmitField("Save Budget")
