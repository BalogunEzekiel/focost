"""Central module entitlements: feature switch + role + plan + operation."""
import json
from app.extensions import db
from app.models.integration import FeaturePolicy

DEFAULTS = {
    # Existing core modules share this same policy registry. Their original
    # route-level RBAC and subscription decorators remain in force as defense in depth.
    "dashboard": ("Dashboard", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "income": ("Income management", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "expenses": ("Expense management", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "budgets": ("Budgets", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "goals": ("Goals", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "reports": ("Reports and exports", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "ai_chat": ("FOCOST AI", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "assets": ("Investments and assets", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "categories": ("Financial categories", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "export"]),
    "multilingual": ("Multi-language", True, ["user", "admin"], ["basic", "plus", "pro", "free trial"], ["view", "configure", "manage"]),
    "privilege_management": ("Granular feature privileges", True, ["super_admin", "admin"], ["admin"], ["view", "configure", "manage"]),
    "bank_readonly": ("Read-only bank connections", False, ["user"], ["plus", "pro"], ["view", "create", "sync", "delete", "import"]),
    "receipt_ocr": ("Receipt scanning", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "import"]),
    "statement_intelligence": ("Bank statement intelligence", True, ["user"], ["basic", "plus", "pro", "free trial"], ["view", "create", "edit", "delete", "import", "export"]),
}

class FeatureAccessService:
    @staticmethod
    def ensure_defaults():
        from app.models.integration import FeaturePolicy
        existing = {item.module_key: item for item in FeaturePolicy.query.all()}
        changed = False
        for key, (label, enabled, roles, plans, operations) in DEFAULTS.items():
            if key not in existing:
                item = FeaturePolicy(module_key=key, label=label, enabled=enabled,
                    allowed_roles_json=json.dumps(roles), allowed_plans_json=json.dumps(plans),
                    operations_json=json.dumps(operations), delegated_roles_json="[]",
                    config_json=json.dumps({"supported_languages": ["en", "yo", "ha", "fr", "es", "pt"]} if key == "multilingual" else {"providers": ["mono"]} if key == "bank_readonly" else {"formats": ["csv", "xlsx", "xlsm", "pdf", "png", "jpg", "jpeg", "webp", "tif", "tiff"]} if key == "statement_intelligence" else {}))
                db.session.add(item)
                changed = True
        if changed:
            db.session.commit()
            try:
                from flask import g, has_request_context
                if has_request_context() and hasattr(g, "_focost_feature_policies"):
                    del g._focost_feature_policies
            except Exception:
                pass

    
    @staticmethod
    def policy(key):
        from flask import g, has_request_context

        if has_request_context():
            cache = getattr(g, "_focost_feature_policies", None)
            if cache is not None and key in cache:
                return cache[key]

        # This may invalidate the request-local cache when defaults are added.
        FeatureAccessService.ensure_defaults()

        if has_request_context():
            # Reinitialize the cache after ensure_defaults(), because that
            # method may have removed it after changing the policy registry.
            cache = getattr(g, "_focost_feature_policies", None)
            if cache is None:
                cache = {}
                g._focost_feature_policies = cache

            if key in cache:
                return cache[key]

        item = FeaturePolicy.query.filter_by(module_key=key).first()

        if has_request_context():
            g._focost_feature_policies[key] = item

        return item


    @staticmethod
    def can_manage(user, key):
        if getattr(user, "is_super_admin", False):
            return True
        policy = FeatureAccessService.policy(key)
        return bool(policy and user.is_admin_group
                    and user.role_slug in policy.json_list("delegated_roles_json")
                    and ({"manage", "configure"} & set(policy.json_list("operations_json"))))

    @staticmethod
    def allowed_existing_module(user, key, operation="view"):
        """Central role/operation gate that preserves each legacy module's own subscription decorator."""
        if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
            return False
        policy = FeatureAccessService.policy(key)
        if not policy or not policy.enabled or not getattr(user, "is_normal_user", False):
            return False
        if "user" not in policy.json_list("allowed_roles_json") or operation not in policy.json_list("operations_json"):
            return False
        try:
            from app.subscriptions.service import SubscriptionService
            subscription = SubscriptionService.current(user.id, create_trial=False)
            # Preserve legacy behavior for accounts without a subscription row;
            # routes that require a plan continue to enforce their existing decorators.
            if subscription is None or not subscription.is_active_access:
                # Let the established route-level subscription decorator handle
                # expired/missing subscription UX and redirects; this middleware
                # must not mask those workflows with a generic 403.
                return True
            plan = "free trial" if getattr(subscription, "is_trial", False) else ((subscription.plan.name or "").strip().lower() if subscription.plan else "")
            return plan in [p.lower() for p in policy.json_list("allowed_plans_json")]
        except Exception:
            return False

    @staticmethod
    def allowed(user, key, operation="view"):
        if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
            return False
        policy = FeatureAccessService.policy(key)
        if not policy or not policy.enabled:
            return False
        if getattr(user, "is_super_admin", False):
            # Administrative governance is not an end-user subscription feature.
            return key in {"multilingual", "privilege_management"} and operation in policy.json_list("operations_json")
        if getattr(user, "is_admin_group", False):
            return (user.role_slug in policy.json_list("allowed_roles_json") and
                    operation in policy.json_list("operations_json"))
        if not getattr(user, "is_normal_user", False):
            return False
        if "user" not in policy.json_list("allowed_roles_json") or operation not in policy.json_list("operations_json"):
            return False
        try:
            from app.subscriptions.service import SubscriptionService
            sub = SubscriptionService.current(user.id, create_trial=False)
            if not sub or not sub.is_active_access:
                return False
            plan = "free trial" if getattr(sub, "is_trial", False) else ((sub.plan.name or "").strip().lower() if sub.plan else "")
            return plan in [p.lower() for p in policy.json_list("allowed_plans_json")]
        except Exception:
            return False
