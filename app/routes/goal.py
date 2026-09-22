from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
)

from flask_login import (
    login_required,
    current_user,
)

from app.extensions import db

from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.expense import Expense

from app.forms.goal_form import GoalForm
from app.forms.goal_contribution_form import GoalContributionForm

from app.services.goal_service import GoalService


goal_bp = Blueprint(
    "goal",
    __name__,
    url_prefix="/goals",
)


# =====================================
# LIST GOALS
# =====================================

@goal_bp.route("/")
@login_required
def list_goals():

    goals = (
        Goal.query
        .filter_by(user_id=current_user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )

    stats = GoalService.get_goal_statistics(
        current_user.id
    )

    return render_template(
        "goal/goals.html",
        goals=goals,
        stats=stats,
    )


# =====================================
# ADD GOAL
# =====================================

@goal_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():

    form = GoalForm()

    if form.validate_on_submit():

        GoalService.create_goal(
            form,
            current_user.id
        )

        flash(
            "Goal created successfully.",
            "success"
        )

        return redirect(
            url_for("goal.list_goals")
        )

    return render_template(
        "goal/add.html",
        form=form,
    )


# =====================================
# EDIT GOAL
# =====================================

@goal_bp.route("/edit/<int:goal_id>", methods=["GET", "POST"])
@login_required
def edit(goal_id):

    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first_or_404()

    form = GoalForm(obj=goal)

    if form.validate_on_submit():

        try:
            GoalService.update_goal(goal, form)
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("goal/edit.html", form=form, goal=goal)

        flash("Goal updated successfully.", "success")

        return redirect(
            url_for("goal.list_goals")
        )

    return render_template(
        "goal/edit.html",
        form=form,
        goal=goal,
    )


# =====================================
# DELETE GOAL
# =====================================

@goal_bp.route("/delete/<int:goal_id>")
@login_required
def delete(goal_id):

    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first_or_404()

    GoalService.delete_goal(goal)

    flash(
        "Goal deleted successfully.",
        "success"
    )

    return redirect(
        url_for("goal.list_goals")
    )


# =====================================
# GOAL DETAILS
# =====================================

@goal_bp.route("/<int:goal_id>")
@login_required
def detail(goal_id):

    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first_or_404()

    contributions = (
        GoalContribution.query
        .filter_by(goal_id=goal.id)
        .order_by(
            GoalContribution.contribution_date.desc()
        )
        .all()
    )

    return render_template(
        "goal/detail.html",
        goal=goal,
        contributions=contributions,
    )


# =====================================
# ADD CONTRIBUTION
# =====================================

@goal_bp.route(
    "/<int:goal_id>/contribute",
    methods=["GET", "POST"]
)
@login_required
def contribute(goal_id):

    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first_or_404()

    if goal.progress_percentage >= 100:
        flash("This goal has already been achieved. Additional contributions are not permitted.", "info")
        return redirect(url_for("goal.detail", goal_id=goal.id))

    form = GoalContributionForm()

    if form.validate_on_submit():

        try:
            GoalService.add_contribution(
                form,
                goal,
                current_user.id
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template(
                "goal/contribute.html",
                form=form,
                goal=goal,
            )

        flash(
            "Contribution recorded and deducted from your available balance.",
            "success"
        )

        return redirect(
            url_for(
                "goal.detail",
                goal_id=goal.id
            )
        )

    return render_template(
        "goal/contribute.html",
        form=form,
        goal=goal,
    )


# =====================================
# CONTRIBUTION HISTORY
# =====================================

@goal_bp.route("/<int:goal_id>/history")
@login_required
def contributions(goal_id):

    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first_or_404()

    contributions = (
        GoalContribution.query
        .filter_by(goal_id=goal.id)
        .order_by(
            GoalContribution.contribution_date.desc()
        )
        .all()
    )

    return render_template(
        "goal/contributions.html",
        goal=goal,
        contributions=contributions,
    )

@goal_bp.route(
    "/contribution/<int:contribution_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_contribution(contribution_id):

    contribution = (
        GoalContribution.query
        .join(Goal)
        .filter(
            GoalContribution.id == contribution_id,
            Goal.user_id == current_user.id
        )
        .first_or_404()
    )

    form = GoalContributionForm(obj=contribution)

    if form.validate_on_submit():
        try:
            GoalService.update_contribution(contribution, form, current_user.id)
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("goal/edit_contribution.html", form=form, contribution=contribution, goal=contribution.goal)

        flash("Contribution updated successfully.", "success")
        return redirect(url_for("goal.contributions", goal_id=contribution.goal_id))

    return render_template(
        "goal/edit_contribution.html",
        form=form,
        contribution=contribution,
        goal=contribution.goal
    )

@goal_bp.route("/contribution/<int:contribution_id>/delete")
@login_required
def delete_contribution(contribution_id):

    contribution = (
        GoalContribution.query
        .join(Goal)
        .filter(
            GoalContribution.id == contribution_id,
            Goal.user_id == current_user.id
        )
        .first_or_404()
    )

    goal_id = contribution.goal_id
    linked_expense = contribution.expense

    db.session.delete(contribution)
    if linked_expense:
        db.session.delete(linked_expense)
    db.session.commit()

    flash(
        "Contribution deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "goal.contributions",
            goal_id=goal_id
        )
    )