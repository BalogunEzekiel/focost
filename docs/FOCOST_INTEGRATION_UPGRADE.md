# FOCOST Integration Upgrade

## Architecture and reuse

This upgrade reuses the existing Flask application factory (`app/__init__.py`), SQLAlchemy extension and models, `UserSettings`/`SettingsService`, RBAC role groups and `permission_required`, `SubscriptionService.can_add_transaction`, `CategoryService`, existing `Income`/`Expense` models, and `DashboardService`. Imported records are written only after a user confirms them; therefore existing dashboard/report/AI paths continue to read the authoritative financial ledger rather than a second set of calculations. The compliance pages reuse `PolicyAcceptance`, its relationships and existing legal/compliance routes.

Key existing integration points:

- `app/services/dashboard_service.py`: authoritative financial facts used by dashboards and AI; unchanged as source of truth.
- `app/services/settings_service.py` and `app/models/user_settings.py`: persistent per-user language preference.
- `app/services/category_service.py` and `app/forms/category_forms.py`: system/personal category validation and Plus/Pro customization rules.
- `app/models/income.py` and `app/models/expense.py`: existing ledger records created only after explicit confirmation, with the existing subscription transaction-limit check.
- `app/rbac/decorators.py`, `app/rbac/constants.py` and `RBACMiddleware`: existing route-level authorization retained as defense in depth.
- `app/models/compliance.py`, `app/routes/compliance.py` and `app/routes/admin.py`: existing legal acknowledgements and admin compliance evidence.

### Added modules

- `FeatureAccessService`: central module switch, role, plan, operation and delegated-manager policy registry. Existing financial route prefixes also use a central entitlement check while their original route decorators remain in place.
- `LanguageService`: persisted user language preference, supported language catalogue, common navigation labels and language instruction for FOCOST AI. Browser speech recognition/synthesis reads the selected locale from the document language attribute.
- `DocumentIntelligenceService`: private file storage, checksum duplicate prevention, CSV/Excel/text-PDF extraction, optional image/scanned-PDF OCR, category suggestions, duplicate hints, running-balance mismatch hints and confirm-before-posting.
- `integrations` routes/templates: receipt/statement review, import confirmation, source deletion, Mono account connection, staged read-only bank transactions, sync status and disconnect.
- `/admin/integrations`: centralized policy controls for module enablement, roles, plans, operations, supported languages/formats/providers and delegated module managers.
- `BankSecurityService`: encrypts Mono account identifiers and cached account balances with a key derived from `APP_ENCRYPTION_KEY`. Provider keys are environment-only and never entered into the admin form.

## Migrations and local setup

1. Back up the database and private document archive.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Configure `.env` from `.env.example`; retain the existing production `SECRET_KEY` and `APP_ENCRYPTION_KEY`. **Do not rotate `APP_ENCRYPTION_KEY` after connecting bank accounts unless you first decrypt/re-encrypt saved account references.**
4. Run `flask db upgrade`.
5. Start the app and visit `/admin/integrations` as Super Admin. Confirm default policies, then enable the desired modules and select roles/plans/operations.
6. Verify `python -m compileall -q app migrations tests` and `pytest -q` before deployment.

The migration adds `feature_policies`, `document_imports`, `bank_connections`, and `bank_sync_records`; it does not rewrite or recalculate existing financial records.

## Read-only Mono provider setup

FOCOST's adapter uses Mono Connect's `scope: auth`, exchanges the one-time code server-side using Mono's `mono-sec-key` header, and requests account/transaction data endpoints only. It does not call payment, transfer, debit, or withdrawal endpoints. Official current documentation: [Mono Connect integration guide](https://docs.mono.co/docs/financial-data/integration-guide), [account information](https://docs.mono.co/docs/financial-data/account-information), and [transactions](https://docs.mono.co/docs/financial-data/transactions), and [unlink](https://docs.mono.co/api/bank-data/accounts/unlink).

- Complete Mono's business onboarding/KYB and create a Connect app.
- Set `MONO_PUBLIC_KEY` and `MONO_SECRET_KEY` in the deployment environment; never commit these keys.
- Set a strong, persistent `APP_ENCRYPTION_KEY`. Generate a Fernet key with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, store it in your secret manager and back it up securely.
- Configure the production webhook URL in Mono if real-time account-status events are required. Scheduled/manual sync currently remains available without webhook-driven refresh.
- Start in Mono sandbox/test mode and verify balances, currency minor units, pagination, duplicate handling, and provider unlink behavior against real provider responses before production use. The disconnect route calls Mono's documented unlink endpoint before deleting local staged data.
- Mono API access, data availability, account refresh frequency and fees depend on Mono's approved product and account configuration.

The Connect widget is loaded from Mono's hosted SDK and sends only a temporary authorization code to FOCOST. FOCOST never asks the user to type bank credentials or OTPs.

## Receipt OCR and statements

- CSV and XLSX/XLSM parsing use existing dependencies.
- PDF text extraction uses `pypdf`; scanned PDF/image OCR additionally requires `pytesseract`, Pillow, PyMuPDF for scanned PDFs, and a compatible Tesseract OS binary installed on the server.
- Set `DOCUMENT_ARCHIVE_DIR` to a private, non-public writable directory. The configured upload limit is enforced before parsing.
- OCR is probabilistic. The user must review and confirm each row; no OCR extraction silently posts to income or expenses.
- Uploads are limited to 10 MB, 1,000 transaction rows, 50 text-PDF pages, and 10 scanned-PDF OCR pages per file. Split larger statements into parts. CSV statements should have a header row with date, description/narration and amount, debit/credit, or withdrawal/deposit columns. Amount signs are normalized to credits positive and debits negative.
- Source files are retained until the user deletes the import or the retention cleanup runs. Configure filesystem encryption, backups and access monitoring to meet your privacy obligations. `flask purge-integration-imports` removes source files and records older than `INTEGRATION_UPLOAD_RETENTION_DAYS` (default 365); schedule it in the host's scheduler.

## Language coverage

English remains the fallback/default. Supported language options (English, Yoruba, Hausa, French, Spanish, Portuguese) are configurable by Super Admin. Common shared navigation labels are translated; the selected language is persisted in `UserSettings`, used for the AI prompt and applied to browser voice input/output locale where the browser supports it. This is not yet a full professional translation of every string in every legacy template, legal document, notification and report. Those remaining strings require reviewed translation catalogues and locale QA before claiming complete localization.

## Security and limitations

- Provider secrets are environment-only; Mono account IDs are encrypted in the database.
- Imported bank transactions remain staged until explicitly confirmed; exact provider transaction IDs are unique per connection.
- CSV/XLSX/PDF/image content is untrusted input. Keep upload directories outside public static paths and apply least-privilege filesystem permissions.
- Balance mismatch and duplicate signals are advisory; statement reconciliation is not certified and depends on statement data quality.
- Existing `DashboardService` remains the authority for dashboard financial totals, and confirmed records are written to the existing `Income` and `Expense` models.
- Production readiness still requires installing dependencies, running the full test suite against the target Python/runtime, validating migration history against a production backup, provider sandbox testing, and review of the app's existing RBAC/entitlement configuration.
