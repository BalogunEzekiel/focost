from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.extensions import csrf

from app.subscriptions.service import SubscriptionService
from app.subscriptions.paystack import PaystackService
from app.models.subscription import PaymentTransaction

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


@billing_bp.get("/")
@login_required
def index():
    return render_template("billing/index.html", plans=SubscriptionService.plans(), subscription=SubscriptionService.current(current_user.id), entitlements=SubscriptionService.entitlements(current_user.id))


@billing_bp.get("/api")
@login_required
def api_status():
    sub = SubscriptionService.current(current_user.id)
    txs = PaymentTransaction.query.filter_by(user_id=current_user.id).order_by(PaymentTransaction.created_at.desc()).limit(20).all()
    return jsonify({
        "success": True,
        "subscription": {
            "status": sub.status if sub else "none",
            "trial": bool(sub and sub.is_trial),
            "plan": sub.plan.name if sub and sub.plan else "Free Trial",
            "period_start": sub.start_date.isoformat() if sub and sub.start_date else None,
            "period_end": sub.end_date.isoformat() if sub and sub.end_date else None,
            "cancel_at_period_end": bool(sub and sub.cancel_at_period_end),
        } if sub else None,
        "entitlements": SubscriptionService.entitlements(current_user.id),
        "transactions": [{"reference": t.reference, "amount": t.amount_minor / 100, "currency": t.currency, "status": t.status, "created_at": t.created_at.isoformat() if t.created_at else None} for t in txs],
    })


@billing_bp.post("/initialize")
@login_required
def initialize():
    data = request.get_json(silent=True) or request.form
    slug = str(data.get("plan", "")).strip().lower()
    plan = next((p for p in SubscriptionService.plans() if p.slug == slug), None)
    if not plan:
        return jsonify({"success": False, "message": "Invalid subscription plan."}), 400
    try:
        data, tx = PaystackService.initialize(current_user, plan, url_for("billing.callback", _external=True))
        return jsonify({"success": True, "authorization_url": data.get("authorization_url"), "access_code": data.get("access_code"), "reference": tx.reference})
    except Exception:
        current_app.logger.exception("Paystack initialization failed")
        return jsonify({"success": False, "message": "Unable to initialize payment. Please try again."}), 502


@billing_bp.get("/callback")
def callback():
    reference = request.args.get("reference", "").strip()
    if not reference:
        flash("Payment reference was not supplied.", "danger")
        return redirect(url_for("billing.index"))
    tx = PaymentTransaction.query.filter_by(reference=reference).first()
    if not tx:
        flash("Payment transaction could not be found.", "danger")
        return redirect(url_for("auth.login"))
    try:
        verified = PaystackService.verify(reference)
        customer_email = (verified.get("customer") or {}).get("email") or verified.get("email")
        plan_code = (verified.get("plan_object") or {}).get("plan_code") or verified.get("plan")
        expected_plan_code = SubscriptionService.paystack_plan_code(tx.plan) if tx.plan else None
        if int(verified.get("amount", 0)) != tx.amount_minor or str(verified.get("currency", "")).upper() != tx.currency.upper() or verified.get("status") != "success":
            raise ValueError("Paystack verification did not match the transaction.")
        if customer_email and customer_email.lower() != tx.user.email.lower():
            raise ValueError("Paystack customer does not match the FOCOST account.")
        if expected_plan_code and plan_code and plan_code != expected_plan_code:
            raise ValueError("Paystack plan does not match the selected FOCOST plan.")
        SubscriptionService.activate_from_payment(tx, verified)
        flash("Payment verified successfully. Your subscription is active.", "success")
    except Exception:
        current_app.logger.exception("Paystack callback verification failed")
        flash("Payment could not be verified. If you were charged, please contact support with your payment reference.", "warning")
    return redirect(url_for("billing.index"))


@billing_bp.post("/cancel")
@login_required
def cancel():
    try:
        sub = SubscriptionService.current(current_user.id)
        if sub and sub.provider_subscription_code:
            try:
                token = PaystackService.decrypt_provider_secret(sub.provider_email_token)
                if not token:
                    return jsonify({"success": False, "message": "The payment provider did not supply a cancellation token. Please contact support."}), 502
                PaystackService.disable_subscription(sub.provider_subscription_code, token)
            except Exception:
                current_app.logger.exception("Paystack subscription cancellation request failed")
                return jsonify({"success": False, "message": "Paystack could not confirm cancellation. Your subscription was not changed."}), 502
        SubscriptionService.cancel_at_period_end(current_user.id)
        return jsonify({"success": True, "message": "Cancellation scheduled for the end of the current billing period."})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@billing_bp.post("/webhook")
@csrf.exempt
def webhook():
    raw = request.get_data(cache=True)
    signature = request.headers.get("x-paystack-signature", "")
    if not PaystackService.verify_signature(raw, signature):
        return jsonify({"success": False, "message": "Invalid signature."}), 401
    payload = request.get_json(silent=True) or {}
    try:
        result = PaystackService.process_webhook(payload, signature)
        return jsonify({"success": True, **result}), 200
    except Exception:
        return jsonify({"success": False, "message": "Webhook processing failed; Paystack may retry."}), 500
