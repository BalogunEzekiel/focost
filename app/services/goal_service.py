from app.extensions import db

from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution

class GoalService:

    @staticmethod
    def create_goal(form, user_id):

        goal = Goal(
            user_id=user_id,
            title=form.title.data,
            goal_type=form.goal_type.data,
            target_amount=float(form.target_amount.data),
            target_date=form.target_date.data,
            priority=form.priority.data,
            notes=form.notes.data,
            status="In Progress",
        )

        db.session.add(goal)
        db.session.commit()

        return goal

    @staticmethod
    def update_goal(goal, form):

        goal.title = form.title.data
        goal.goal_type = form.goal_type.data
        goal.target_amount = float(form.target_amount.data)
        goal.target_date = form.target_date.data
        goal.priority = form.priority.data
        goal.notes = form.notes.data

        db.session.commit()

        return goal

    @staticmethod
    def delete_goal(goal):

        db.session.delete(goal)
        db.session.commit()

    @staticmethod
    def add_contribution(form, goal, user_id):

        contribution = GoalContribution(
            goal_id=goal.id,
            user_id=user_id,
            amount=float(form.amount.data),
            contribution_date=form.contribution_date.data,
            note=form.note.data
        )

        db.session.add(contribution)
        db.session.commit()

        return contribution

    @staticmethod
    def get_goal_statistics(user_id):

        goals = Goal.query.filter_by(
            user_id=user_id
        ).all()

        total_goals = len(goals)

        completed = 0
        overdue = 0
        in_progress = 0

        total_target = 0
        total_saved = 0

        for goal in goals:

            total_target += goal.target_amount
            total_saved += goal.saved_amount

            if goal.progress_status == "Completed":
                completed += 1

            elif goal.progress_status == "Overdue":
                overdue += 1

            else:
                in_progress += 1

        return {
            "total_goals": total_goals,
            "completed": completed,
            "overdue": overdue,
            "in_progress": in_progress,
            "total_target": total_target,
            "total_saved": total_saved,
            "remaining": total_target - total_saved
        }