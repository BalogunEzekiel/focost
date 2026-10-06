from app.extensions import db
from app.models.permission import Permission


def sync_route_permissions(app):
    """Synchronize permission records from permission-decorated routes.

    This removes the need to maintain a second manual permission inventory
    whenever a future module exposes a route through the standard RBAC
    decorator. Existing named permissions retain their human-friendly metadata.
    """
    existing = {p.code: p for p in Permission.query.all()}
    created = 0

    for endpoint, view in app.view_functions.items():
        codes = getattr(view, "_rbac_permissions", ())
        for code in codes:
            if code in existing:
                continue
            module = endpoint.split(".", 1)[0].replace("_", " ").title()
            action = code.rsplit(".", 1)[-1]
            permission = Permission(
                code=code,
                module=module,
                action=action,
                name=f"{action.replace('_', ' ').title()} {module}",
                description=f"Automatically registered from route {endpoint}.",
            )
            db.session.add(permission)
            existing[code] = permission
            created += 1

    if created:
        db.session.commit()

    return created
