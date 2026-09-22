import hashlib
import json
import hmac
import logging
import os
import time
import uuid
from cryptography.fernet import Fernet

import httpx

from app.extensions import db
from app.models.subscription import PaystackCustomer, PaymentAttempt, PaymentTransaction, WebhookEvent
from .service import SubscriptionService

logger = logging.getLogger(__name__)


class PaystackService:
    BASE_URL = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co").rstrip("/")

    @classmethod
    def secret_key(cls):
        return os.getenv("PAYSTACK_SECRET_KEY", "").strip()

    @classmethod
    def public_key(cls):
        return os.getenv("PAYSTACK_PUBLIC_KEY", "").strip()

    @classmethod
    def webhook_secret(cls):
        return os.getenv("PAYSTACK_WEBHOOK_SECRET", "").strip() or cls.secret_key()

    @classmethod
    def _fernet(cls):
        key = os.getenv("APP_ENCRYPTION_KEY", "").strip()
        if not key:
            raise RuntimeError("APP_ENCRYPTION_KEY is not configured.")
        return Fernet(key.encode())

    @classmethod
    def encrypt_provider_secret(cls, value):
        return cls._fernet().encrypt(value.encode()).decode() if value else None

    @classmethod
    def decrypt_provider_secret(cls, value):
        return cls._fernet().decrypt(value.encode()).decode() if value else None

    @classmethod
    def _request(cls, method, path, **kwargs):
        secret = cls.secret_key()
        if not secret:
            raise RuntimeError("PAYSTACK_SECRET_KEY is not configured.")

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {secret}"
        headers["Content-Type"] = "application/json"

        timeout = float(os.getenv("PAYSTACK_TIMEOUT_SECONDS", "20"))

        with httpx.Client(base_url=cls.BASE_URL, timeout=timeout) as client:
            response = client.request(method, path, headers=headers, **kwargs)

        # Log Paystack's actual response without logging secrets.
        logger.error(
            "Paystack API response: method=%s url=%s status=%s body=%s",
            method,
            response.url,
            response.status_code,
            response.text[:2000],
        )

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code >= 400:
            message = payload.get("message") if isinstance(payload, dict) else None
            raise RuntimeError(
                f"Paystack API error ({response.status_code}): "
                f"{message or response.text[:500]}"
            )

        if not payload.get("status"):
            raise RuntimeError(
                payload.get("message") or "Paystack request failed."
            )

        return payload.get("data") or {}

    @classmethod
    def initialize(cls, user, plan, callback_url):
        reference = f"focost_{uuid.uuid4().hex}"
        payload = {
            "email": user.email,
            "amount": plan.amount_minor,
            "currency": plan.currency,
            "reference": reference,
            "callback_url": callback_url,
            "metadata": {"user_id": user.id, "plan_id": plan.id, "product": "FOCOST"},
        }
        plan_code = SubscriptionService.paystack_plan_code(plan)
        if not plan_code:
            raise RuntimeError(f"Paystack plan code is not configured for {plan.slug}. Run 'flask --app run.py create-paystack-plans' after configuring Paystack credentials.")
        payload["plan"] = plan_code
        tx = SubscriptionService.create_transaction(user.id, plan, reference, payload["metadata"])
        started = time.perf_counter()
        try:
            data = cls._request("POST", "/transaction/initialize", json=payload)
            duration = int((time.perf_counter() - started) * 1000)
            customer = data.get("customer") or {}
            customer_code = customer.get("customer_code")
            if customer_code:
                existing_customer = PaystackCustomer.query.filter_by(user_id=user.id).first()
                if existing_customer:
                    existing_customer.customer_code = customer_code
                    existing_customer.provider_email = user.email
                else:
                    db.session.add(PaystackCustomer(user_id=user.id, customer_code=customer_code, provider_email=user.email))
            db.session.add(PaymentAttempt(transaction_id=tx.id, attempt_number=1, action="initialize", status="success", duration_ms=duration))
            db.session.commit()
            return data, tx
        except Exception as exc:
            duration = int((time.perf_counter() - started) * 1000)
            tx.status = "initialization_failed"
            db.session.add(PaymentAttempt(transaction_id=tx.id, attempt_number=1, action="initialize", status="failed", response_message=str(exc)[:1000], duration_ms=duration))
            db.session.commit()
            raise

    @classmethod
    def verify(cls, reference):
        return cls._request("GET", f"/transaction/verify/{reference}")

    @classmethod
    def disable_subscription(cls, subscription_code, email_token):
        return cls._request("POST", "/subscription/disable", json={"code": subscription_code, "token": email_token})

    @classmethod
    def ensure_customer(cls, user):
        existing = PaystackCustomer.query.filter_by(user_id=user.id).first()
        if existing:
            return existing
        data = cls._request("POST", "/customer", json={"email": user.email, "first_name": user.first_name, "last_name": user.last_name, "phone": user.phone})
        customer = PaystackCustomer(user_id=user.id, customer_code=data["customer_code"], provider_email=user.email)
        db.session.add(customer)
        db.session.commit()
        return customer

    @classmethod
    def verify_signature(cls, raw_body, signature):
        secret = cls.webhook_secret()
        if not secret or not signature:
            return False
        digest = hmac.new(secret.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(digest, signature)

    @classmethod
    def process_webhook(cls, payload, signature=None):
        event = payload.get("event", "unknown")
        data = payload.get("data") or {}
        fallback_key = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        event_key = f"{event}:{data.get('id') or data.get('reference') or fallback_key}"
        existing = WebhookEvent.query.filter_by(event_key=str(event_key)).first()
        if existing and existing.status == "processed":
            return {"status": "duplicate", "event": event}
        if not existing:
            existing = WebhookEvent(provider="paystack", event_key=str(event_key), event_type=event, payload_json=json.dumps(payload, ensure_ascii=False, default=str), signature=signature)
            db.session.add(existing)
            db.session.flush()
        try:
            reference = data.get("reference")
            tx = PaymentTransaction.query.filter_by(reference=reference).first() if reference else None
            if event == "charge.success" and tx:
                if int(data.get("amount", 0)) != tx.amount_minor or str(data.get("currency", "")).upper() != tx.currency.upper():
                    raise ValueError("Webhook amount or currency does not match transaction.")
                customer_email = (data.get("customer") or {}).get("email") or data.get("email")
                if customer_email and customer_email.lower() != tx.user.email.lower():
                    raise ValueError("Webhook customer does not match the FOCOST account.")
                expected_plan_code = SubscriptionService.paystack_plan_code(tx.plan) if tx.plan else None
                plan_code = (data.get("plan_object") or {}).get("plan_code") or data.get("plan")
                if expected_plan_code and plan_code and plan_code != expected_plan_code:
                    raise ValueError("Webhook plan does not match the local transaction.")
                if tx.status != "success":
                    SubscriptionService.activate_from_payment(tx, data)
            elif event in {"invoice.payment_success", "subscription.create", "subscription.enable"}:
                code = data.get("subscription_code") or data.get("subscription", {}).get("subscription_code")
                sub = __import__("app.models.subscription", fromlist=["UserSubscription"]).UserSubscription.query.filter_by(provider_subscription_code=code).first() if code else None
                if sub and event == "invoice.payment_success":
                    from datetime import datetime
                    renewal_ref = data.get("reference")
                    if renewal_ref and not PaymentTransaction.query.filter_by(reference=renewal_ref).first():
                        db.session.add(PaymentTransaction(user_id=sub.user_id, plan_id=sub.plan_id, subscription_id=sub.id, provider="paystack", reference=renewal_ref, amount_minor=int(data.get("amount", 0) or 0), currency=data.get("currency", "NGN"), status="success", paid_at=datetime.utcnow(), metadata_json=json.dumps({"event": event}, ensure_ascii=False)))
                    sub.status = "active"
                    sub.current_period_start = datetime.utcnow()
                    next_payment = data.get("next_payment_date")
                    if next_payment:
                        try:
                            sub.current_period_end = datetime.fromisoformat(next_payment.replace("Z", "+00:00")).replace(tzinfo=None)
                        except ValueError:
                            pass
                    sub.cancel_at_period_end = False
                    db.session.add(__import__("app.models.subscription", fromlist=["SubscriptionEvent"]).SubscriptionEvent(user_id=sub.user_id, subscription_id=sub.id, event_type="renewal_success", old_status="active", new_status="active", source="paystack"))
            elif event in {"charge.failed", "invoice.payment_failed"} and tx:
                tx.status = "failed"
                sub = tx.subscription
                if sub:
                    sub.status = "past_due"
                    db.session.add(__import__("app.models.subscription", fromlist=["SubscriptionEvent"]).SubscriptionEvent(user_id=sub.user_id, subscription_id=sub.id, event_type="renewal_failed", old_status="active", new_status="past_due", source="paystack"))
                    from app.services.notification_service import NotificationService
                    NotificationService.create(sub.user_id, "Subscription payment failed", "Your recurring FOCOST payment could not be completed. Please update your payment method to keep paid access.", notification_type="subscription", level="danger", priority="critical", action_url="/billing", unique_key=f"PAYMENT_FAILED:{sub.id}", commit=False)
            elif event in {"subscription.disable", "subscription.not_renew", "subscription.cancel"}:
                code = data.get("subscription_code")
                sub = __import__("app.models.subscription", fromlist=["UserSubscription"]).UserSubscription.query.filter_by(provider_subscription_code=code).first() if code else None
                if sub:
                    sub.cancel_at_period_end = True
                    sub.canceled_at = __import__('datetime').datetime.utcnow()
                    if event == "subscription.disable":
                        sub.status = "canceled"
            existing.status = "processed"
            existing.processed_at = __import__('datetime').datetime.utcnow()
            db.session.commit()
            return {"status": "processed", "event": event}
        except Exception as exc:
            db.session.rollback()
            existing = WebhookEvent.query.filter_by(event_key=str(event_key)).first()
            if existing:
                existing.status = "failed"
                existing.error_message = str(exc)[:1000]
                db.session.commit()
            logger.exception("Paystack webhook processing failed")
            raise

    @classmethod
    def create_or_sync_plans(cls):
        """Create monthly Paystack plans from DB configuration and persist their provider codes."""
        from app.models.subscription import SubscriptionPlan
        plans = SubscriptionService.plans(False)
        results = []
        import os
        for plan in plans:
            env_code = os.getenv(f"PAYSTACK_PLAN_{plan.slug.upper()}", "").strip()
            if env_code and not plan.paystack_plan_code:
                plan.paystack_plan_code = env_code
                db.session.commit()
            if plan.paystack_plan_code:
                results.append({"slug": plan.slug, "code": plan.paystack_plan_code, "created": False})
                continue
            data = cls._request("POST", "/plan", json={
                "name": f"FOCOST {plan.name}",
                "amount": plan.amount_minor,
                "interval": plan.interval,
                "currency": plan.currency,
                "description": plan.description or f"FOCOST {plan.name} monthly subscription",
            })
            plan.paystack_plan_code = data.get("plan_code")
            db.session.commit()
            results.append({"slug": plan.slug, "code": plan.paystack_plan_code, "created": True})
        return results
