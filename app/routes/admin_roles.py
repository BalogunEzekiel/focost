from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort
)

from flask_login import (
    login_required,
    current_user
)
from app.services.admin_role_service import AdminRoleService
from app.rbac.decorators import permission_required
from app.audit.service import AuditService
from app.audit.constants import (
    ADMIN,
    RBAC,
    ROLE_CREATED,
    ROLE_UPDATED,
    ROLE_DELETED,
    ROLE_CLONED,
    ROLE_ASSIGNED,
    ROLE_REMOVED,
    PERMISSION_GRANTED,
)

from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.extensions import db
from app.models.user import User

admin_roles_bp = Blueprint(
    "admin_roles",
    __name__,
    url_prefix="/admin/roles"
)

# ============================================================
# Role List
# ============================================================

@admin_roles_bp.route("/")
@login_required
@permission_required("roles.view")
def index():

    page = request.args.get(
        "page",
        1,
        type=int
    )

    search = request.args.get(
        "search",
        ""
    )

    roles = AdminRoleService.list_roles(
        page=page,
        search=search
    )

    stats = AdminRoleService.get_statistics()

    return render_template(
        "admin/roles/index.html",
        roles=roles,
        stats=stats,
        search=search
    )


# ============================================================
# Role Details
# ============================================================

@admin_roles_bp.route("/<int:role_id>")
@login_required
@permission_required("roles.view")
def details(role_id):

    role = AdminRoleService.get_role(role_id)

    if not role:
        abort(404)

    permissions = AdminRoleService.get_role_permissions(role_id)

    grouped_permissions = AdminRoleService.get_grouped_permissions()

    assigned_permission_ids = (
        AdminRoleService.get_assigned_permission_ids(role_id)
    )

    users = AdminRoleService.get_role_users(role_id)

    activities = AdminRoleService.get_role_activity(role_id)

    return render_template(
        "admin/roles/details.html",
        role=role,
        permissions=permissions,
        grouped_permissions=grouped_permissions,
        assigned_permission_ids=assigned_permission_ids,
        users=users,
        activities=activities
    )

#    permissions = AdminRoleService.get_role_permissions(role_id)

#    users = AdminRoleService.get_role_users(role_id)

#    activities = AdminRoleService.get_role_activity(role_id)

#    return render_template(
#        "admin/roles/details.html",
#        role=role,
#        permissions=permissions,
#        users=users,
#        activities=activities
#    )

# ============================================================
# Create Role
# ============================================================

@admin_roles_bp.route(
    "/create",
    methods=["GET", "POST"]
)
@login_required
@permission_required("roles.create")
def create():

    if request.method == "POST":

        name = request.form.get("name")
        slug = request.form.get("slug")
        description = request.form.get("description")

        if AdminRoleService.slug_exists(slug):

            flash(
                "Role slug already exists.",
                "danger"
            )

            return redirect(request.url)

        role = AdminRoleService.create_role(
            name=name,
            slug=slug,
            description=description,
            is_system=request.form.get("is_system") == "on"
        )

        AuditService.log(
            action=ROLE_CREATED,
            category=RBAC,
            resource="Role",
            resource_id=role.public_id,
            description=f"Created role {role.name}"
        )

        flash(
            "Role created successfully.",
            "success"
        )

        return redirect(
            url_for(
                "admin_roles.index"
            )
        )

    return render_template(
        "admin/roles/create.html"
    )


# ============================================================
# Edit Role
# ============================================================

@admin_roles_bp.route(
    "/<int:role_id>/edit",
    methods=["GET", "POST"]
)
@login_required
@permission_required("roles.update")
def edit(role_id):

    role = AdminRoleService.get_role(
        role_id
    )

    if request.method == "POST":

        slug = request.form.get("slug")

        if AdminRoleService.slug_exists(
            slug,
            exclude_id=role_id
        ):

            flash(
                "Slug already exists.",
                "danger"
            )

            return redirect(request.url)

        AdminRoleService.update_role(
            role=role,
            name=request.form.get("name"),
            slug=slug,
            description=request.form.get("description"),
            is_system=request.form.get("is_system") == "on"
        )

        AuditService.log(
            action=ROLE_UPDATED,
            category=RBAC,
            resource="Role",
            resource_id=role.public_id,
            description=f"Updated role {role.name}"
        )

        flash(
            "Role updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "admin_roles.index"
            )
        )

    return render_template(
        "admin/roles/edit.html",
        role=role
    )


# ============================================================
# Delete Role
# ============================================================

@admin_roles_bp.route(
    "/<int:role_id>/delete",
    methods=["POST"]
)
@login_required
@permission_required("roles.delete")
def delete(role_id):

    role = AdminRoleService.get_role(
        role_id
    )

    if role.is_system:

        flash(
            "System roles cannot be deleted.",
            "warning"
        )

        return redirect(
            url_for(
                "admin_roles.index"
            )
        )

    AuditService.log(
        action=ROLE_DELETED,
        category=RBAC,
        resource="Role",
        resource_id=role.public_id,
        description=f"Deleted role {role.name}"
    )

    AdminRoleService.delete_role(role)

    flash(
        "Role deleted.",
        "success"
    )

    return redirect(
        url_for(
            "admin_roles.index"
        )
    )


# ============================================================
# Clone Role
# ============================================================

@admin_roles_bp.route(
    "/<int:role_id>/clone",
    methods=["POST"]
)
@login_required
@permission_required("roles.create")
def clone(role_id):

    role = Role.query.get_or_404(role_id)

    clone = Role(

        name=f"{role.name} Copy",

        slug=f"{role.slug}_copy",

        description=role.description,

        is_system=False
    )

    db.session.add(clone)

    db.session.flush()

    permissions = RolePermission.query.filter_by(
        role_id=role_id
    ).all()

    for rp in permissions:

        db.session.add(

            RolePermission(

                role_id=clone.id,

                permission_id=rp.permission_id

            )
        )

    db.session.commit()

    AuditService.log(

        action=ROLE_CLONED,

        category=RBAC,

        resource="Role",

        resource_id=clone.public_id,

        description=f"Cloned {role.name}"
    )

    flash(
        "Role cloned successfully.",
        "success"
    )

    return redirect(
        url_for(
            "admin_roles.edit",
            role_id=clone.id
        )
    )

# ============================================================
# Assign Permissions
# ============================================================

@admin_roles_bp.route(
    "/<int:role_id>/permissions",
    methods=["GET", "POST"]
)
@login_required
@permission_required("permissions.assign")
def permissions(role_id):

    role = Role.query.get_or_404(role_id)

    if request.method == "POST":

        RolePermission.query.filter_by(
            role_id=role_id
        ).delete()

        permission_ids = request.form.getlist(
            "permissions"
        )

        for permission_id in permission_ids:

            db.session.add(
                RolePermission(
                    role_id=role_id,
                    permission_id=int(permission_id)
                )
            )

        db.session.commit()

        AuditService.log(
            action=PERMISSION_GRANTED,
            category=RBAC,
            resource="Role",
            resource_id=role.public_id,
            description=f"Updated permissions for '{role.name}'"
        )

        flash(
            "Permissions updated successfully.",
            "success"
        )

        return redirect(request.url)

    # -------------------------------------------------------
    # Group permissions by module
    # -------------------------------------------------------

    grouped_permissions = {}

    permissions = (
        Permission.query
        .order_by(
            Permission.module,
            Permission.action
        )
        .all()
    )

    for permission in permissions:

        grouped_permissions.setdefault(
            permission.module,
            []
        ).append(permission)

    # -------------------------------------------------------
    # Assigned permissions
    # -------------------------------------------------------

    assigned_permission_ids = {

        rp.permission_id

        for rp in RolePermission.query.filter_by(
            role_id=role_id
        ).all()

    }

    return render_template(

        "admin/roles/permissions.html",

        role=role,

        grouped_permissions=grouped_permissions,

        assigned_permission_ids=assigned_permission_ids
    )

# ============================================================
# Export Roles
# ============================================================

@admin_roles_bp.route("/export")
@login_required
@permission_required("roles.export")
def export():

    abort(501)

# ============================================================
# Role Users
# ============================================================

@admin_roles_bp.route("/<int:role_id>/users")
@login_required
@permission_required("roles.view")
def role_users(role_id):

    role = Role.query.get_or_404(role_id)

    assigned_users = (
        User.query
        .join(UserRole)
        .filter(UserRole.role_id == role_id)
        .order_by(User.first_name, User.last_name)
        .all()
    )

    return render_template(
        "admin/roles/users.html",
        role=role,
        users=assigned_users
    )


# ============================================================
# Assign Users To Role
# ============================================================

@admin_roles_bp.route(
    "/<int:role_id>/assign-users",
    methods=["GET", "POST"]
)
@login_required
@permission_required("roles.assign")
def assign_users(role_id):

    role = Role.query.get_or_404(role_id)

    assigned_ids = {
        row.user_id
        for row in UserRole.query.filter_by(
            role_id=role_id
        ).all()
    }

    query = User.query

    if assigned_ids:
        query = query.filter(
            ~User.id.in_(assigned_ids)
        )

    available_users = (
        query
        .order_by(
            User.first_name,
            User.last_name
        )
        .all()
    )

    if request.method == "POST":

        user_ids = request.form.getlist("users")

        added = 0

        for user_id in user_ids:

            exists = UserRole.query.filter_by(
                user_id=int(user_id),
                role_id=role_id
            ).first()

            if exists:
                continue

            db.session.add(
                UserRole(
                    user_id=int(user_id),
                    role_id=role_id,
                    assigned_by_id=current_user.id
                )
            )

            added += 1

        db.session.commit()

        AuditService.log(
            action=ROLE_ASSIGNED,
            category=RBAC,
            resource="Role",
            resource_id=role.public_id,
            description=f"{added} user(s) assigned to role '{role.name}'"
        )

        flash(
            f"{added} user(s) assigned successfully.",
            "success"
        )

        return redirect(
            url_for(
                "admin_roles.role_users",
                role_id=role_id
            )
        )

    return render_template(
        "admin/roles/assign_users.html",
        role=role,
        users=available_users
    )


# ============================================================
# Remove User From Role
# ============================================================

@admin_roles_bp.route(
    "/<int:role_id>/remove-user/<int:user_id>",
    methods=["POST"]
)
@login_required
@permission_required("roles.assign")
def remove_user(role_id, user_id):

    role = Role.query.get_or_404(role_id)

    assignment = UserRole.query.filter_by(
        role_id=role_id,
        user_id=user_id
    ).first_or_404()

    user = db.session.get(User, user_id)

    db.session.delete(assignment)
    db.session.commit()

    AuditService.log(
        action=ROLE_REMOVED,
        category=RBAC,
        resource="Role",
        resource_id=role.public_id,
        description=f"{user.first_name} {user.last_name} removed from '{role.name}'"
    )

    flash(
        "User removed from role.",
        "success"
    )

    return redirect(
        url_for(
            "admin_roles.role_users",
            role_id=role_id
        )
    )