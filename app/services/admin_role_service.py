from collections import defaultdict

from app.extensions import db

from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.models.user import User
from app.models.audit_log import AuditLog


class AdminRoleService:
    """
    Business logic for Role Management.
    """

    # =========================================================
    # Dashboard Statistics
    # =========================================================

    @staticmethod
    def get_statistics():

        return {
            "total_roles": Role.query.count(),
            "system_roles": Role.query.filter_by(
                is_system=True
            ).count(),
            "custom_roles": Role.query.filter_by(
                is_system=False
            ).count(),
            "total_permissions": Permission.query.count(),
            "assigned_roles": UserRole.query.count()
        }

    # =========================================================
    # Role Listing
    # =========================================================

    @staticmethod
    def list_roles(
        page=1,
        per_page=15,
        search=""
    ):

        query = Role.query

        if search:

            search = f"%{search}%"

            query = query.filter(
                db.or_(
                    Role.name.ilike(search),
                    Role.slug.ilike(search),
                    Role.description.ilike(search)
                )
            )

        return (
            query
            .order_by(Role.name)
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )

    # =========================================================
    # Single Role
    # =========================================================

    @staticmethod
    def get_role(role_id):

        return Role.query.get_or_404(role_id)

    # =========================================================
    # CRUD
    # =========================================================

    @staticmethod
    def create_role(
        name,
        slug,
        description="",
        is_system=False
    ):

        role = Role(
            name=name,
            slug=slug,
            description=description,
            is_system=is_system
        )

        db.session.add(role)
        db.session.commit()

        return role

    @staticmethod
    def update_role(
        role,
        name,
        slug,
        description,
        is_system
    ):

        role.name = name
        role.slug = slug
        role.description = description
        role.is_system = is_system

        db.session.commit()

        return role

    @staticmethod
    def delete_role(role):

        db.session.delete(role)
        db.session.commit()

    @staticmethod
    def slug_exists(
        slug,
        exclude_id=None
    ):

        query = Role.query.filter_by(
            slug=slug
        )

        if exclude_id:

            query = query.filter(
                Role.id != exclude_id
            )

        return query.first() is not None

    # =========================================================
    # Permissions
    # =========================================================

    @staticmethod
    def get_role_permissions(role_id):

        return (
            Permission.query
            .join(
                RolePermission,
                Permission.id == RolePermission.permission_id
            )
            .filter(
                RolePermission.role_id == role_id
            )
            .order_by(
                Permission.module,
                Permission.action
            )
            .all()
        )

    @staticmethod
    def get_grouped_permissions():

        grouped = defaultdict(list)

        permissions = (
            Permission.query
            .order_by(
                Permission.module,
                Permission.action
            )
            .all()
        )

        for permission in permissions:

            grouped[
                permission.module
            ].append(permission)

        return dict(grouped)

    @staticmethod
    def get_assigned_permission_ids(role_id):

        ids = (
            RolePermission.query
            .filter_by(role_id=role_id)
            .with_entities(
                RolePermission.permission_id
            )
            .all()
        )

        return {
            permission_id
            for permission_id, in ids
        }

    # =========================================================
    # Users
    # =========================================================

    @staticmethod
    def get_role_users(role_id):

        return (
            User.query
            .join(
                UserRole,
                User.id == UserRole.user_id
            )
            .filter(
                UserRole.role_id == role_id
            )
            .order_by(
                User.first_name,
                User.last_name
            )
            .all()
        )

    # =========================================================
    # Activity
    # =========================================================

    @staticmethod
    def get_role_activity(
        role_id,
        limit=20
    ):

        role = Role.query.get(role_id)

        if not role:
            return []

        return (
            AuditLog.query
            .filter(
                AuditLog.resource == "Role",
                AuditLog.resource_id == role.public_id
            )
            .order_by(
                AuditLog.created_at.desc()
            )
            .limit(limit)
            .all()
        )