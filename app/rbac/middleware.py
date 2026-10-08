from flask import request, abort
from app.rbac.service import RBACService


class RBACMiddleware:
    """
    Global RBAC boundary for the administrative URL surface.

    Authentication is required first; membership in the admin role group
    is required before route-level permissions are evaluated.
    """

    ADMIN_PREFIX = "/admin"

    @classmethod
    def init_app(cls, app):

        @app.before_request
        def protect_admin():

            if not request.path.startswith(cls.ADMIN_PREFIX):
                return

            if not RBACService.is_authenticated():
                abort(401)

            if not RBACService.is_admin_group():
                abort(403)
