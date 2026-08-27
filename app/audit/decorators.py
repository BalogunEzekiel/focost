from functools import wraps

from app.audit.service import AuditService


def audit(action, category):

    def decorator(view):

        @wraps(view)
        def wrapper(*args, **kwargs):

            response = view(*args, **kwargs)

            AuditService.log(

                action=action,

                category=category
            )

            return response

        return wrapper

    return decorator