"""Language catalogue and persisted language preferences."""
from app.services.settings_service import SettingsService

LANGUAGES = {
    "en": {"name": "English", "native": "English", "dir": "ltr"},
    "yo": {"name": "Yoruba", "native": "Yorùbá", "dir": "ltr"},
    "ha": {"name": "Hausa", "native": "Hausa", "dir": "ltr"},
    "fr": {"name": "French", "native": "Français", "dir": "ltr"},
    "es": {"name": "Spanish", "native": "Español", "dir": "ltr"},
    "pt": {"name": "Portuguese", "native": "Português", "dir": "ltr"},
}

class LanguageService:
    @staticmethod
    def available():
        try:
            from app.services.feature_access_service import FeatureAccessService
            policy = FeatureAccessService.policy("multilingual")
            if policy and not policy.enabled:
                return {"en": LANGUAGES["en"]}
            configured = policy.config().get("supported_languages", list(LANGUAGES)) if policy else list(LANGUAGES)
            codes = [code for code in configured if code in LANGUAGES and (code == "en" or code in configured)]
            if "en" not in codes: codes.insert(0, "en")
            return {code: LANGUAGES[code] for code in codes}
        except Exception:
            return LANGUAGES

    @staticmethod
    def get(user_id=None):
        if not user_id:
            return "en"
        try:
            code = SettingsService.get_preferences(user_id).get("language", "en")
            return code if code in LanguageService.available() else "en"
        except Exception:
            return "en"

    @staticmethod
    def set(user_id, code):
        if code not in LanguageService.available():
            raise ValueError("Unsupported language.")
        prefs = SettingsService.get_preferences(user_id)
        prefs["language"] = code
        SettingsService.update(user_id, prefs)
        return code

    @staticmethod
    def translate(code, key):
        catalogue = {
            "en": {"dashboard":"Dashboard", "income":"Income", "expenses":"Expenses", "reports":"Reports", "settings":"Settings", "language":"Language", "budgets":"Budgets", "goals":"Goals", "assets":"Investments & assets", "ai":"FOCOST AI", "notifications":"Notifications", "profile":"Profile", "integrations":"Receipts & statements", "categories":"Categories", "logout":"Sign out", "transactions":"Transactions"},
            "yo": {"dashboard":"Pẹpẹ iṣakoso", "income":"Owó tí wọlé", "expenses":"Ìnáwó", "reports":"Àwọn ìròyìn", "settings":"Ètò", "language":"Èdè", "budgets":"Ètò ìnáwó", "goals":"Àwọn àfojúsùn", "assets":"Ìdókòwò àti ohun-ìní", "ai":"FOCOST AI", "notifications":"Àwọn ìfitónilétí", "profile":"Àkọọ́lẹ̀ ara ẹni", "integrations":"Rísítì àti ìwé banki", "categories":"Àwọn ẹ̀ka", "logout":"Jáde", "transactions":"Àwọn ìṣòwò"},
            "ha": {"dashboard":"Allon kulawa", "income":"Kuɗin shiga", "expenses":"Kuɗaɗen kashewa", "reports":"Rahotanni", "settings":"Saituna", "language":"Harshe", "budgets":"Kasafin kuɗi", "goals":"Manufofi", "assets":"Jari da kadarori", "ai":"FOCOST AI", "notifications":"Sanarwa", "profile":"Bayanan mutum", "integrations":"Rasiti da bayanan banki", "categories":"Rukuni", "logout":"Fita", "transactions":"Ma'amaloli"},
            "fr": {"dashboard":"Tableau de bord", "income":"Revenus", "expenses":"Dépenses", "reports":"Rapports", "settings":"Paramètres", "language":"Langue", "budgets":"Budgets", "goals":"Objectifs", "assets":"Investissements et actifs", "ai":"FOCOST AI", "notifications":"Notifications", "profile":"Profil", "integrations":"Reçus et relevés", "categories":"Catégories", "logout":"Déconnexion", "transactions":"Transactions"},
            "es": {"dashboard":"Panel", "income":"Ingresos", "expenses":"Gastos", "reports":"Informes", "settings":"Configuración", "language":"Idioma", "budgets":"Presupuestos", "goals":"Objetivos", "assets":"Inversiones y activos", "ai":"FOCOST AI", "notifications":"Notificaciones", "profile":"Perfil", "integrations":"Recibos y extractos", "categories":"Categorías", "logout":"Cerrar sesión", "transactions":"Transacciones"},
            "pt": {"dashboard":"Painel", "income":"Receitas", "expenses":"Despesas", "reports":"Relatórios", "settings":"Definições", "language":"Idioma", "budgets":"Orçamentos", "goals":"Objetivos", "assets":"Investimentos e ativos", "ai":"FOCOST AI", "notifications":"Notificações", "profile":"Perfil", "integrations":"Recibos e extratos", "categories":"Categorias", "logout":"Terminar sessão", "transactions":"Transações"},
        }
        return catalogue.get(code, catalogue["en"]).get(key, catalogue["en"].get(key, key))
