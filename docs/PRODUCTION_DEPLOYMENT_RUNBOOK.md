# FOCOST Production Deployment Runbook

## 1. Never deploy these from the source package

- `.env`
- production database files
- `instance/*.backup*`, `instance/*.forensic*`, recovery databases
- `.git/`
- `.venv/`
- API keys, Paystack secrets, encryption keys, SMTP passwords or signing keys

Use environment/secret storage instead.

## 2. Test environment

```powershell
cd C:\Users\win\Documents\focost
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set a test `DATABASE_URL` to an isolated test database. Never point tests at production.

Run:

```powershell
python -m pytest -q
```

Compile-only fallback when dependencies are not installed:

```powershell
python -m compileall -q app migrations tests
```

## 3. Database migration

Create a backup before production migration.

```powershell
flask db current
flask db upgrade
flask db current
```

The compliance/authentication migration is:

```text
c4d8e2f1a9b3
```

The migration preserves access for existing accounts by treating accounts created before this verification rollout as already established; all newly registered accounts must verify email before activation.

It adds policy documents/acceptance records, one-time authentication tokens, authentication throttles, the Super Admin document archive and the user authentication-session version.

Do not use `db.create_all()` as a production migration mechanism.

## 4. Seed governance data

After the migration:

```powershell
flask seed all
```

This seeds RBAC plus the current FOCOST policy catalog. Confirm the Super Administrator account is verified and has the intended permissions.

## 5. Transactional email

Configure a production SMTP/transactional email provider:

```text
MAIL_ENABLED=true
MAIL_HOST=...
MAIL_PORT=587
MAIL_USERNAME=...
MAIL_PASSWORD=...
MAIL_FROM=no-reply@your-domain
MAIL_USE_TLS=true
```

Verify SPF, DKIM and DMARC for the sending domain. Registration must not be released publicly until verification email delivery has been tested.

## 6. Security secrets

Generate unique production values for:

- `SECRET_KEY`
- `APP_ENCRYPTION_KEY` (Fernet key)
- Paystack secret/public/webhook credentials
- Groq API key(s)
- SMTP credentials
- database credentials

Never reuse development secrets.

## 7. HTTPS and cookies

Set:

```text
APP_BASE_URL=https://your-real-domain
SESSION_COOKIE_SECURE=true
REMEMBER_COOKIE_SECURE=true
```

Confirm HTTP redirects to HTTPS at the reverse proxy/hosting layer.

## 8. Email-authentication acceptance test

Test:

1. Register a new account.
2. Confirm it cannot access the protected application before verification.
3. Confirm verification email arrives.
4. Confirm the link is one-time and expires.
5. Confirm resend invalidates the previous token.
6. Confirm verified account activates and can log in.
7. Confirm wrong/expired tokens are rejected.

## 9. Password recovery acceptance test

Test:

1. Request reset for an existing email.
2. Request reset for a non-existent email and confirm the response does not reveal account existence.
3. Confirm the link expires.
4. Confirm the link is single-use.
5. Confirm password changes require the new password and confirmation.
6. Confirm previous authenticated sessions are invalidated after reset.

## 10. Privacy/compliance acceptance test

Confirm:

- Privacy, Terms, Cookies, AI Disclosure and Acceptable Use pages are live over HTTPS.
- Registration records exact policy versions accepted.
- Policy updates trigger re-acknowledgement.
- Data export works.
- Account deletion works and legal-retention exceptions are documented.
- Super Admin can access the Document Archive.
- ROPA, DPIA, processor inventory and DPAs are archived after approval.

## 11. Payments

FOCOST's web billing remains server-authoritative. Verify payment amount, currency, reference and provider response server-side before granting entitlements. Keep Paystack credentials server-side.

For a native Android/iOS product, use the platform's applicable billing rules and validate store purchases server-side before granting premium entitlements.

## 12. Backups and rollback

Before every schema release:

1. Create a verified database backup.
2. Record the migration head.
3. Apply migration in staging.
4. Run regression/security tests.
5. Apply to production.
6. Run smoke tests.
7. Record the new migration head.

A rollback plan must use a tested database restore or a forward migration; do not casually downgrade a production financial database.

## 13. Post-deployment smoke test

- Home/public pages
- Registration
- Email verification
- Login/logout
- Forgot/reset password
- Dashboard
- Income/expense/goal/investment workflows
- AI coach and AI limits
- Reports/export
- Subscription purchase/cancellation
- Notifications
- Profile/avatar
- Account deletion
- Super Admin/RBAC/audit logs
- Document archive
- `/healthz` and `/readyz`
- `/.well-known/security.txt`
