"""Static regression contracts for the FOCOST enhancement bundle.
Run from the extracted package root: python -m unittest discover -s tests/regression -v
These checks complement, but do not replace, the application's integration suite.
"""
from pathlib import Path
import ast
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]

class EnhancementContracts(unittest.TestCase):
    def read(self, relative):
        path = ROOT / relative
        self.assertTrue(path.is_file(), f"Missing expected file: {relative}")
        return path.read_text(encoding="utf-8")

    def test_currency_service_is_display_only(self):
        source = self.read("app/services/currency_service.py")
        ast.parse(source)
        self.assertIn("class CurrencyService", source)
        self.assertIn("def format", source)
        self.assertNotRegex(source.lower(), r"exchange.?rate|forex|convert_currency|fx_api")

    def test_supported_languages_are_declared(self):
        source = self.read("app/services/language_service.py")
        ast.parse(source)
        for code in ('"en"', '"yo"', '"ha"', '"fr"', '"es"', '"pt"'):
            self.assertIn(code, source)
        self.assertIn("def speech_locale", source)

    def test_communication_sender_allowlist_is_enforced(self):
        source = self.read("app/services/email_service.py")
        ast.parse(source)
        self.assertIn("MAIL_ALLOWED_FROM", source)
        for address in ("focostteam@gmail.com", "focostsupport@gmail.com", "focostprivacy@gmail.com", "focostsecurity@gmail.com"):
            self.assertIn(address, source)

    def test_communication_supports_individual_recipients_and_deduplication(self):
        service = self.read("app/services/announcement_service.py")
        route = self.read("app/routes/admin_communications.py")
        self.assertIn("normalize_individual_emails", service)
        self.assertIn("recipient_emails", service)
        self.assertIn("recipient_emails", route)
        self.assertRegex(service.lower(), r"set\(|\.lower\(\)")

    def test_migration_is_based_on_existing_communications_head(self):
        migration = self.read("migrations/versions/ab31c9d8e702_communication_recipients_sender_identity.py")
        self.assertIn('revision = "ab31c9d8e702"', migration)
        self.assertIn('down_revision = "f1a9c7d2e604"', migration)
        self.assertIn('"recipient_emails"', migration)
        self.assertIn('"sender_identity"', migration)

    def test_settings_routes_and_template_exist(self):
        for item in ("app/routes/settings.py", "app/templates/includes/modals/settings_modal.html", "app/routes/profile.py"):
            self.read(item)

if __name__ == "__main__":
    unittest.main()
