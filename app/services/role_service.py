from app.extensions import db
from app.models.user_role import UserRole
from app.models.role import Role


class RoleService:

    # ==========================================================
    # ASSIGN INITIAL ROLE
    # ==========================================================

    @staticmethod
    def assign_initial_role(
        user,
        role_slug,
        assigned_by=None
    ):
        """
        Assign the first and only role to a user.

        A user can never receive a second role.

        Once a role exists, the account's role is permanent.
        The user must create a new account/email to obtain
        another role.
        """

        # ------------------------------------------------------
        # User already has a role
        # ------------------------------------------------------

        if user.role_assignment:

            raise ValueError(
                "This account already has a role. "
                "A different role requires a new account "
                "with a unique email address."
            )

        # ------------------------------------------------------
        # Find role
        # ------------------------------------------------------

        role = Role.query.filter_by(
            slug=role_slug
        ).first()

        if not role:

            raise ValueError(
                f"Role '{role_slug}' does not exist."
            )

        if not role.is_active:

            raise ValueError(
                f"Role '{role_slug}' is inactive."
            )

        # ------------------------------------------------------
        # Create role assignment
        # ------------------------------------------------------

        assignment = UserRole(

            user_id=user.id,

            role_id=role.id,

            assigned_by_id=(
                assigned_by.id
                if assigned_by
                else None
            )

        )

        db.session.add(assignment)

        db.session.commit()

        return assignment


    # ==========================================================
    # GET USER ROLE
    # ==========================================================

    @staticmethod
    def get_user_role(user):

        if not user.role_assignment:
            return None

        return user.role_assignment.role


    # ==========================================================
    # CHECK WHETHER USER ALREADY HAS ROLE
    # ==========================================================

    @staticmethod
    def has_role(user):

        return user.role_assignment is not None