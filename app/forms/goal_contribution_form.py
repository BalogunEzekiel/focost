from flask_wtf import FlaskForm

from wtforms import (
    DecimalField,
    DateField,
    TextAreaField,
    SubmitField,
)

from wtforms.validators import (
    DataRequired,
    NumberRange,
)


class GoalContributionForm(FlaskForm):

    amount = DecimalField(
        "Contribution Amount",
        places=2,
        validators=[
            DataRequired(),
            NumberRange(min=1)
        ]
    )

    contribution_date = DateField(
        "Contribution Date",
        format="%Y-%m-%d",
        validators=[
            DataRequired()
        ]
    )

    note = TextAreaField(
        "Note"
    )

    submit = SubmitField(
        "Add Contribution"
    )