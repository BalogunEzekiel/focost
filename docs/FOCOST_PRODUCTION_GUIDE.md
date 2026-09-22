# FOCOST 2.1 — Production, GitHub, PythonAnywhere and Paystack Guide

## 1. Architecture implemented

FOCOST now separates two domains:

- **AI domain:** provider/model selection, conversations, database-derived context, AI usage/token accounting, forecasting and coaching.
- **Subscription domain:** trial lifecycle, plans, entitlements, billing, Paystack transactions, recurring subscriptions, webhook processing and subscription access.

The subscription domain exposes entitlements to the AI domain; AI processing never owns subscription state.

### Subscription catalog

| Plan | Price | AI tokens/month | AI requests/month |
|---|---:|---:|---:|
| Essential | ₦4,900 | 50,000 | 200 |
| Plus | ₦9,900 | 150,000 | 600 |
| Pro | ₦14,900 | 400,000 | 1,500 |

There is **no permanent free plan**. New accounts receive a 30-day trial. After the trial, AI access requires an active paid subscription.

Plan entitlements are stored in `subscription_plans`, not scattered through application code.

## 2. Database domains

The migration adds:

- `subscription_plans`
- `user_subscriptions`
- `payment_transactions`
- `payment_attempts`
- `paystack_customers`
- `payment_webhook_events`
- `subscription_events`
- `ai_usage`
- `assets`

Notifications also gain `read_at`, `dismissed_at`, and `expires_at` lifecycle fields.

## 3. Local installation

### Prerequisites

- Python 3.11+ (3.12 recommended for the supplied project)
- Git
- VS Code
- SQLite for local development, or PostgreSQL for production
- A Paystack test account for payment testing
- At least one configured AI provider key for AI testing

### Extract and open

1. Extract the ZIP.
2. Open the extracted `focost` folder in VS Code.
3. Open a terminal in the project root.

### Virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Environment configuration

Copy `.env.example` to `.env` and fill in secrets locally. Never commit `.env`.

Required core settings:

```text
SECRET_KEY=<long-random-secret>
APP_ENCRYPTION_KEY=<Fernet-key>
DATABASE_URL=sqlite:///instance/focost
FLASK_ENV=development
SESSION_COOKIE_SECURE=false
```

For production, use your platform's secret/environment-variable manager and set `SESSION_COOKIE_SECURE=true`. Generate the encryption key once with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep `APP_ENCRYPTION_KEY` stable; changing it makes encrypted provider tokens unreadable.

### AI

Configure the Groq and/or Cerebras variables shown in `.env.example`. Empty provider keys are permitted; the application starts and reports AI as unavailable until a provider is configured.

### Paystack

Use **test keys** locally:

```text
PAYSTACK_BASE_URL=https://api.paystack.co
PAYSTACK_SECRET_KEY=<test-secret-key>
PAYSTACK_PUBLIC_KEY=<test-public-key>
PAYSTACK_WEBHOOK_SECRET=<normally the Paystack secret key unless you intentionally configure a separate compatible secret>
```

Paystack authenticates backend API calls with a secret key. Transaction amounts are sent in the currency subunit. The application therefore stores ₦4,900 as `490000`, ₦9,900 as `990000`, and ₦14,900 as `1490000`. citeturn0search1

## 5. Database setup

Create the local database directory if necessary, then run:

```bash
flask --app run.py db upgrade
```

Verify the migration chain:

```bash
flask --app run.py db current
```

The final migration is `9c3e1a6d7f2b` and the billing/AI/asset migration is `8f4d2a7c1b9e`.

## 6. Seed RBAC

```bash
flask --app run.py seed-rbac
```

If your installation has an existing RBAC database, run the command after the migration and verify roles/permissions in the admin area.

## 7. Run locally

```bash
python run.py
```

Then open the local address shown by Flask.

Check health:

```text
/healthz
/readyz
```

`/readyz` should report database availability.

## 8. Paystack plan setup

FOCOST keeps the commercial plan definition in its database and stores the corresponding Paystack plan code in `subscription_plans.paystack_plan_code`.

There are two supported workflows:

### A. Create plans in Paystack Dashboard

Create three **monthly** plans with the same amounts as FOCOST and enter their plan codes through the admin/API configuration.

### B. Create missing plans through FOCOST

After configuring a Paystack test secret key:

```bash
flask --app run.py create-paystack-plans
```

This creates missing monthly Paystack plans from the FOCOST database catalog and stores the returned plan codes.

Paystack supports creating plans and using a plan code during transaction initialization to create a recurring subscription. citeturn0search2turn0search11

## 9. End-to-end payment test

1. Configure Paystack test credentials.
2. Create/sync the Paystack plans.
3. Register a new FOCOST account.
4. Confirm the 30-day trial is shown.
5. Open **Plan & Billing**.
6. Select a plan.
7. Confirm FOCOST initializes the transaction server-side.
8. Complete the payment using Paystack's test environment.
9. Allow the callback to return to FOCOST.
10. FOCOST verifies the transaction server-side before activating access.
11. Confirm the user subscription changes to `active`.
12. Confirm the selected plan and billing period are displayed.
13. Confirm AI usage limits now reflect the paid plan.
14. Confirm a payment transaction and subscription event exist in the database.
15. Send the same webhook again and confirm no duplicate subscription/payment activation occurs.

Paystack's transaction API supports initialization and server-side verification. citeturn0search1

## 10. Webhook configuration

Set the Paystack webhook URL to:

```text
https://<your-domain>/billing/webhook
```

The endpoint:

- reads the raw request body;
- validates `x-paystack-signature` using HMAC SHA-512;
- rejects invalid signatures;
- records webhook event identity;
- prevents duplicate processing;
- verifies payment amount/currency against the local transaction;
- updates subscription state transactionally;
- records failures for retry/recovery.

Paystack documents the `x-paystack-signature` HMAC-SHA512 mechanism for webhook verification. citeturn0search3

Relevant lifecycle events include successful charges, failed invoice payments, subscription creation/enabling, non-renewal and disable/cancellation events.

## 11. AI usage enforcement

AI requests pass through the subscription entitlement check before reaching an LLM provider.

Monthly usage is independently recorded in `ai_usage`:

- input tokens
- output tokens
- total tokens
- provider
- model
- request ID
- duration
- status
- optional estimated cost

The AI usage counter is not the billing ledger.

## 12. Database-authentic AI

The AI context is generated by `DashboardService.financial_context()` and `DashboardService.monthly_series()`.

The conversational layer is instructed to use only that database-derived context. For date-sensitive questions, the AI service derives a date/period and passes that period's actual ledger to the model.

If a required record does not exist, the model is instructed to say that the information is unavailable rather than manufacture a figure.

## 13. Forecasting

FOCOST now exposes:

```text
/ai/forecast
```

The forecasting service provides:

- current-month run-rate forecast;
- multi-month trend projection;
- residual-based uncertainty/confidence information;
- monthly historical series;
- anomaly analysis using standard deviation;
- scenario calculations.

Forecasts explicitly remain estimates and are never represented as guaranteed financial outcomes.

## 14. Notifications

The notification service now supports lifecycle fields, priorities, duplicate prevention, expiry and optional email delivery.

Notification categories include financial, budget, goal, subscription and AI-usage alerts. The existing notification center remains the in-app system of record.

Optional email delivery requires the `MAIL_*` variables and a user preference enabling email notifications.

## 15. Profile and assets

Profile management is available at `/profile/` and supports:

- personal details;
- phone/country/currency/occupation;
- avatar upload;
- server-side extension validation.

Assets are available at `/assets/` and are deliberately separate from expense transactions.

## 16. GitHub

The supplied project originally pointed at:

```text
https://github.com/BalogunEzekiel/focost.git
```

For a clean deployment repository:

```bash
git init
git branch -M main
git remote add origin https://github.com/BalogunEzekiel/focost.git
git status
git add .
git commit -m "Enhance FOCOST AI, subscriptions, billing and production readiness"
git push -u origin main
```

Before pushing, confirm:

```bash
git status
git ls-files .env
```

`.env` must not be tracked.

Also inspect for secrets:

```bash
git grep -n -E 'sk_live|sk_test|pk_live|pk_test|GROQ_API_KEY|CEREBRAS_API_KEY|PAYSTACK_SECRET_KEY' -- ':!docs/*'
```

Do not paste real secrets into source files.

## 17. PythonAnywhere deployment

1. Back up the current PythonAnywhere application and database.
2. Pull the updated repository.
3. Open a PythonAnywhere Bash console.
4. Navigate to the application directory.
5. Create/activate the virtual environment.
6. Install dependencies:

```bash
pip install -r requirements.txt
```

7. Configure environment variables in the PythonAnywhere WSGI/environment mechanism used by your account.
8. Set a production `SECRET_KEY`.
9. Set the production `DATABASE_URL`.
10. Set production AI keys.
11. Set **live** Paystack credentials only in the production secret store.
12. Set `SESSION_COOKIE_SECURE=true`.
13. Run migrations:

```bash
flask --app run.py db upgrade
```

14. Confirm `/readyz` reports ready.
15. Reload the PythonAnywhere web application.
16. Test login, dashboard, profile, notifications and AI.
17. Test Paystack webhook delivery from the Paystack dashboard.
18. Verify the webhook reaches `/billing/webhook` and is accepted only with a valid signature.

### Production database warning

Do not run destructive database recreation commands against production. Use Alembic/Flask-Migrate migrations and take a backup first.

## 18. Production Paystack checklist

- [ ] Live secret key configured only on server
- [ ] Live public key exposed only where needed by the client
- [ ] Paystack monthly plan codes stored in DB
- [ ] Correct live callback URL configured
- [ ] Correct live webhook URL configured
- [ ] HTTPS enabled
- [ ] Signature verification confirmed
- [ ] Amount/currency verification confirmed
- [ ] Duplicate webhook test completed
- [ ] Renewal success test completed
- [ ] Failed payment test completed
- [ ] Cancellation test completed
- [ ] Expiration/access-loss test completed
- [ ] Payment records reconciled with Paystack

## 19. Rollback

Before deployment:

```bash
git tag focost-pre-production
```

If application code needs rollback:

```bash
git checkout <known-good-commit>
```

Do not blindly downgrade database migrations if newer production data has already been written. Prefer a forward-fix migration or restore a verified database backup.

## 20. Android / Google Play

See `android/GOOGLE_PLAY_GUIDE.md`.

A Play-distributed FOCOST Android application that sells digital financial-management functionality must be designed around Google Play's current payments rules. Google Play's policy generally requires Google Play Billing for digital subscriptions and financial-management software sold inside a Play-distributed app unless an applicable exception/program applies. citeturn1search0turn1search1
