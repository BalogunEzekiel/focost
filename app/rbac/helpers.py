from app.rbac.service import RBACService


# ==========================================================
# Authentication
# ==========================================================

def is_authenticated():
    """
    Returns True if the current user
    is authenticated.
    """

    return RBACService.is_authenticated()


# ==========================================================
# Roles
# ==========================================================

def has_role(role):
    """
    Checks whether the current user
    has the specified role.
    """

    return RBACService.has_role(role)


def has_any_role(*roles):
    """
    Returns True if the current user
    has at least one of the supplied roles.
    """

    return RBACService.has_any_role(
        *roles
    )

# ==========================================================
# Permissions
# ==========================================================

def has_permission(permission):
    """
    Checks whether the current user
    has the specified permission.
    """

    return RBACService.has_permission(
        permission
    )


def has_any_permission(*permissions):
    """
    Returns True if the current user
    has at least one supplied permission.
    """

    return RBACService.has_any_permission(
        *permissions
    )


def has_all_permissions(*permissions):
    """
    Returns True if the current user
    has every supplied permission.
    """

    return RBACService.has_all_permissions(
        *permissions
    )


# ==========================================================
# Admin
# ==========================================================

def is_admin():
    """
    Returns True if the current user
    belongs to an administrative role.
    """

    return RBACService.is_admin()