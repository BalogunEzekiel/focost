from flask import request
from flask import abort

from app.rbac.service import RBACService


class RBACMiddleware:
    """
    Global authentication middleware.

    Ensures every request under /admin
    is made by an authenticated user.

    Authorization is handled by the
    @permission_required decorators.
    """

    ADMIN_PREFIX = "/admin"

    @classmethod
    def init_app(cls, app):

        @app.before_request
        def protect_admin():

            # ------------------------------------------
            # Protect only /admin routes
            # ------------------------------------------

            if not request.path.startswith(
                cls.ADMIN_PREFIX
            ):
                return

            # ------------------------------------------
            # User must be authenticated
            # ------------------------------------------

            if not RBACService.is_authenticated():

                abort(401)