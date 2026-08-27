"""
FOCOST RBAC Constants

This file contains the default system roles and permissions.

Every part of the application should import from here instead
of hardcoding role names or permission codes.
"""

# ==========================================================
# SYSTEM ROLES
# ==========================================================

SYSTEM_ROLES = [

    {
        "slug": "super_admin",
        "name": "Super Administrator",
        "description": "Full unrestricted access",
        "is_system": True
    },

    {
        "slug": "admin",
        "name": "Administrator",
        "description": "Administrative access",
        "is_system": True
    },

    {
        "slug": "user",
        "name": "User",
        "description": "Regular application user",
        "is_system": True
    }

]


# ==========================================================
# SYSTEM PERMISSIONS
# ==========================================================

SYSTEM_PERMISSIONS = [

    # ======================================================
    # Dashboard
    # ======================================================

    {
        "code": "dashboard.view",
        "module": "Dashboard",
        "action": "view",
        "name": "View Dashboard"
    },

    # ======================================================
    # Users
    # ======================================================

    {
        "code": "users.view",
        "module": "Users",
        "action": "view",
        "name": "View Users"
    },

    {
        "code": "users.create",
        "module": "Users",
        "action": "create",
        "name": "Create Users"
    },

    {
        "code": "users.edit",
        "module": "Users",
        "action": "edit",
        "name": "Edit Users"
    },

    {
        "code": "users.delete",
        "module": "Users",
        "action": "delete",
        "name": "Delete Users"
    },

    # ======================================================
    # Roles
    # ======================================================

    {
        "code": "roles.view",
        "module": "Roles",
        "action": "view",
        "name": "View Roles"
    },

    {
        "code": "roles.create",
        "module": "Roles",
        "action": "create",
        "name": "Create Roles"
    },

    {
        "code": "roles.edit",
        "module": "Roles",
        "action": "edit",
        "name": "Edit Roles"
    },

    {
        "code": "roles.delete",
        "module": "Roles",
        "action": "delete",
        "name": "Delete Roles"
    },

    # ======================================================
    # Permissions
    # ======================================================

    {
        "code": "permissions.view",
        "module": "Permissions",
        "action": "view",
        "name": "View Permissions"
    },

    {
        "code": "permissions.create",
        "module": "Permissions",
        "action": "create",
        "name": "Create Permissions"
    },

    {
        "code": "permissions.edit",
        "module": "Permissions",
        "action": "edit",
        "name": "Edit Permissions"
    },

    {
        "code": "permissions.delete",
        "module": "Permissions",
        "action": "delete",
        "name": "Delete Permissions"
    },

    # ======================================================
    # Audit
    # ======================================================

    {
        "code": "audit.view",
        "module": "Audit",
        "action": "view",
        "name": "View Audit Logs"
    },

    # ======================================================
    # Subscriptions
    # ======================================================

    {
        "code": "subscriptions.view",
        "module": "Subscriptions",
        "action": "view",
        "name": "View Subscriptions"
    },

    {
        "code": "subscriptions.edit",
        "module": "Subscriptions",
        "action": "edit",
        "name": "Edit Subscriptions"
    },

    # ======================================================
    # AI
    # ======================================================

    {
        "code": "ai.view",
        "module": "AI",
        "action": "view",
        "name": "View AI"
    },

    {
        "code": "ai.configure",
        "module": "AI",
        "action": "configure",
        "name": "Configure AI"
    },

    # ======================================================
    # Settings
    # ======================================================

    {
        "code": "settings.view",
        "module": "Settings",
        "action": "view",
        "name": "View Settings"
    },

    {
        "code": "settings.edit",
        "module": "Settings",
        "action": "edit",
        "name": "Edit Settings"
    }

]