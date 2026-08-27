from datetime import datetime
from sqlalchemy import or_
from datetime import datetime



from app.extensions import db
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role


class AdminUserService:

    @staticmethod
    def get_user(public_id):

        return User.query.filter_by(
            public_id=public_id
        ).first()

    @staticmethod
    def list_users(page=1, search=""):

        query = User.query

        if search:

            query = query.filter(
                or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )

        return query.order_by(
            User.created_at.desc()
        ).paginate(
            page=page,
            per_page=10,
            error_out=False
        )


    @staticmethod
    def user_statistics():

        now = datetime.utcnow()

        start_month = datetime(
            now.year,
            now.month,
            1
        )

        return {

            "total": User.query.count(),

            "active": User.query.filter_by(
                is_active=True
            ).count(),

            "inactive": User.query.filter_by(
                is_active=False
            ).count(),

            "new_this_month": User.query.filter(
                User.created_at >= start_month
            ).count()

        }

    @staticmethod
    def create_user(
        first_name,
        last_name,
        email,
        password,
        role_slug=None
    ):

        email = email.lower().strip()

        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists.")

        user = User(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email
        )

        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        if role_slug:

            role = Role.query.filter_by(
                slug=role_slug
            ).first()

            if role:

                db.session.add(
                    UserRole(
                        user_id=user.id,
                        role_id=role.id
                    )
                )

        db.session.commit()

        return user

    @staticmethod
    def update_user(
        public_id,
        **data
    ):

        user = AdminUserService.get_user(public_id)

        if not user:
            return None

        if "first_name" in data:
            user.first_name = data["first_name"].strip()

        if "last_name" in data:
            user.last_name = data["last_name"].strip()

        if "email" in data:

            email = data["email"].lower().strip()

            exists = User.query.filter(
                User.email == email,
                User.id != user.id
            ).first()

            if exists:
                raise ValueError("Email already exists.")

            user.email = email

        if data.get("password"):
            user.set_password(data["password"])

        db.session.commit()

        return user

    @staticmethod
    def activate_user(public_id):

        user = AdminUserService.get_user(public_id)

        if not user:
            return None

        user.is_active = True

        db.session.commit()

        return user

    @staticmethod
    def deactivate_user(public_id):

        user = AdminUserService.get_user(public_id)

        if not user:
            return None

        user.is_active = False

        db.session.commit()

        return user

    @staticmethod
    def delete_user(public_id):

        user = AdminUserService.get_user(public_id)

        if not user:
            return False

        UserRole.query.filter_by(
            user_id=user.id
        ).delete()

        db.session.delete(user)

        db.session.commit()

        return True

    @staticmethod
    def assign_role(
        user,
        role_slug
    ):

        role = Role.query.filter_by(
            slug=role_slug
        ).first()

        if not role:
            raise ValueError("Role not found.")

        exists = UserRole.query.filter_by(
            user_id=user.id,
            role_id=role.id
        ).first()

        if exists:
            return

        db.session.add(
            UserRole(
                user_id=user.id,
                role_id=role.id
            )
        )

        db.session.commit()

    @staticmethod
    def remove_role(
        user,
        role_slug
    ):

        role = Role.query.filter_by(
            slug=role_slug
        ).first()

        if not role:
            return

        assignment = UserRole.query.filter_by(
            user_id=user.id,
            role_id=role.id
        ).first()

        if assignment:

            db.session.delete(assignment)

            db.session.commit()

    @staticmethod
    def change_role(
        user,
        role_slug
    ):

        role = Role.query.filter_by(
            slug=role_slug
        ).first()

        if not role:
            raise ValueError("Role not found.")

        UserRole.query.filter_by(
            user_id=user.id
        ).delete(
            synchronize_session=False
        )

        db.session.add(
            UserRole(
                user_id=user.id,
                role_id=role.id
            )
        )

        db.session.commit()