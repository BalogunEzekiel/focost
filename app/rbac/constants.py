"""
FOCOST RBAC Constants

This module contains the canonical system roles and permissions
used throughout the FOCOST application.

Design principles:
    - SYSTEM_ROLES is the canonical system-role registry.
    - SYSTEM_PERMISSIONS is the canonical permission registry.
    - Permission codes must not be hardcoded elsewhere when a
      constant can be imported from this module.
    - RBAC seeding synchronizes SYSTEM_PERMISSIONS with the database.
    - Super Admin receives all registered permissions.
    - DEFAULT_USER_PERMISSION_CODES defines the permissions granted
      to the standard User role.
    - Each user may have only one role.
"""


# ==========================================================
# SYSTEM ROLES
# ==========================================================

SYSTEM_ROLES = [
    {
        "slug": "super_admin",
        "name": "Super Administrator",
        "description": "Full unrestricted administrative access.",
        "is_system": True,
    },
    {
        "slug": "admin",
        "name": "Administrator",
        "description": "Administrative access to assigned system functions.",
        "is_system": True,
    },
    {
        "slug": "user",
        "name": "User",
        "description": "Regular FOCOST application user.",
        "is_system": True,
    },
]


# ==========================================================
# SYSTEM PERMISSIONS
# ==========================================================
#
# This is the SINGLE CANONICAL PERMISSION REGISTRY.
#
# Every permission supported by the application should be
# declared here.
#
# RBACSeed.seed_permissions() synchronizes this registry with
# the Permission table.
#
# Super Admin receives all permissions registered here.
# ==========================================================

SYSTEM_PERMISSIONS = [

    # ======================================================
    # DASHBOARD
    # ======================================================

    {
        "code": "dashboard.view",
        "module": "Dashboard",
        "action": "view",
        "name": "View Dashboard",
    },


    # ======================================================
    # ADMINISTRATION
    # ======================================================

    {
        "code": "admin.dashboard.view",
        "module": "Administration",
        "action": "view",
        "name": "View Admin Dashboard",
    },


    # ======================================================
    # USERS
    # ======================================================

    {
        "code": "users.view",
        "module": "Users",
        "action": "view",
        "name": "View Users",
    },
    {
        "code": "users.create",
        "module": "Users",
        "action": "create",
        "name": "Create Users",
    },
    {
        "code": "users.edit",
        "module": "Users",
        "action": "edit",
        "name": "Edit Users",
    },
    {
        "code": "users.update",
        "module": "Users",
        "action": "update",
        "name": "Update Users",
    },
    {
        "code": "users.delete",
        "module": "Users",
        "action": "delete",
        "name": "Delete Users",
    },


    # ======================================================
    # ROLES
    # ======================================================

    {
        "code": "roles.view",
        "module": "Roles",
        "action": "view",
        "name": "View Roles",
    },
    {
        "code": "roles.create",
        "module": "Roles",
        "action": "create",
        "name": "Create Roles",
    },
    {
        "code": "roles.edit",
        "module": "Roles",
        "action": "edit",
        "name": "Edit Roles",
    },
    {
        "code": "roles.update",
        "module": "Roles",
        "action": "update",
        "name": "Update Roles",
    },
    {
        "code": "roles.delete",
        "module": "Roles",
        "action": "delete",
        "name": "Delete Roles",
    },
    {
        "code": "roles.assign",
        "module": "Roles",
        "action": "assign",
        "name": "Assign Roles",
    },
    {
        "code": "roles.remove",
        "module": "Roles",
        "action": "remove",
        "name": "Remove Roles",
    },
    {
        "code": "roles.export",
        "module": "Roles",
        "action": "export",
        "name": "Export Roles",
    },


    # ======================================================
    # PERMISSIONS
    # ======================================================

    {
        "code": "permissions.view",
        "module": "Permissions",
        "action": "view",
        "name": "View Permissions",
    },
    {
        "code": "permissions.create",
        "module": "Permissions",
        "action": "create",
        "name": "Create Permissions",
    },
    {
        "code": "permissions.edit",
        "module": "Permissions",
        "action": "edit",
        "name": "Edit Permissions",
    },
    {
        "code": "permissions.delete",
        "module": "Permissions",
        "action": "delete",
        "name": "Delete Permissions",
    },
    {
        "code": "permissions.assign",
        "module": "Permissions",
        "action": "assign",
        "name": "Assign Permissions",
    },


    # ======================================================
    # AUDIT
    # ======================================================

    {
        "code": "audit.view",
        "module": "Audit",
        "action": "view",
        "name": "View Audit Logs",
    },


    # ======================================================
    # SUBSCRIPTIONS
    # ======================================================

    {
        "code": "subscriptions.view",
        "module": "Subscriptions",
        "action": "view",
        "name": "View Subscriptions",
    },
    {
        "code": "subscriptions.edit",
        "module": "Subscriptions",
        "action": "edit",
        "name": "Edit Subscriptions",
    },


    # ======================================================
    # AI
    # ======================================================

    {
        "code": "ai.view",
        "module": "AI",
        "action": "view",
        "name": "View AI",
    },
    {
        "code": "ai.configure",
        "module": "AI",
        "action": "configure",
        "name": "Configure AI",
    },
    {
        "code": "ai.use",
        "module": "AI",
        "action": "use",
        "name": "Use AI",
    },
    {
        "code": "ai.chat",
        "module": "AI",
        "action": "chat",
        "name": "Use FOCOST AI",
    },


    # ======================================================
    # ANALYTICS
    # ======================================================

    {
        "code": "analytics.view",
        "module": "Analytics",
        "action": "view",
        "name": "View Analytics Center",
    },


    # ======================================================
    # COMMUNICATIONS
    # ======================================================

    {
        "code": "communications.view",
        "module": "Communications",
        "action": "view",
        "name": "View Communications",
    },
    {
        "code": "communications.manage",
        "module": "Communications",
        "action": "manage",
        "name": "Manage Communications",
    },


    # ======================================================
    # NOTIFICATIONS
    # ======================================================

    {
        "code": "notifications.view",
        "module": "Notifications",
        "action": "view",
        "name": "View Notifications",
    },
    {
        "code": "notifications.manage",
        "module": "Notifications",
        "action": "manage",
        "name": "Manage Notifications",
    },


    # ======================================================
    # DOCUMENTS
    # ======================================================

    {
        "code": "documents.view",
        "module": "Documents",
        "action": "view",
        "name": "View Document Archive",
    },
    {
        "code": "documents.manage",
        "module": "Documents",
        "action": "manage",
        "name": "Manage Document Archive",
    },
    {
        "code": "documents.download",
        "module": "Documents",
        "action": "download",
        "name": "Download Documents",
    },


    # ======================================================
    # FEEDBACK
    # ======================================================

    {
        "code": "feedback.view",
        "module": "Feedback",
        "action": "view",
        "name": "View Feedback",
        "description": (
            "View submitted public feedback in the "
            "administration area."
        ),
    },
    {
        "code": "feedback.manage",
        "module": "Feedback",
        "action": "manage",
        "name": "Manage Feedback",
        "description": (
            "Review, classify and update submitted feedback."
        ),
    },
    {
        "code": "feedback.export",
        "module": "Feedback",
        "action": "export",
        "name": "Export Feedback",
    },


    # ======================================================
    # COMPLIANCE
    # ======================================================

    {
        "code": "compliance.view",
        "module": "Compliance",
        "action": "view",
        "name": "View Compliance Evidence",
    },


    # ======================================================
    # SETTINGS
    # ======================================================

    {
        "code": "settings.view",
        "module": "Settings",
        "action": "view",
        "name": "View Settings",
    },
    {
        "code": "settings.edit",
        "module": "Settings",
        "action": "edit",
        "name": "Edit Settings",
    },
    {
        "code": "settings.view_profile",
        "module": "Profile Settings",
        "action": "view",
        "name": "View Profile Settings",
    },


    # ======================================================
    # PROFILE
    # ======================================================

    {
        "code": "profile.view",
        "module": "Profile",
        "action": "view",
        "name": "View Profile",
    },
    {
        "code": "profile.edit",
        "module": "Profile",
        "action": "edit",
        "name": "Edit Profile",
    },


    # ======================================================
    # INVESTMENTS
    # ======================================================

    {
        "code": "investments.view",
        "module": "Investments",
        "action": "view",
        "name": "View Investments",
    },
    {
        "code": "investments.manage",
        "module": "Investments",
        "action": "manage",
        "name": "Manage Investments",
    },


    # ======================================================
    # CATEGORIES
    # ======================================================

    {
        "code": "categories.view",
        "module": "Categories",
        "action": "view",
        "name": "View Category Registry",
    },
    {
        "code": "categories.manage",
        "module": "Categories",
        "action": "manage",
        "name": "Manage Category Registry",
    },


    # ======================================================
    # INCOME
    # ======================================================

    {
        "code": "income.view",
        "module": "Income",
        "action": "view",
        "name": "View Income",
    },
    {
        "code": "income.create",
        "module": "Income",
        "action": "create",
        "name": "Create Income",
    },
    {
        "code": "income.edit",
        "module": "Income",
        "action": "edit",
        "name": "Edit Income",
    },
    {
        "code": "income.delete",
        "module": "Income",
        "action": "delete",
        "name": "Delete Income",
    },


    # ======================================================
    # EXPENSES
    # ======================================================

    {
        "code": "expenses.view",
        "module": "Expenses",
        "action": "view",
        "name": "View Expenses",
    },
    {
        "code": "expenses.create",
        "module": "Expenses",
        "action": "create",
        "name": "Create Expenses",
    },
    {
        "code": "expenses.edit",
        "module": "Expenses",
        "action": "edit",
        "name": "Edit Expenses",
    },
    {
        "code": "expenses.delete",
        "module": "Expenses",
        "action": "delete",
        "name": "Delete Expenses",
    },


    # ======================================================
    # BUDGETS
    # ======================================================

    {
        "code": "budgets.view",
        "module": "Budgets",
        "action": "view",
        "name": "View Budgets",
    },
    {
        "code": "budgets.create",
        "module": "Budgets",
        "action": "create",
        "name": "Create Budgets",
    },
    {
        "code": "budgets.edit",
        "module": "Budgets",
        "action": "edit",
        "name": "Edit Budgets",
    },
    {
        "code": "budgets.delete",
        "module": "Budgets",
        "action": "delete",
        "name": "Delete Budgets",
    },


    # ======================================================
    # GOALS
    # ======================================================

    {
        "code": "goals.view",
        "module": "Goals",
        "action": "view",
        "name": "View Goals",
    },
    {
        "code": "goals.create",
        "module": "Goals",
        "action": "create",
        "name": "Create Goals",
    },
    {
        "code": "goals.edit",
        "module": "Goals",
        "action": "edit",
        "name": "Edit Goals",
    },
    {
        "code": "goals.delete",
        "module": "Goals",
        "action": "delete",
        "name": "Delete Goals",
    },


    # ======================================================
    # REPORTS
    # ======================================================

    {
        "code": "reports.view",
        "module": "Reports",
        "action": "view",
        "name": "View Reports",
    },
    {
        "code": "reports.export",
        "module": "Reports",
        "action": "export",
        "name": "Export Reports",
    },
]


# ==========================================================
# DEFAULT USER PERMISSIONS
# ==========================================================
#
# Permissions granted to the standard "user" role.
#
# This is intentionally separate from SYSTEM_PERMISSIONS:
#
# SYSTEM_PERMISSIONS
#     = everything the FOCOST RBAC system recognizes.
#
# DEFAULT_USER_PERMISSION_CODES
#     = the subset available to normal application users.
#
# Super Admin is NOT restricted by this list.
# ==========================================================

DEFAULT_USER_PERMISSION_CODES = {
    # Dashboard
    "dashboard.view",

    # Personal financial records
    "income.view",
    "income.create",
    "income.edit",
    "income.delete",

    "expenses.view",
    "expenses.create",
    "expenses.edit",
    "expenses.delete",

    # Planning
    "budgets.view",
    "budgets.create",
    "budgets.edit",
    "budgets.delete",

    "goals.view",
    "goals.create",
    "goals.edit",
    "goals.delete",

    # Reports
    "reports.view",

    # Investments
    "investments.view",

    # AI
    "ai.chat",

    # Profile
    "profile.view",
    "profile.edit",

    # Notifications
    "notifications.view",

    # Profile settings
    "settings.view_profile",
}


# ==========================================================
# RBAC INTEGRITY VALIDATION
# ==========================================================
#
# These checks run when this module is imported.
#
# They protect against accidental duplicate permission codes
# being introduced into SYSTEM_PERMISSIONS.
# ==========================================================

_PERMISSION_CODES = [
    permission["code"]
    for permission in SYSTEM_PERMISSIONS
]

if len(_PERMISSION_CODES) != len(set(_PERMISSION_CODES)):
    duplicate_codes = sorted(
        {
            code
            for code in _PERMISSION_CODES
            if _PERMISSION_CODES.count(code) > 1
        }
    )

    raise RuntimeError(
        "Duplicate RBAC permission codes detected: "
        + ", ".join(duplicate_codes)
    )


_SYSTEM_PERMISSION_CODES = set(_PERMISSION_CODES)

_unknown_default_permissions = (
    set(DEFAULT_USER_PERMISSION_CODES)
    - _SYSTEM_PERMISSION_CODES
)

if _unknown_default_permissions:
    raise RuntimeError(
        "Default User permissions are not registered in "
        "SYSTEM_PERMISSIONS: "
        + ", ".join(sorted(_unknown_default_permissions))
    )
