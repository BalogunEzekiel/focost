from app.extensions import db
from app.models.announcement import Announcement
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.rbac.service import RBACService
from app.services.announcement_service import AnnouncementService
from app.services.subscription_gate import SubscriptionGate
from app.subscriptions.service import SubscriptionService
from flask_login import login_user


def _make_user(app, email, role_slug):
    with app.app_context():
        user = User(
            first_name="Role",
            last_name="Test",
            email=email,
            email_verified=True,
        )
        user.set_password("StrongPassword123!")
        db.session.add(user)
        db.session.flush()

        role = Role.query.filter_by(slug=role_slug).first()
        assert role is not None

        db.session.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
            )
        )
        db.session.commit()
        return user.id


def test_custom_admin_role_is_an_admin_group(app):
    with app.app_context():
        role = Role(
            name="Developer",
            slug="developer_test",
            description="Test admin role",
            is_system=False,
            group_slug="admin",
        )
        db.session.add(role)
        db.session.commit()

        assert role.group_slug == "admin"


def test_admin_group_has_no_subscription_plan(app):
    user_id = _make_user(app, "admin-group@example.com", "admin")

    with app.app_context():
        assert SubscriptionService.current(user_id) is None
        assert SubscriptionGate.current_plan_slug(user_id) is None
        assert SubscriptionGate.ads_allowed(user_id) is False


def test_admin_group_cannot_use_end_user_ai_or_financial_permissions(app, client):
    with app.app_context():
        role = Role(
            name="Developer",
            slug="developer_group_test",
            description="Test admin role",
            is_system=False,
            group_slug="admin",
        )
        db.session.add(role)
        db.session.flush()

        user = User(
            first_name="Developer",
            last_name="Test",
            email="developer-group@example.com",
            email_verified=True,
        )
        user.set_password("StrongPassword123!")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role.id))
        db.session.commit()
        user_id = user.id

        from app.models.permission import Permission
        from app.models.role_permission import RolePermission

        for code in ("income.view", "ai.use", "ai.chat", "admin.dashboard.view"):
            permission = Permission.query.filter_by(code=code).first()
            if permission:
                db.session.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )
        db.session.commit()

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    with client.application.test_request_context():
        user = db.session.get(User, user_id)
        login_user(user)

        assert not RBACService.has_permission("income.view")
        assert not RBACService.has_permission("ai.use")
        assert not RBACService.has_permission("ai.chat")
        assert RBACService.has_permission("admin.dashboard.view")


def test_communications_audience_uses_role_group(app):
    super_admin_id = _make_user(app, "super-audience@example.com", "super_admin")
    admin_id = _make_user(app, "admin-audience@example.com", "admin")
    user_id = _make_user(app, "user-audience@example.com", "user")

    with app.app_context():
        all_item = Announcement(
            title="All",
            message="All accounts",
            audience="all",
        )
        super_item = Announcement(
            title="Super",
            message="Super Admin only",
            audience="super_admin",
        )
        admin_item = Announcement(
            title="Admin",
            message="Admin group only",
            audience="admin",
        )
        user_item = Announcement(
            title="User",
            message="Normal users only",
            audience="user",
        )

        db.session.add_all([
            all_item,
            super_item,
            admin_item,
            user_item,
        ])
        db.session.commit()

        assert AnnouncementService.can_receive(all_item, super_admin_id)
        assert AnnouncementService.can_receive(all_item, admin_id)
        assert AnnouncementService.can_receive(all_item, user_id)

        assert AnnouncementService.can_receive(super_item, super_admin_id)
        assert not AnnouncementService.can_receive(super_item, admin_id)

        assert AnnouncementService.can_receive(admin_item, admin_id)
        assert not AnnouncementService.can_receive(admin_item, super_admin_id)

        assert AnnouncementService.can_receive(user_item, user_id)
        assert not AnnouncementService.can_receive(user_item, admin_id)
        assert not AnnouncementService.can_receive(user_item, super_admin_id)


def test_role_slug_and_group_are_immutable(app):
    with app.app_context():
        role = Role(
            name="Operations Test",
            slug="operations_test",
            description="Test",
            is_system=False,
            group_slug="admin",
        )
        db.session.add(role)
        db.session.commit()

        role.slug = "renamed"
        try:
            db.session.commit()
            assert False, "Role slug mutation should have been rejected."
        except ValueError:
            db.session.rollback()

        role = db.session.get(Role, role.id)
        assert role.slug == "operations_test"
