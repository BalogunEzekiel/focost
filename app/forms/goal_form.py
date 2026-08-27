from flask_wtf import FlaskForm

from wtforms import (
    StringField,
    SelectField,
    DecimalField,
    DateField,
    TextAreaField,
    SubmitField,
)

from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
)


class GoalForm(FlaskForm):

    title = StringField(
        "Goal Name",
        validators=[
            DataRequired(),
            Length(max=150)
        ]
    )

    goal_type = SelectField(
        "Goal Type",
        choices=[
            ("Emergency Fund", "Emergency Fund"),
            ("Vacation", "Vacation"),
            ("Car", "Car"),
            ("House", "House"),
            ("Education", "Education"),
            ("Business", "Business"),
            ("Investment", "Investment"),
            ("Retirement", "Retirement"),
            ("Other", "Other"),
        ],
        validators=[DataRequired()]
    )

    target_amount = DecimalField(
        "Target Amount",
        places=2,
        validators=[
            DataRequired(),
            NumberRange(min=1)
        ]
    )

    target_date = DateField(
        "Target Date",
        format="%Y-%m-%d",
        validators=[DataRequired()]
    )

    priority = SelectField(
        "Priority",
        choices=[
            ("High", "High"),
            ("Medium", "Medium"),
            ("Low", "Low"),
        ],
        default="Medium"
    )

    notes = TextAreaField(
        "Notes"
    )

    submit = SubmitField(
        "Save Goal"
    )