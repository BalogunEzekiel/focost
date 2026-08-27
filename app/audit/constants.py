"""
Audit Categories
"""

AUTH = "authentication"
SECURITY = "security"
RBAC = "rbac"
USER = "user"
ADMIN = "admin"
AI = "ai"
PAYMENT = "payment"
SYSTEM = "system"


"""
Authentication Events
"""

AUTH_LOGIN = "auth.login"
AUTH_LOGOUT = "auth.logout"
AUTH_LOGIN_FAILED = "auth.login_failed"
AUTH_PASSWORD_RESET = "auth.password_reset"
AUTH_PASSWORD_CHANGED = "auth.password_changed"
AUTH_EMAIL_VERIFIED = "auth.email_verified"


"""
User Events
"""

USER_CREATED = "user.created"
USER_UPDATED = "user.updated"
USER_DELETED = "user.deleted"
USER_SUSPENDED = "user.suspended"
USER_RESTORED = "user.restored"


"""
RBAC Events
"""

ROLE_CREATED = "rbac.role_created"
ROLE_UPDATED = "rbac.role_updated"
ROLE_DELETED = "rbac.role_deleted"
ROLE_CLONED = "rbac.role.cloned"

ROLE_ASSIGNED = "rbac.role_assigned"
ROLE_REMOVED = "rbac.role_removed"

PERMISSION_GRANTED = "rbac.permission_granted"
PERMISSION_REVOKED = "rbac.permission_revoked"


"""
Admin Events
"""

ADMIN_LOGIN = "admin.login"
ADMIN_SETTINGS_UPDATED = "admin.settings_updated"


"""
AI Events
"""

AI_CONFIGURATION_CHANGED = "ai.configuration_changed"
AI_MODEL_CHANGED = "ai.model_changed"


"""
Payment Events
"""

PAYMENT_CREATED = "payment.created"
PAYMENT_UPDATED = "payment.updated"
PAYMENT_REFUNDED = "payment.refunded"


"""
System Events
"""

SYSTEM_ERROR = "system.error"
SYSTEM_BACKUP = "system.backup"
SYSTEM_RESTORE = "system.restore"

# Categories
ADMIN = "admin"

# Actions
ADMIN_DASHBOARD_VIEW = "admin.dashboard.view"
USERS_VIEW = "users.view"
ROLES_VIEW = "roles.view"
PERMISSIONS_VIEW = "permissions.view"
AUDIT_VIEW = "audit.view"
AI_SETTINGS_VIEW = "ai.settings.view"
SYSTEM_SETTINGS_VIEW = "system.settings.view"
SUBSCRIPTIONS_VIEW = "subscriptions.view"