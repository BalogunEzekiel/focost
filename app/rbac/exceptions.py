class RBACError(Exception):
    """
    Base class for all RBAC-related exceptions.
    """

    default_message = "RBAC error."

    def __init__(self, message=None):

        super().__init__(
            message or self.default_message
        )


# ==========================================================
# Authentication
# ==========================================================

class AuthenticationRequired(RBACError):
    """
    Raised when an anonymous user attempts
    to access a protected resource.
    """

    default_message = "Authentication required."


# ==========================================================
# Authorization
# ==========================================================

class AuthorizationError(RBACError):
    """
    Base authorization exception.
    """

    default_message = "Access denied."


class PermissionDenied(AuthorizationError):
    """
    Raised when the user lacks a required permission.
    """

    def __init__(self, permission=None):

        self.permission = permission

        message = (
            f"Missing permission: {permission}"
            if permission
            else "Permission denied."
        )

        super().__init__(message)


class RoleDenied(AuthorizationError):
    """
    Raised when the user lacks a required role.
    """

    def __init__(self, role=None):

        self.role = role

        message = (
            f"Missing role: {role}"
            if role
            else "Role denied."
        )

        super().__init__(message)