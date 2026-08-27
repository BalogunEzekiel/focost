from functools import wraps

from flask import abort

from flask_login import current_user
from flask_login import login_required


def admin_required(func):

    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):

        if not current_user.is_authenticated:
            abort(401)

        if not current_user.is_admin:
            abort(403)

        return func(*args, **kwargs)

    return wrapper