from app.rbac.service import RBACService


def has_permission(permission):
    return RBACService.has_permission(permission)


def has_any_permission(*permissions):
    return RBACService.has_any_permission(*permissions)


def has_role(role):
    return RBACService.has_role(role)