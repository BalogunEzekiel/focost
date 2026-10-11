# FOCOST Integration Upgrade Review — 9 October 2026

## Architecture and implementation

The upgrade extends the existing Flask/SQLAlchemy architecture. `DashboardService` remains the source of truth for dashboard and AI financial facts. Confirmed imports create rows in the existing `Income` and `Expense` ledger models; no parallel totals engine was introduced. Existing `CategoryService`, `SettingsService`/`UserSettings`, subscription transaction limits, RBAC, and compliance acknowledgement models are reused.

### Implemented in this revision

- Fixed the category index template path and completed the responsive category-management view, preserving existing system-category and Plus/Pro personal-category rules.
- Added a centralized `FeaturePolicy` registry and `FeatureAccessService` for module switches, roles/custom roles, Basic/Plus/Pro/Free Trial groups, operations and delegated module management. Core financial route groups also use the shared policy check while existing route permissions and subscription decorators remain in place.
- Added persistent language preferences, configurable supported languages, common translated navigation labels, language-aware AI prompts and browser voice locale selection.
- Added private receipt and statement upload workflows with file signature/size checks, private storage permissions, duplicate file detection, OCR/extraction, category suggestions, review/correction, balance mismatch/outlier hints, subscription transaction-limit checks, and explicit confirm-before-import.
- Added a Mono Connect read-only account adapter for account authorization, balance/transaction retrieval, deduped staged transactions, editable confirmation, sync status and provider unlink. Provider identifiers and cached balances are encrypted using `APP_ENCRYPTION_KEY`; provider credentials are environment-only.
- Added a retention cleanup CLI command, audit events for integration operations, a schema migration, dependency updates, setup documentation and integration tests.
- Refined the category, legal policy/history and administrative compliance evidence templates; added `/admin/compliance/history` with pagination.

## Production-readiness boundaries

This is a substantial implementation, but it is **not honestly certifiable as fully production-ready from this environment**:

1. The Flask test suite could not run because Flask is not installed in the provided execution environment and package installation could not reach the package index. Python compilation and isolated parser/static smoke checks passed, but the full integration suite must run in the project virtual environment.
2. Mono credentials, business onboarding, sandbox account linking, provider response variations, balance/transaction currency units and unlink behavior have not been exercised against a live/sandbox FOCOST deployment. Configure and test the Mono account before enabling the module for users.
3. There is no verified webhook receiver or asynchronous job queue in this revision. Manual sync and staged review are supported; production-grade real-time updates, scheduled backfills and large document processing need an authenticated webhook/queue design.
4. English is the default and language preferences affect common navigation, AI responses and browser voice locale. This is **not yet a full professional translation of every legacy page, report, notification, email, legal document or financial category**. Those strings need reviewed locale catalogues and native-speaker QA.
5. OCR and statement reconciliation are advisory. OCR may miss fields, and reconciliation requires a statement with reliable balances. Every transaction remains subject to user review; flagged records are never silently imported.
6. Configure database/storage encryption at rest, private upload-directory ACLs, backup/retention controls, production HTTPS, secret management and monitoring before handling real bank statements.

## Deployment checklist

1. Back up the database and any private document archive.
2. Install dependencies from `requirements.txt`; use `requirements-dev.txt` for tests.
3. Configure `MONO_PUBLIC_KEY`, `MONO_SECRET_KEY`, a stable `APP_ENCRYPTION_KEY`, `INTEGRATION_UPLOAD_DIR`, `INTEGRATION_UPLOAD_RETENTION_DAYS` and a 10 MB request limit as documented in `FOCOST_INTEGRATION_UPGRADE.md`.
4. Run `flask db upgrade` and confirm the new revision `f9c2a6d8e401` is the sole Alembic head.
5. Run `python -m compileall -q app migrations tests` and `pytest -q` in the full project environment.
6. In `/admin/integrations`, review role/plan/operation assignments, delegation, supported languages/formats and provider switches. Keep bank linking disabled until Mono sandbox tests pass.
7. Test CSV/XLSX/text-PDF imports, scanned OCR, duplicate imports, transaction limits, account unlink, expired subscriptions and user deletion on a staging database.
8. Schedule `flask purge-integration-imports` according to the configured retention period.
