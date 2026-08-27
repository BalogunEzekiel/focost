from app import create_app
from app.extensions import db

from app.models import (
    User,
    Role,
    Permission,
    RolePermission,
    UserRole
)

app = create_app()


PERMISSIONS = {

    "Dashboard": [
        "view"
    ],

    "Users": [
        "view",
        "create",
        "edit",
        "delete"
    ],

    "Roles": [
        "view",
        "create",
        "edit",
        "delete"
    ],

    "Permissions": [
        "view",
        "create",
        "edit",
        "delete"
    ],

    "Income": [
        "view",
        "create",
        "edit",
        "delete"
    ],

    "Expenses": [
        "view",
        "create",
        "edit",
        "delete"
    ],

    "Budgets": [
        "view",
        "create",
        "edit",
        "delete"
    ],

    "Goals": [
        "view",
        "create",
        "edit",
        "delete"
    ],

    "Reports": [
        "view",
        "export"
    ],

    "AI": [
        "use"
    ],

    "Settings": [
        "view",
        "edit"
    ]

}


ROLES = [

    {
        "slug": "super_admin",
        "name": "Super Administrator",
        "description": "Full system access",
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
        "description": "Normal user",
        "is_system": True
    }

]


SUPER_ADMIN = {

    "first_name": "Super",
    "last_name": "Administrator",
    "email": "admin@focost.com",
    "password": "admiN@321"

}


with app.app_context():

    print("\nSeeding database...\n")

    # ---------------------------------------------------
    # PERMISSIONS
    # ---------------------------------------------------

    for module, actions in PERMISSIONS.items():

        for action in actions:

            code = f"{module.lower()}.{action}"

            permission = Permission.query.filter_by(
                code=code
            ).first()

            if permission is None:

                permission = Permission(

                    code=code,

                    module=module,

                    action=action,

                    name=f"{action.title()} {module}"

                )

                db.session.add(permission)

    db.session.commit()

    print("✓ Permissions seeded")

    # ---------------------------------------------------
    # ROLES
    # ---------------------------------------------------

    for role_data in ROLES:

        role = Role.query.filter_by(
            slug=role_data["slug"]
        ).first()

        if role is None:

            role = Role(**role_data)

            db.session.add(role)

    db.session.commit()

    print("✓ Roles seeded")

    # ---------------------------------------------------
    # SUPER ADMIN GETS ALL PERMISSIONS
    # ---------------------------------------------------

    super_admin_role = Role.query.filter_by(
        slug="super_admin"
    ).first()

    permissions = Permission.query.all()

    for permission in permissions:

        exists = RolePermission.query.filter_by(

            role_id=super_admin_role.id,

            permission_id=permission.id

        ).first()

        if exists is None:

            db.session.add(

                RolePermission(

                    role=super_admin_role,

                    permission=permission

                )

            )

    db.session.commit()

    print("✓ Super Admin permissions assigned")

    # ---------------------------------------------------
    # CREATE SUPER ADMIN USER
    # ---------------------------------------------------

    admin = User.query.filter_by(

        email=SUPER_ADMIN["email"]

    ).first()

    if admin is None:

        admin = User(

            first_name=SUPER_ADMIN["first_name"],

            last_name=SUPER_ADMIN["last_name"],

            email=SUPER_ADMIN["email"]

        )

        admin.set_password(

            SUPER_ADMIN["password"]

        )

        db.session.add(admin)

        db.session.commit()

        print("✓ Super Admin created")

    else:

        print("✓ Super Admin already exists")

    # ---------------------------------------------------
    # ASSIGN ROLE
    # ---------------------------------------------------

    assignment = UserRole.query.filter_by(

        user_id=admin.id,

        role_id=super_admin_role.id

    ).first()

    if assignment is None:

        db.session.add(

            UserRole(

                user=admin,

                role=super_admin_role

            )

        )

        db.session.commit()

    print("✓ Super Admin role assigned")

    print("\nDatabase seeded successfully.\n")