from collections import defaultdict

from app.extensions import db

from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.models.user import User
from app.models.audit_log import AuditLog


class AdminRoleService:
    """Authoritative role-management policy and persistence."""

    @staticmethod
    def get_statistics():
        return {
            "total_roles": Role.query.count(),
            "system_roles": Role.query.filter_by(is_system=True).count(),
            "custom_roles": Role.query.filter_by(is_system=False).count(),
            "total_permissions": Permission.query.count(),
            "assigned_roles": UserRole.query.count(),
        }

    @staticmethod
    def list_roles(page=1, per_page=15, search=""):
        query = Role.query

        if search:
            search = f"%{search}%"
            query = query.filter(
                db.or_(
                    Role.name.ilike(search),
                    Role.slug.ilike(search),
                    Role.description.ilike(search),
                )
            )

        return query.order_by(Role.group_slug, Role.name).paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )

    @staticmethod
    def get_role(role_id):
        return Role.query.get_or_404(role_id)

    @staticmethod
    def create_role(name, slug, description="", is_system=False):
        # UI/API role creation is for custom administrative roles only.
        # System roles are provisioned by RBACSeed and their identifiers are
        # reserved forever.
        slug = (slug or "").strip().lower()
        if not slug:
            raise ValueError("Role slug is required.")
        if slug in {"super_admin", "admin", "user"}:
            raise ValueError(
                "The reserved system role identifiers cannot be used for custom roles."
            )
        if is_system:
            raise PermissionError(
                "System roles can only be provisioned by the system seed."
            )

        role = Role(
            name=(name or "").strip(),
            slug=slug,
            description=(description or "").strip() or None,
            is_system=False,
            group_slug="admin",
        )

        if not role.name:
            raise ValueError("Role name is required.")

        db.session.add(role)
        db.session.commit()
        return role

    @staticmethod
    def update_role(role, name, slug, description, is_system=None):
        if not role:
            raise ValueError("Role not found.")

        submitted_slug = (slug or "").strip().lower()
        if submitted_slug and submitted_slug != role.slug:
            raise ValueError(
                "Role slugs are immutable system identifiers and cannot be changed."
            )

        if role.slug in {"super_admin", "admin", "user"}:
            expected_group = role.slug
            if role.group_slug != expected_group:
                raise ValueError("System role group is inconsistent with its slug.")
        elif role.group_slug != "admin":
            raise ValueError("Custom roles must belong to the admin group.")

        role.name = (name or "").strip()
        role.description = (description or "").strip() or None

        if not role.name:
            raise ValueError("Role name is required.")

        db.session.commit()
        return role

    @staticmethod
    def delete_role(role):
        if role.is_system or role.slug in {"super_admin", "admin", "user"}:
            raise PermissionError("System roles cannot be deleted.")

        assigned_users = UserRole.query.filter_by(role_id=role.id).count()
        if assigned_users:
            raise ValueError(
                "This role is assigned to users. Reassign those users before deleting the role."
            )

        db.session.delete(role)
        db.session.commit()

    @staticmethod
    def slug_exists(slug, exclude_id=None):
        query = Role.query.filter_by(slug=(slug or "").strip().lower())
        if exclude_id:
            query = query.filter(Role.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def get_role_permissions(role_id):
        return (
            Permission.query
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role_id == role_id)
            .order_by(Permission.module, Permission.action)
            .all()
        )

    @staticmethod
    def get_grouped_permissions():
        grouped = defaultdict(list)
        permissions = Permission.query.order_by(
            Permission.module,
            Permission.action,
        ).all()
        for permission in permissions:
            grouped[permission.module].append(permission)
        return dict(grouped)

    @staticmethod
    def get_assigned_permission_ids(role_id):
        ids = (
            RolePermission.query
            .filter_by(role_id=role_id)
            .with_entities(RolePermission.permission_id)
            .all()
        )
        return {permission_id for permission_id, in ids}

    @staticmethod
    def get_role_users(role_id):
        return (
            User.query
            .join(UserRole, User.id == UserRole.user_id)
            .filter(UserRole.role_id == role_id)
            .order_by(User.first_name, User.last_name)
            .all()
        )

    @staticmethod
    def get_role_activity(role_id, limit=20):
        role = Role.query.get(role_id)
        if not role:
            return []

        return (
            AuditLog.query
            .filter(
                AuditLog.resource == "Role",
                AuditLog.resource_id == role.public_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
