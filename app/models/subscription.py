from datetime import datetime
import json

from app.extensions import db
from app.models.base import BaseModel


class SubscriptionPlan(BaseModel):
    __tablename__ = "subscription_plans"

    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    amount_minor = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="NGN")
    interval = db.Column(db.String(20), nullable=False, default="monthly")
    ai_token_limit = db.Column(db.Integer, nullable=False, default=0)
    ai_request_limit = db.Column(db.Integer, nullable=False, default=0)
    transaction_limit = db.Column(db.Integer)
    feature_entitlements = db.Column(db.Text, nullable=False, default="{}")
    paystack_plan_code = db.Column(db.String(120), unique=True)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def entitlements(self):
        try:
            return json.loads(self.feature_entitlements or "{}")
        except (TypeError, ValueError):
            return {}

    @property
    def amount(self):
        return self.amount_minor / 100

    @property
    def price(self):
        return self.amount

    @property
    def billing_cycle(self):
        return self.interval

    @property
    def active(self):
        return self.is_active

    @property
    def subscriber_count(self):
        return len([s for s in self.subscriptions if s.status == "active"])


class UserSubscription(BaseModel):
    __tablename__ = "user_subscriptions"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id"), nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="trial", index=True)
    is_trial = db.Column(db.Boolean, nullable=False, default=True, index=True)
    trial_started_at = db.Column(db.DateTime)
    trial_ends_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)
    canceled_at = db.Column(db.DateTime)
    provider = db.Column(db.String(30), nullable=False, default="paystack")
    provider_subscription_code = db.Column(db.String(160), unique=True)
    provider_email_token = db.Column(db.String(255))
    metadata_json = db.Column(db.Text, nullable=False, default="{}")

    user = db.relationship("User", backref=db.backref("subscriptions", lazy=True, cascade="all, delete-orphan"))
    plan = db.relationship("SubscriptionPlan", backref=db.backref("subscriptions", lazy=True))

    def get_metadata(self):
        try:
            return json.loads(self.metadata_json or "{}")
        except (TypeError, ValueError):
            return {}

    @property
    def start_date(self):
        return self.current_period_start or self.trial_started_at

    @property
    def end_date(self):
        return self.current_period_end or self.trial_ends_at

    @property
    def is_active_access(self):
        now = datetime.utcnow()
        if self.status == "trial":
            return bool(self.trial_ends_at and self.trial_ends_at > now)
        if self.status in {"active", "past_due"}:
            return bool(self.current_period_end and self.current_period_end > now)
        return False


class PaymentTransaction(BaseModel):
    __tablename__ = "payment_transactions"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id"), nullable=True, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    provider = db.Column(db.String(30), nullable=False, default="paystack", index=True)
    reference = db.Column(db.String(160), unique=True, nullable=False, index=True)
    amount_minor = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="NGN")
    status = db.Column(db.String(30), nullable=False, default="initialized", index=True)
    gateway_response = db.Column(db.Text)
    paid_at = db.Column(db.DateTime)
    metadata_json = db.Column(db.Text, nullable=False, default="{}")

    user = db.relationship("User", backref=db.backref("payment_transactions", lazy=True, cascade="all, delete-orphan"))
    plan = db.relationship("SubscriptionPlan")
    subscription = db.relationship("UserSubscription")


class PaymentAttempt(BaseModel):
    __tablename__ = "payment_attempts"

    transaction_id = db.Column(db.Integer, db.ForeignKey("payment_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = db.Column(db.Integer, nullable=False, default=1)
    action = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    response_code = db.Column(db.String(20))
    response_message = db.Column(db.Text)
    duration_ms = db.Column(db.Integer)

    transaction = db.relationship("PaymentTransaction", backref=db.backref("attempts", lazy=True, cascade="all, delete-orphan"))


class PaystackCustomer(BaseModel):
    __tablename__ = "paystack_customers"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    customer_code = db.Column(db.String(160), unique=True, nullable=False)
    provider_email = db.Column(db.String(160), nullable=False)

    user = db.relationship("User", backref=db.backref("paystack_customer", uselist=False, cascade="all, delete-orphan"))


class WebhookEvent(BaseModel):
    __tablename__ = "payment_webhook_events"

    provider = db.Column(db.String(30), nullable=False, default="paystack")
    event_key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(100), nullable=False, index=True)
    payload_json = db.Column(db.Text, nullable=False)
    signature = db.Column(db.String(255))
    status = db.Column(db.String(30), nullable=False, default="received")
    processed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)


class SubscriptionEvent(BaseModel):
    __tablename__ = "subscription_events"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("user_subscriptions.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    old_status = db.Column(db.String(30))
    new_status = db.Column(db.String(30))
    source = db.Column(db.String(40), nullable=False, default="system")
    details_json = db.Column(db.Text, nullable=False, default="{}")

    user = db.relationship("User")
    subscription = db.relationship("UserSubscription")