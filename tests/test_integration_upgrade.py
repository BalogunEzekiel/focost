from pathlib import Path

from app.services.document_intelligence_service import DocumentIntelligenceService
from app.services.language_service import LanguageService
from app.services.feature_access_service import FeatureAccessService


def test_statement_csv_extracts_signed_income_and_expense():
    csv_text = "Date,Description,Debit,Credit,Balance\n2026-01-01,Groceries,2500,,10000\n2026-01-02,Salary,,50000,60000\n"
    rows = DocumentIntelligenceService._statement_rows(csv_text, "csv")
    assert len(rows) == 2
    assert rows[0]["amount"] == -2500
    assert rows[0]["kind"] == "expense"
    assert rows[1]["amount"] == 50000
    assert rows[1]["kind"] == "income"
    assert "fingerprint" in rows[0]


def test_statement_duplicate_is_flagged_not_silently_removed():
    csv_text = "Date,Description,Amount\n2026-01-01,POS Grocery,-1000\n2026-01-01,POS Grocery,-1000\n"
    rows = DocumentIntelligenceService._statement_rows(csv_text, "csv")
    assert len(rows) == 2
    assert rows[0]["possible_duplicate"] is False
    assert rows[1]["possible_duplicate"] is True


def test_language_catalogue_defaults_to_english():
    assert LanguageService.translate("en", "income") == "Income"
    assert LanguageService.translate("yo", "expenses") == "Ìnáwó"
    assert LanguageService.translate("unsupported", "income") == "Income"


def test_feature_policy_defaults_and_bank_operations(app):
    with app.app_context():
        FeatureAccessService.ensure_defaults()
        policy = FeatureAccessService.policy("bank_readonly")
        assert policy is not None
        assert policy.enabled is False
        assert "sync" in policy.json_list("operations_json")
        assert "import" in policy.json_list("operations_json")


def test_bank_routes_are_read_only_and_no_payment_routes_are_defined():
    source = (Path(__file__).resolve().parents[1] / "app/routes/integrations.py").read_text(encoding="utf-8")
    assert "bank_sync" in source
    assert "bank_disconnect" in source
    assert "payment" not in source.lower() or "cannot initiate" in source.lower() or "read-only" in source.lower()
    assert "api.withmono.com/v2/accounts/auth" in source
    assert "api.withmono.com/v2/accounts/{provider_account_id}/unlink" in source
    assert "transfer" not in source.lower() or "no payment" in source.lower() or "read-only" in source.lower()


def test_upgrade_migration_is_present():
    migration = Path(__file__).resolve().parents[1] / "migrations/versions/f9c2a6d8e401_add_integration_governance_and_imports.py"
    assert migration.exists()
    content = migration.read_text(encoding="utf-8")
    assert 'revision = "f9c2a6d8e401"' in content
    assert '"bank_sync_records"' in content
