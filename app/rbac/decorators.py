from functools import wraps
from flask import abort
from flask_login import login_required
from app.rbac.service import RBACService


# ==========================================================
# Role Required
# ==========================================================

def role_required(*roles):

    def decorator(view):

        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):

            if not RBACService.has_any_role(*roles):
                abort(403)

            return view(*args, **kwargs)

        return wrapper

    return decorator


# ==========================================================
# Permission Required
# ==========================================================

def permission_required(*permissions):

    def decorator(view):

        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):

            if not RBACService.has_all_permissions(*permissions):
                abort(403)

            return view(*args, **kwargs)

        return wrapper

    return decorator


# ==========================================================
# Admin Required
# ==========================================================

def admin_required(view):

    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):

        if not RBACService.is_admin():
            abort(403)

        return view(*args, **kwargs)

    return wrapper


# ==========================================================
# Super Admin Required
# ==========================================================

def super_admin_required(view):

    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):

        if not RBACService.is_super_admin():
            abort(403)

        return view(*args, **kwargs)

    return wrapper