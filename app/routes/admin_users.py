from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required

from app.rbac.decorators import permission_required

from app.audit.service import AuditService
from app.audit.constants import (
    USER_CREATED,
    USER_UPDATED,
    USER_DELETED,
    USER,
    ROLE_ASSIGNED,
    ROLE_REMOVED,
    RBAC
)

#from app.routes.admin import roles
from app.services.admin_user_service import AdminUserService
from app.models.role import Role

admin_users_bp = Blueprint(
    "admin_users",
    __name__,
    url_prefix="/admin/users"
)


# ==========================================================
# User List
# ==========================================================

@admin_users_bp.route("/")
@login_required
@permission_required("users.view")
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

    users = AdminUserService.list_users(
        page=page,
        search=search
    )

    statistics = AdminUserService.user_statistics()

    return render_template(
        "admin/users/index.html",
        users=users,
        statistics=statistics,
        search=search
    )

# ==========================================================
# User Details
# ==========================================================

@admin_users_bp.route("/<public_id>")
@login_required
@permission_required("users.view")
def details(public_id):

    user = AdminUserService.get_user(
        public_id
    )

    if not user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("admin_users.index")
        )

    roles = (
        Role.query
        .filter_by(is_active=True)
        .order_by(Role.name)
        .all()
    )

    return render_template(
        "admin/users/details.html",
        user=user,
        roles=roles
    )


# ==========================================================
# Create User
# ==========================================================

@admin_users_bp.route(
    "/create",
    methods=["GET", "POST"]
)
@login_required
@permission_required("users.create")
def create():

    if request.method == "POST":

        try:

            user = AdminUserService.create_user(

                first_name=request.form.get("first_name"),

                last_name=request.form.get("last_name"),

                email=request.form.get("email"),

                password=request.form.get("password"),

                role_slug=request.form.get("role")
            )

            AuditService.log(

                action=USER_CREATED,

                category=USER,

                resource="User",

                resource_id=user.public_id,

                description=f"Created {user.email}"
            )

            flash(
                "User created successfully.",
                "success"
            )

            return redirect(
                url_for("admin_users.index")
            )

        except Exception as ex:

            flash(
                str(ex),
                "danger"
            )

    roles = Role.query.order_by(Role.name).all()
    return render_template(
        "admin/users/create.html",
        roles=roles
    )

# ==========================================================
# Edit User
# ==========================================================

@admin_users_bp.route(
    "/<public_id>/edit",
    methods=["GET", "POST"]
)
@login_required
@permission_required("users.update")
def edit(public_id):

    user = AdminUserService.get_user(
        public_id
    )

    if not user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("admin_users.index")
        )

    if request.method == "POST":

        try:

            AdminUserService.update_user(

                public_id,

                first_name=request.form.get("first_name"),

                last_name=request.form.get("last_name"),

                email=request.form.get("email"),

                password=request.form.get("password")
            )

            AuditService.log(

                action=USER_UPDATED,

                category=USER,

                resource="User",

                resource_id=user.public_id,

                description=f"Updated {user.email}"
            )

            flash(
                "User updated.",
                "success"
            )

            return redirect(
                url_for("admin_users.details",
                public_id=public_id)
            )

        except Exception as ex:

            flash(
                str(ex),
                "danger"
            )

    return render_template(
        "admin/users/edit.html",
        user=user
    )


# ==========================================================
# Activate User
# ==========================================================

@admin_users_bp.route(
    "/<public_id>/activate"
)
@login_required
@permission_required("users.update")
def activate(public_id):

    user = AdminUserService.activate_user(
        public_id
    )

    if user:

        AuditService.log(

            action=USER_UPDATED,

            category=USER,

            resource="User",

            resource_id=user.public_id,

            description="Activated account"
        )

        flash(
            "User activated.",
            "success"
        )

    return redirect(
        url_for("admin_users.index")
    )


# ==========================================================
# Deactivate User
# ==========================================================

@admin_users_bp.route(
    "/<public_id>/deactivate"
)
@login_required
@permission_required("users.update")
def deactivate(public_id):

    user = AdminUserService.deactivate_user(
        public_id
    )

    if user:

        AuditService.log(

            action=USER_UPDATED,

            category=USER,

            resource="User",

            resource_id=user.public_id,

            description="Deactivated account"
        )

        flash(
            "User deactivated.",
            "warning"
        )

    return redirect(
        url_for("admin_users.index")
    )


# ==========================================================
# Delete User
# ==========================================================

@admin_users_bp.route(
    "/<public_id>/delete"
)
@login_required
@permission_required("users.delete")
def delete(public_id):

    user = AdminUserService.get_user(
        public_id
    )

    if user:

        AuditService.log(

            action=USER_DELETED,

            category=USER,

            resource="User",

            resource_id=user.public_id,

            description=f"Deleted {user.email}"
        )

        AdminUserService.delete_user(
            public_id
        )

        flash(
            "User deleted.",
            "success"
        )

    return redirect(
        url_for("admin_users.index")
    )


# ==========================================================
# Assign / Change Role
# ==========================================================

@admin_users_bp.route(
    "/<public_id>/assign-role",
    methods=["POST"]
)
@login_required
@permission_required("roles.assign")
def assign_role(public_id):

    user = AdminUserService.get_user(
        public_id
    )

    if not user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("admin_users.index")
        )

    role_slug = request.form.get(
        "role"
    )

    if not role_slug:

        flash(
            "Please select a role.",
            "warning"
        )

        return redirect(
            url_for(
                "admin_users.details",
                public_id=public_id
            )
        )

    try:

        AdminUserService.change_role(
            user,
            role_slug
        )

        AuditService.log(

            action=ROLE_ASSIGNED,

            category=RBAC,

            resource="Role",

            resource_id=role_slug,

            description=f"{role_slug} assigned to {user.email}"
        )

        flash(
            "User role changed successfully.",
            "success"
        )

    except Exception as ex:

        flash(
            str(ex),
            "danger"
        )

    return redirect(
        url_for(
            "admin_users.details",
            public_id=public_id
        )
    )

# ==========================================================
# Remove Role
# ==========================================================

@admin_users_bp.route(
    "/<public_id>/remove-role",
    methods=["POST"]
)
@login_required
@permission_required("roles.remove")
def remove_role(public_id):

    user = AdminUserService.get_user(
        public_id
    )

    role_slug = request.form.get(
        "role"
    )

    AdminUserService.remove_role(
        user,
        role_slug
    )

    AuditService.log(

        action=ROLE_REMOVED,

        category=RBAC,

        resource="Role",

        resource_id=role_slug,

        description=f"{role_slug} removed from {user.email}"
    )

    flash(
        "Role removed.",
        "success"
    )

    return redirect(
        url_for(
            "admin_users.details",
            public_id=public_id
        )
    )