"""User-facing receipt, statement and read-only bank integration workflows."""
import hashlib, json
from datetime import datetime, date
import httpx
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.integration import DocumentImport, BankConnection, BankSyncRecord
from app.models.expense import Expense
from app.models.income import Income
from app.services.feature_access_service import FeatureAccessService
from app.services.document_intelligence_service import DocumentIntelligenceService

integrations_bp = Blueprint("integrations", __name__, url_prefix="/integrations")

@integrations_bp.before_request
@login_required
def user_surface():
    if not current_user.is_normal_user:
        abort(403)

@integrations_bp.get("/")
def index():
    imports = DocumentImport.query.filter_by(user_id=current_user.id).order_by(DocumentImport.created_at.desc()).limit(50).all()
    connections = BankConnection.query.filter_by(user_id=current_user.id).order_by(BankConnection.created_at.desc()).all()
    staged_bank_transactions = BankSyncRecord.query.join(BankConnection).filter(BankConnection.user_id == current_user.id, BankSyncRecord.status == "review").order_by(BankSyncRecord.transaction_date.desc()).limit(100).all()
    bank_policy = FeatureAccessService.policy("bank_readonly")
    mono_provider_enabled = bool(bank_policy and "mono" in (bank_policy.config().get("providers") or ["mono"]))
    return render_template("integrations/index.html", imports=imports, connections=connections, staged_bank_transactions=staged_bank_transactions, mono_provider_enabled=mono_provider_enabled,
        receipt_enabled=FeatureAccessService.allowed(current_user, "receipt_ocr", "create"),
        statement_enabled=FeatureAccessService.allowed(current_user, "statement_intelligence", "create"),
        bank_enabled=FeatureAccessService.allowed(current_user, "bank_readonly", "create"),
        mono_public_key=current_app.config.get("MONO_PUBLIC_KEY", ""))

@integrations_bp.post("/upload/<import_type>")
def upload(import_type):
    feature = "receipt_ocr" if import_type == "receipt" else "statement_intelligence" if import_type == "statement" else None
    if not feature: abort(404)
    if not FeatureAccessService.allowed(current_user, feature, "create"): abort(403)
    try:
        record = DocumentIntelligenceService.create(current_user.id, import_type, request.files.get("file"))
        from app.audit.service import AuditService
        AuditService.log(action="document_import.created", category="FINANCIAL_INTEGRATION", description=f"Created a {import_type} review import", resource="document_import", resource_id=record.id)
        flash("Document extracted. Review every transaction and confirm before importing.", "success")
        return redirect(url_for("integrations.review", import_id=record.id))
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("integrations.index"))

@integrations_bp.get("/review/<int:import_id>")
def review(import_id):
    record = DocumentImport.query.filter_by(id=import_id, user_id=current_user.id).first_or_404()
    feature = "receipt_ocr" if record.import_type == "receipt" else "statement_intelligence"
    if not FeatureAccessService.allowed(current_user, feature, "view"): abort(403)
    return render_template("integrations/review.html", record=record, rows=record.extracted().get("transactions", []))

@integrations_bp.post("/review/<int:import_id>/<int:index>/confirm")
def confirm(import_id, index):
    record = DocumentImport.query.filter_by(id=import_id, user_id=current_user.id).first_or_404()
    feature = "receipt_ocr" if record.import_type == "receipt" else "statement_intelligence"
    if not FeatureAccessService.allowed(current_user, feature, "import"): abort(403)
    try:
        record = DocumentIntelligenceService.confirm(current_user.id, import_id, index, request.form)
        from app.audit.service import AuditService
        AuditService.log(action="document_import.transaction_confirmed", category="FINANCIAL_INTEGRATION", description="User confirmed a staged financial transaction", resource="document_import", resource_id=record.id)
        flash("Confirmed transaction added to your financial records.", "success")
    except ValueError as exc:
        flash(str(exc), "warning")
    return redirect(url_for("integrations.review", import_id=import_id))

@integrations_bp.post("/review/<int:import_id>/delete")
def delete_import(import_id):
    record = DocumentImport.query.filter_by(id=import_id, user_id=current_user.id).first_or_404()
    feature = "receipt_ocr" if record.import_type == "receipt" else "statement_intelligence"
    if not FeatureAccessService.allowed(current_user, feature, "delete"): abort(403)
    try:
        DocumentIntelligenceService.delete(current_user.id, import_id)
        from app.audit.service import AuditService
        AuditService.log(action="document_import.deleted", category="FINANCIAL_INTEGRATION", description="Deleted a private document import and source file", resource="document_import", resource_id=import_id)
        flash("Import and retained source file deleted.", "success")
    except ValueError as exc: flash(str(exc), "warning")
    return redirect(url_for("integrations.index"))

@integrations_bp.post("/bank/connect")
def bank_connect():
    if not FeatureAccessService.allowed(current_user, "bank_readonly", "create"): abort(403)
    # Mono Connect Widget returns a short-lived authorization code. The server
    # exchanges it using the private key; no user enters bank credentials here.
    public_key = current_app.config.get("MONO_PUBLIC_KEY")
    secret_key = current_app.config.get("MONO_SECRET_KEY")
    code = (request.form.get("code") or "").strip()
    provider_policy = FeatureAccessService.policy("bank_readonly")
    if not provider_policy or "mono" not in (provider_policy.config().get("providers") or []):
        flash("Mono is not enabled by the Super Admin. No bank data was changed.", "warning")
        return redirect(url_for("integrations.index"))
    if not public_key or not secret_key or not current_app.config.get("APP_ENCRYPTION_KEY"):
        flash("Read-only bank linking is not configured yet. Set MONO_PUBLIC_KEY, MONO_SECRET_KEY and APP_ENCRYPTION_KEY after enabling your Mono account.", "warning")
        return redirect(url_for("integrations.index"))
    if not code or len(code) > 500:
        flash("Bank provider did not return a valid authorization code.", "warning")
        return redirect(url_for("integrations.index"))
    try:
        response = httpx.post("https://api.withmono.com/v2/accounts/auth", json={"code": code}, headers={"mono-sec-key": secret_key, "Content-Type": "application/json", "Accept": "application/json"}, timeout=15.0)
        response.raise_for_status()
        response_data = response.json()
        payload = response_data.get("data", {}) if isinstance(response_data, dict) else {}
        if not isinstance(payload, dict) or not payload:
            payload = response_data if isinstance(response_data, dict) else {}
        account_id = str(payload.get("id") or "").strip()
        if not account_id or len(account_id) > 180: raise ValueError("Provider did not return an account reference.")
        from app.services.bank_security_service import BankSecurityService
        encrypted_id = BankSecurityService.encrypt(account_id)
        account_fingerprint = hashlib.sha256(f"{current_user.id}:mono:{account_id}".encode("utf-8")).hexdigest()
        existing = BankConnection.query.filter_by(user_id=current_user.id, provider_key="mono", account_fingerprint=account_fingerprint).first()
        if existing:
            existing.status = "connected"; existing.last_error = None
        else:
            db.session.add(BankConnection(user_id=current_user.id, provider_key="mono", provider_account_id=encrypted_id, account_fingerprint=account_fingerprint, account_name="Connected bank account", status="connected"))
        db.session.commit()
        from app.audit.service import AuditService
        AuditService.log(action="bank.account.connected", category="FINANCIAL_INTEGRATION", description="Connected a read-only bank account", resource="bank_connection", status="success")
        flash("Bank account connected in read-only mode. FOCOST cannot initiate transfers or payments.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Mono read-only account authorization failed for user_id=%s", current_user.id)
        flash("Bank account connection failed. Check provider configuration and try again.", "danger")
    return redirect(url_for("integrations.index"))

@integrations_bp.post("/bank/<int:connection_id>/sync")
def bank_sync(connection_id):
    if not FeatureAccessService.allowed(current_user, "bank_readonly", "sync"): abort(403)
    conn = BankConnection.query.filter_by(id=connection_id, user_id=current_user.id, provider_key="mono").first_or_404()
    secret = current_app.config.get("MONO_SECRET_KEY")
    provider_policy = FeatureAccessService.policy("bank_readonly")
    if not provider_policy or "mono" not in (provider_policy.config().get("providers") or []):
        flash("Mono is not enabled by the Super Admin. No bank data was changed.", "warning"); return redirect(url_for("integrations.index"))
    if not secret or not current_app.config.get("APP_ENCRYPTION_KEY"):
        flash("Bank provider or encryption key is not configured. No data was changed.", "warning"); return redirect(url_for("integrations.index"))
    try:
        from app.services.bank_security_service import BankSecurityService
        provider_account_id = BankSecurityService.decrypt(conn.provider_account_id)
        headers = {"mono-sec-key": secret, "Accept": "application/json"}
        with httpx.Client(timeout=20.0, headers=headers) as client:
            account_resp = client.get(f"https://api.withmono.com/v2/accounts/{provider_account_id}")
            account_resp.raise_for_status(); account_payload = account_resp.json().get("data", {})
            account = account_payload.get("account", account_payload) if isinstance(account_payload, dict) else {}
            provider_meta = account_payload.get("meta", {}) if isinstance(account_payload, dict) and isinstance(account_payload.get("meta"), dict) else {}
            provider_data_status = str(provider_meta.get("data_status") or "AVAILABLE").upper()
            data = []
            for page in range(1, 11):
                txn_resp = client.get(f"https://api.withmono.com/v2/{provider_account_id}/transactions", params={"paginate": "true", "limit": 100, "page": page})
                txn_resp.raise_for_status(); txn_payload = txn_resp.json()
                page_data = txn_payload.get("data", [])
                if isinstance(page_data, dict): page_data = page_data.get("transactions", [])
                if not isinstance(page_data, list) or not page_data: break
                data.extend(page_data)
                meta = txn_payload.get("meta", {}) if isinstance(txn_payload.get("meta"), dict) else {}
                if not meta.get("next") and len(page_data) < 100: break
        imported = 0
        for txn in data[:1000]:
            txn_id = str(txn.get("_id") or txn.get("id") or "").strip()
            description = str(txn.get("narration") or txn.get("description") or txn.get("type") or "Bank transaction").strip()[:255]
            raw_amount = txn.get("amount")
            try:
                # Mono represents transaction amounts in minor units (kobo).
                amount = abs(float(raw_amount)) / 100.0
            except (TypeError, ValueError): continue
            txn_type = str(txn.get("type") or txn.get("transaction_type") or "").lower()
            if txn_type in {"debit", "withdrawal", "outgoing"}:
                amount = -amount
            if not txn_id or amount == 0: continue
            dt = txn.get("date") or txn.get("created_at") or txn.get("createdAt")
            try: tx_date = datetime.fromisoformat(str(dt).replace("Z", "+00:00")).date()
            except (ValueError, TypeError): continue
            # Mono account transactions are imported into a staging ledger only;
            # users explicitly review/confirm before financial records are created.
            fingerprint = hashlib.sha256(f"{tx_date}|{amount:.2f}|{description.lower()}".encode()).hexdigest()
            if BankSyncRecord.query.filter_by(connection_id=conn.id, provider_transaction_id=txn_id).first(): continue
            db.session.add(BankSyncRecord(connection_id=conn.id, provider_transaction_id=txn_id, transaction_date=tx_date, description=description, amount=amount, currency=(account.get("currency") or "NGN")[:8], fingerprint=fingerprint, raw_json="{}", status="review"))
            imported += 1
        institution = account.get("institution") if isinstance(account.get("institution"), dict) else {}
        conn.account_name = str(institution.get("name") or account.get("name") or "Connected bank account")[:180]
        conn.account_mask = str(account.get("account_number") or account.get("accountNumber") or "")[-4:]
        conn.currency = str(account.get("currency") or "NGN")[:8]
        try:
            from app.services.bank_security_service import BankSecurityService
            conn.encrypted_balance = BankSecurityService.encrypt(str(float(account.get("balance"))))
        except (TypeError, ValueError):
            conn.encrypted_balance = None
        conn.last_synced_at = datetime.utcnow()
        if provider_data_status in {"FAILED", "UNAVAILABLE", "PARTIAL", "PROCESSING"}:
            conn.status = "partial" if provider_data_status in {"PARTIAL", "PROCESSING"} else "error"
            conn.last_error = f"Provider data status: {provider_data_status}"
        else:
            conn.last_error = None
            conn.status = "connected"
        db.session.commit()
        from app.audit.service import AuditService
        AuditService.log(action="bank.account.synced", category="FINANCIAL_INTEGRATION", description=f"Synced read-only bank data; staged {imported} new transaction(s)", resource="bank_connection", resource_id=conn.id, status="success")
        flash(f"Sync complete ({provider_data_status}). {imported} new transactions staged for review; none were automatically posted.", "success" if conn.status == "connected" else "warning")
    except Exception:
        db.session.rollback(); conn.status = "error"; conn.last_error = "Provider sync failed"; db.session.commit()
        current_app.logger.exception("Mono bank sync failed for connection_id=%s", connection_id)
        flash("Bank sync failed. Existing financial records were not changed.", "danger")
    return redirect(url_for("integrations.index"))

@integrations_bp.post("/bank/<int:connection_id>/disconnect")
def bank_disconnect(connection_id):
    if not FeatureAccessService.allowed(current_user, "bank_readonly", "delete"): abort(403)
    conn = BankConnection.query.filter_by(id=connection_id, user_id=current_user.id).first_or_404()
    # Revoke the Mono account link before deleting local credentials/metadata.
    # This is an unlink operation only; it cannot initiate a financial transaction.
    secret = current_app.config.get("MONO_SECRET_KEY")
    try:
        if conn.provider_key == "mono":
            if not secret or not current_app.config.get("APP_ENCRYPTION_KEY"):
                raise RuntimeError("Provider credentials or encryption key are not configured.")
            from app.services.bank_security_service import BankSecurityService
            provider_account_id = BankSecurityService.decrypt(conn.provider_account_id)
            response = httpx.post(f"https://api.withmono.com/v2/accounts/{provider_account_id}/unlink", headers={"mono-sec-key": secret, "Accept": "application/json"}, timeout=15.0)
            response.raise_for_status()
        db.session.delete(conn); db.session.commit()
        from app.audit.service import AuditService
        AuditService.log(action="bank.account.disconnected", category="FINANCIAL_INTEGRATION", description="Unlinked read-only bank account and removed staged sync data", resource="bank_connection", resource_id=connection_id)
        flash("Bank account unlinked at the provider. Staged sync data was removed; previously posted financial records remain unchanged.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Bank unlink failed for connection_id=%s", connection_id)
        flash("The provider could not confirm unlinking. The local connection was retained so you can retry safely.", "danger")
    return redirect(url_for("integrations.index"))


@integrations_bp.post("/bank/transaction/<int:record_id>/confirm")
def confirm_bank_transaction(record_id):
    if not FeatureAccessService.allowed(current_user, "bank_readonly", "import"): abort(403)
    record = BankSyncRecord.query.join(BankConnection).filter(BankSyncRecord.id == record_id, BankConnection.user_id == current_user.id).with_for_update().first_or_404()
    if record.status != "review":
        flash("This bank transaction has already been reviewed.", "warning")
        return redirect(url_for("integrations.index"))
    desc = " ".join(str(request.form.get("description", record.description)).split())[:255]
    try:
        tx_date = date.fromisoformat(str(request.form.get("date", record.transaction_date.isoformat())))
        amount = abs(float(request.form.get("amount", abs(record.amount))))
    except (ValueError, TypeError):
        flash("Enter a valid date and positive amount.", "warning")
        return redirect(url_for("integrations.index"))
    kind = str(request.form.get("kind", "income" if record.amount > 0 else "expense")).lower()
    if not desc or amount <= 0 or kind not in {"income", "expense"}:
        flash("Enter a valid description, amount and transaction type.", "warning")
        return redirect(url_for("integrations.index"))
    from app.services.document_intelligence_service import _category
    from app.services.category_service import CategoryService
    category = " ".join(str(request.form.get("category") or _category(desc, kind)).split())[:100]
    CategoryService.ensure_system_categories()
    if not CategoryService.is_valid_for_user(current_user.id, kind, category):
        category = "Other"
    if kind == "expense":
        duplicate = Expense.query.filter_by(user_id=current_user.id, merchant=desc[:150], expense_date=tx_date, amount=amount).first()
    else:
        duplicate = Income.query.filter_by(user_id=current_user.id, source=desc[:150], received_date=tx_date, amount=amount).first()
    if duplicate:
        record.status = "duplicate"
        db.session.commit()
        flash("Matching transaction already exists. The bank record was marked as duplicate; no new financial record was created.", "warning")
        return redirect(url_for("integrations.index"))
    from app.subscriptions.service import SubscriptionService
    allowed, limit_message = SubscriptionService.can_add_transaction(current_user.id)
    if not allowed:
        flash(limit_message or "Your active subscription does not allow another transaction.", "warning")
        return redirect(url_for("integrations.index"))
    if kind == "expense":
        db.session.add(Expense(user_id=current_user.id, category=category, merchant=desc[:150], description=desc, amount=amount, payment_method="Bank sync", expense_date=tx_date, notes=f"Confirmed read-only bank transaction #{record.provider_transaction_id}"))
    else:
        db.session.add(Income(user_id=current_user.id, source=desc[:150], category=category, amount=amount, received_date=tx_date, notes=f"Confirmed read-only bank transaction #{record.provider_transaction_id}"))
    record.status = "imported"
    db.session.commit()
    from app.audit.service import AuditService
    AuditService.log(action="bank.transaction.confirmed", category="FINANCIAL_INTEGRATION", description="User confirmed a staged read-only bank transaction", resource="bank_sync_record", resource_id=record.id)
    flash("Bank transaction confirmed and added to financial records.", "success")
    return redirect(url_for("integrations.index"))
