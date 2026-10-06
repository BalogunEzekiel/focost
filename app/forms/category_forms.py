from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length


class CategoryForm(FlaskForm):
    category_type = SelectField(
        "Category Type",
        choices=[("income", "Income"), ("expense", "Expense")],
        validators=[DataRequired()],
    )
    name = StringField("Category Name", validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField("Description", validators=[Length(max=255)])
    submit = SubmitField("Save Category")
