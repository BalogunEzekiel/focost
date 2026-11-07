"""Central language catalogue and persisted user language preferences.

Translations are deliberately explicit and deterministic. Unknown keys fall back
 to English so missing translations never produce blank UI labels.
"""
from app.services.settings_service import SettingsService

LANGUAGES = {
    "en": {"name": "English", "native": "English", "dir": "ltr", "speech": "en-NG"},
    "yo": {"name": "Yoruba", "native": "Yorùbá", "dir": "ltr", "speech": "yo-NG"},
    "ha": {"name": "Hausa", "native": "Hausa", "dir": "ltr", "speech": "ha-NG"},
    "fr": {"name": "French", "native": "Français", "dir": "ltr", "speech": "fr-FR"},
    "es": {"name": "Spanish", "native": "Español", "dir": "ltr", "speech": "es-ES"},
    "pt": {"name": "Portuguese", "native": "Português", "dir": "ltr", "speech": "pt-PT"},
}

# Shared labels used by navigation, common forms, status messages and dashboards.
# Extend this catalogue as templates are migrated to focost_t('key').
CATALOGUE = {
"en": {
"dashboard":"Dashboard", "income":"Income", "expenses":"Expenses", "reports":"Reports", "settings":"Settings", "language":"Language", "currency":"Currency", "budgets":"Budgets", "goals":"Goals", "assets":"Investments & assets", "ai":"FOCOST AI", "notifications":"Notifications", "profile":"Profile", "integrations":"Receipts & statements", "categories":"Categories", "logout":"Sign out", "transactions":"Transactions", "search":"Search...", "alerts":"Alerts", "new":"New", "save":"Save changes", "cancel":"Cancel", "close":"Close", "edit":"Edit", "delete":"Delete", "view":"View", "add":"Add new", "update":"Update", "submit":"Submit", "loading":"Loading...", "success":"Success", "error":"Error", "warning":"Warning", "date":"Date", "amount":"Amount", "description":"Description", "status":"Status", "actions":"Actions", "total":"Total", "monthly":"Monthly", "weekly":"Weekly", "daily":"Daily", "this_month":"This month", "all_time":"All time", "no_records":"No records found.", "confirm_delete":"Are you sure you want to delete this item?", "preferences_saved":"Your preferences have been saved.", "language_saved":"Language preference saved.", "voice_listening":"Listening…", "voice_speaking":"Speaking…", "voice_unavailable":"Voice input is not supported by this browser.", "send":"Send", "message":"Message", "email":"Email", "phone":"Phone", "name":"Name", "back":"Back", "next":"Next", "previous":"Previous", "download":"Download", "export":"Export", "print":"Print", "filter":"Filter", "apply":"Apply", "reset":"Reset", "all":"All", "pending":"Pending", "completed":"Completed", "overdue":"Overdue", "active":"Active", "inactive":"Inactive"
},
"yo": {
"dashboard":"Pẹpẹ iṣakoso", "income":"Owó tí wọlé", "expenses":"Ìnáwó", "reports":"Àwọn ìròyìn", "settings":"Ètò", "language":"Èdè", "currency":"Owó ìṣírò", "budgets":"Ètò ìnáwó", "goals":"Àwọn àfojúsùn", "assets":"Ìdókòwò àti ohun-ìní", "ai":"FOCOST AI", "notifications":"Àwọn ìfitónilétí", "profile":"Àkọọ́lẹ̀ ara ẹni", "integrations":"Rísítì àti ìwé banki", "categories":"Àwọn ẹ̀ka", "logout":"Jáde", "transactions":"Àwọn ìṣòwò", "search":"Wá…", "alerts":"Ìkìlọ̀", "new":"Tuntun", "save":"Fi àwọn àyípadà pamọ́", "cancel":"Fagilé", "close":"Pàdé", "edit":"Ṣàtúnṣe", "delete":"Paarẹ́", "view":"Wo", "add":"Fi kún un", "update":"Ṣe àtúnṣe", "submit":"Fọwọ́ sí i", "loading":"Ó ń ṣiṣẹ́…", "success":"Ó ṣàṣeyọrí", "error":"Àṣìṣe", "warning":"Ìkìlọ̀", "date":"Ọjọ́", "amount":"Iye", "description":"Àlàyé", "status":"Ipò", "actions":"Ìgbésẹ̀", "total":"Àpapọ̀", "monthly":"Oṣooṣù", "weekly":"Ọ̀sọ̀ọ̀sẹ̀", "daily":"Ojoojúmọ́", "this_month":"Oṣù yìí", "all_time":"Gbogbo àkókò", "no_records":"A kò rí àkọsílẹ̀ kankan.", "preferences_saved":"A ti fi àwọn ààyò rẹ pamọ́.", "language_saved":"A ti fi èdè tí o yàn pamọ́.", "send":"Fi ránṣẹ́", "message":"Ifiranṣẹ́", "email":"Ímeèlì", "phone":"Fóònù", "name":"Orúkọ", "back":"Padà", "next":"Tókàn", "previous":"Ti ìṣáájú", "download":"Gba sílẹ̀", "export":"Jade síta", "print":"Tẹ̀ jáde", "filter":"Ṣàlẹ̀mọ́", "apply":"Lò ó", "reset":"Tún bẹ̀rẹ̀", "all":"Gbogbo", "pending":"Ń dúró", "completed":"Parí", "overdue":"Ó ti pẹ́", "active":"Ń ṣiṣẹ́", "inactive":"Kò ṣiṣẹ́"
},
"ha": {
"dashboard":"Allon kulawa", "income":"Kuɗin shiga", "expenses":"Kuɗaɗen kashewa", "reports":"Rahotanni", "settings":"Saituna", "language":"Harshe", "currency":"Nau'in kuɗi", "budgets":"Kasafin kuɗi", "goals":"Manufofi", "assets":"Jari da kadarori", "ai":"FOCOST AI", "notifications":"Sanarwa", "profile":"Bayanan mutum", "integrations":"Rasiti da bayanan banki", "categories":"Rukuni", "logout":"Fita", "transactions":"Ma'amaloli", "search":"Bincika…", "alerts":"Faɗakarwa", "new":"Sabo", "save":"Ajiye canje-canje", "cancel":"Soke", "close":"Rufe", "edit":"Gyara", "delete":"Goge", "view":"Duba", "add":"Ƙara", "update":"Sabunta", "submit":"Aika", "loading":"Ana lodawa…", "success":"An yi nasara", "error":"Kuskure", "warning":"Gargaɗi", "date":"Kwanan wata", "amount":"Adadi", "description":"Bayani", "status":"Matsayi", "actions":"Ayyuka", "total":"Jimilla", "monthly":"Na wata", "weekly":"Na mako", "daily":"Na yau da kullum", "this_month":"Wannan watan", "all_time":"Duk lokaci", "no_records":"Ba a sami bayanai ba.", "preferences_saved":"An ajiye zaɓuɓɓukanka.", "language_saved":"An ajiye zaɓin harshe.", "send":"Aika", "message":"Saƙo", "email":"Imel", "phone":"Waya", "name":"Suna", "back":"Baya", "next":"Na gaba", "previous":"Na baya", "download":"Sauke", "export":"Fitarwa", "print":"Buga", "filter":"Tace", "apply":"Aiwatar", "reset":"Sake saita", "all":"Duka", "pending":"Ana jira", "completed":"An kammala", "overdue":"Ya wuce lokaci", "active":"Aiki", "inactive":"Ba ya aiki"
},
"fr": {
"dashboard":"Tableau de bord", "income":"Revenus", "expenses":"Dépenses", "reports":"Rapports", "settings":"Paramètres", "language":"Langue", "currency":"Devise", "budgets":"Budgets", "goals":"Objectifs", "assets":"Investissements et actifs", "ai":"FOCOST AI", "notifications":"Notifications", "profile":"Profil", "integrations":"Reçus et relevés", "categories":"Catégories", "logout":"Déconnexion", "transactions":"Transactions", "search":"Rechercher…", "alerts":"Alertes", "new":"Nouveau", "save":"Enregistrer les modifications", "cancel":"Annuler", "close":"Fermer", "edit":"Modifier", "delete":"Supprimer", "view":"Voir", "add":"Ajouter", "update":"Mettre à jour", "submit":"Soumettre", "loading":"Chargement…", "success":"Succès", "error":"Erreur", "warning":"Avertissement", "date":"Date", "amount":"Montant", "description":"Description", "status":"Statut", "actions":"Actions", "total":"Total", "monthly":"Mensuel", "weekly":"Hebdomadaire", "daily":"Quotidien", "this_month":"Ce mois-ci", "all_time":"Depuis le début", "no_records":"Aucun enregistrement trouvé.", "preferences_saved":"Vos préférences ont été enregistrées.", "language_saved":"La préférence linguistique a été enregistrée.", "send":"Envoyer", "message":"Message", "email":"E-mail", "phone":"Téléphone", "name":"Nom", "back":"Retour", "next":"Suivant", "previous":"Précédent", "download":"Télécharger", "export":"Exporter", "print":"Imprimer", "filter":"Filtrer", "apply":"Appliquer", "reset":"Réinitialiser", "all":"Tout", "pending":"En attente", "completed":"Terminé", "overdue":"En retard", "active":"Actif", "inactive":"Inactif"
},
"es": {
"dashboard":"Panel", "income":"Ingresos", "expenses":"Gastos", "reports":"Informes", "settings":"Configuración", "language":"Idioma", "currency":"Moneda", "budgets":"Presupuestos", "goals":"Objetivos", "assets":"Inversiones y activos", "ai":"FOCOST AI", "notifications":"Notificaciones", "profile":"Perfil", "integrations":"Recibos y extractos", "categories":"Categorías", "logout":"Cerrar sesión", "transactions":"Transacciones", "search":"Buscar…", "alerts":"Alertas", "new":"Nuevo", "save":"Guardar cambios", "cancel":"Cancelar", "close":"Cerrar", "edit":"Editar", "delete":"Eliminar", "view":"Ver", "add":"Añadir", "update":"Actualizar", "submit":"Enviar", "loading":"Cargando…", "success":"Correcto", "error":"Error", "warning":"Advertencia", "date":"Fecha", "amount":"Importe", "description":"Descripción", "status":"Estado", "actions":"Acciones", "total":"Total", "monthly":"Mensual", "weekly":"Semanal", "daily":"Diario", "this_month":"Este mes", "all_time":"Todo el tiempo", "no_records":"No se encontraron registros.", "preferences_saved":"Tus preferencias se han guardado.", "language_saved":"Se ha guardado el idioma preferido.", "send":"Enviar", "message":"Mensaje", "email":"Correo electrónico", "phone":"Teléfono", "name":"Nombre", "back":"Atrás", "next":"Siguiente", "previous":"Anterior", "download":"Descargar", "export":"Exportar", "print":"Imprimir", "filter":"Filtrar", "apply":"Aplicar", "reset":"Restablecer", "all":"Todos", "pending":"Pendiente", "completed":"Completado", "overdue":"Vencido", "active":"Activo", "inactive":"Inactivo"
},
"pt": {
"dashboard":"Painel", "income":"Receitas", "expenses":"Despesas", "reports":"Relatórios", "settings":"Definições", "language":"Idioma", "currency":"Moeda", "budgets":"Orçamentos", "goals":"Objetivos", "assets":"Investimentos e ativos", "ai":"FOCOST AI", "notifications":"Notificações", "profile":"Perfil", "integrations":"Recibos e extratos", "categories":"Categorias", "logout":"Terminar sessão", "transactions":"Transações", "search":"Pesquisar…", "alerts":"Alertas", "new":"Novo", "save":"Guardar alterações", "cancel":"Cancelar", "close":"Fechar", "edit":"Editar", "delete":"Eliminar", "view":"Ver", "add":"Adicionar", "update":"Atualizar", "submit":"Enviar", "loading":"A carregar…", "success":"Sucesso", "error":"Erro", "warning":"Aviso", "date":"Data", "amount":"Valor", "description":"Descrição", "status":"Estado", "actions":"Ações", "total":"Total", "monthly":"Mensal", "weekly":"Semanal", "daily":"Diário", "this_month":"Este mês", "all_time":"Todo o período", "no_records":"Não foram encontrados registos.", "preferences_saved":"As suas preferências foram guardadas.", "language_saved":"A preferência de idioma foi guardada.", "send":"Enviar", "message":"Mensagem", "email":"E-mail", "phone":"Telefone", "name":"Nome", "back":"Voltar", "next":"Seguinte", "previous":"Anterior", "download":"Transferir", "export":"Exportar", "print":"Imprimir", "filter":"Filtrar", "apply":"Aplicar", "reset":"Repor", "all":"Todos", "pending":"Pendente", "completed":"Concluído", "overdue":"Atrasado", "active":"Ativo", "inactive":"Inativo"
}}

class LanguageService:
    @staticmethod
    def available():
        try:
            from app.services.feature_access_service import FeatureAccessService
            policy = FeatureAccessService.policy("multilingual")
            if policy and not policy.enabled:
                return {"en": LANGUAGES["en"]}
            configured = policy.config().get("supported_languages", list(LANGUAGES)) if policy else list(LANGUAGES)
            codes = [code for code in configured if code in LANGUAGES]
            if "en" not in codes:
                codes.insert(0, "en")
            return {code: LANGUAGES[code] for code in codes}
        except Exception:
            return LANGUAGES.copy()

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
        code = str(code or "").strip().lower()
        if code not in LanguageService.available():
            raise ValueError("Unsupported language.")
        prefs = SettingsService.get_preferences(user_id)
        prefs["language"] = code
        SettingsService.update(user_id, prefs)
        return code

    @staticmethod
    def translate(code, key):
        code = code if code in CATALOGUE else "en"
        key = str(key)
        return CATALOGUE.get(code, CATALOGUE["en"]).get(key, CATALOGUE["en"].get(key, key))

    @staticmethod
    def translate_text(code, text):
        """Translate known application-owned strings without rewriting user data.

        Exact matching is intentional: arbitrary user-authored descriptions,
        merchant names, announcement copy and AI responses must not be altered.
        Unmapped strings fall back to their original language.
        """
        code = code if code in CATALOGUE else "en"
        value = str(text or "")
        reverse = {source: key for source, key in TEXT_KEY_MAP.items()}
        key = reverse.get(value.strip())
        if key:
            translated = LanguageService.translate(code, key)
            if value != value.strip():
                return value[:len(value) - len(value.lstrip())] + translated + value[len(value.rstrip()):]
            return translated
        notification_key = NOTIFICATION_TEXT_KEYS.get(value.strip())
        if notification_key:
            return LanguageService.translate(code, notification_key)
        import re
        patterns = (
            (r"^(?P<name>.+?) budget has reached (?P<percentage>\d+(?:\.\d+)?)%\.$", "budget_percentage_message"),
            (r"^You achieved your '(?P<name>.*)' goal\.$", "goal_achieved_message"),
            (r"^Your goal '(?P<name>.*)' is due in (?P<days>\d+) day\(s\)\.$", "goal_due_message"),
            (r"^'(?P<name>.*)' is only (?P<percentage>\d+(?:\.\d+)?)% funded\.$", "goal_behind_message"),
            (r"^(?P<name>.+?) exceeded by (?P<amount>.+)\.$", "budget_exceeded_message"),
            (r"^Current balance is (?P<amount>.+)\.$", "low_balance_message"),
            (r"^(?P<amount>.+?) income received from (?P<source>.+)\.$", "income_added_message"),
            (r"^(?P<amount>.+?) spent on (?P<category>.+)\.$", "expense_recorded_message"),
        )
        for pattern, key in patterns:
            match = re.match(pattern, value.strip())
            if match:
                template = NOTIFICATION_MESSAGE_TEMPLATES.get(code, {}).get(key)
                if template:
                    return template.format(**match.groupdict())
        return text

    @staticmethod
    def speech_locale(code):
        return LANGUAGES.get(code, LANGUAGES["en"])["speech"]

# Exact English text-node -> catalogue-key bridge. This lets the browser localize
# common labels across legacy templates while those templates are progressively
# migrated to explicit data-i18n/focost_t keys. It intentionally only matches
# complete text nodes; it never rewrites arbitrary prose or user-generated data.
TEXT_KEY_MAP = {
    "Dashboard": "dashboard", "Income": "income", "Expenses": "expenses",
    "Reports": "reports", "Settings": "settings", "Language": "language",
    "Currency": "currency", "Budgets": "budgets", "Goals": "goals",
    "Investments & assets": "assets", "FOCOST AI": "ai",
    "Notifications": "notifications", "Profile": "profile",
    "Transactions": "transactions", "Search...": "search", "Alerts": "alerts",
    "New": "new", "Save changes": "save", "Cancel": "cancel",
    "Close": "close", "Edit": "edit", "Delete": "delete", "View": "view",
    "Add new": "add", "Update": "update", "Submit": "submit",
    "Loading...": "loading", "Success": "success", "Error": "error",
    "Warning": "warning", "Date": "date", "Amount": "amount",
    "Description": "description", "Status": "status", "Actions": "actions",
    "Total": "total", "Monthly": "monthly", "Weekly": "weekly",
    "Daily": "daily", "This month": "this_month", "All time": "all_time",
    "No records found.": "no_records", "Send": "send", "Message": "message",
    "Email": "email", "Phone": "phone", "Name": "name", "Back": "back",
    "Next": "next", "Previous": "previous", "Download": "download",
    "Export": "export", "Print": "print", "Filter": "filter",
    "Apply": "apply", "Reset": "reset", "All": "all", "Pending": "pending",
    "Completed": "completed", "Overdue": "overdue", "Active": "active",
    "Inactive": "inactive",
}

# Additional shared finance vocabulary used across dashboard, ledger, budgets,
# goals, investments and reports. Keep keys aligned across all six locales.
_CROSS_MODULE_TRANSLATIONS = {
    "en": {
        "total_income": "Total Income", "total_expenses": "Total Expenses", "net_savings": "Net Savings",
        "current_balance": "Current Balance", "financial_health": "Financial Health", "financial_position": "Financial Position",
        "total_budget": "Total Budget", "budget_used": "Budget Used", "spent": "Spent", "remaining": "Remaining",
        "target": "Target", "saved": "Saved", "contribution": "Contribution", "contributions": "Contributions",
        "investment": "Investment", "investments": "Investments", "current_value": "Current Value",
        "cost_basis": "Cost Basis", "gain_loss": "Gain / Loss", "net_worth": "Net Worth",
        "period": "Period", "category": "Category", "merchant": "Merchant", "payment_method": "Payment Method",
        "recurring": "Recurring", "one_time": "One-time", "forecast": "Forecast", "monthly_forecast": "Monthly Forecast",
        "income_breakdown": "Income Breakdown", "expense_breakdown": "Expense Breakdown", "recent_transactions": "Recent Transactions",
        "view_all": "View All", "no_data": "No data available", "start_date": "Start Date", "end_date": "End Date",
        "original_amount": "Original Amount", "original_currency": "Original Currency", "display_currency": "Display Currency",
        "exchange_rate": "Exchange Rate", "rate_date": "Rate Date", "converted_amount": "Converted Amount",
        "conversion_unavailable": "Currency conversion is currently unavailable.", "historical_rate": "Historical exchange rate",
        "account_balance": "Account Balance", "transaction_date": "Transaction Date", "financial_summary": "Financial Summary",
    },
    "yo": {
        "total_income": "Àpapọ̀ Owó Tí Wọlé", "total_expenses": "Àpapọ̀ Ìnáwó", "net_savings": "Ìfowópamọ́ Apapọ̀",
        "current_balance": "Ìwọ̀ntúnwọ̀nsì Lọ́wọ́lọ́wọ́", "financial_health": "Ìlera Ọ̀rọ̀ Ajé", "financial_position": "Ipò Ọ̀rọ̀ Ajé",
        "total_budget": "Àpapọ̀ Ètò Ìnáwó", "budget_used": "Ètò Ìnáwó Tí A Lò", "spent": "Èyí Tí A Ná", "remaining": "Èyí Tó Kù",
        "target": "Àfojúsùn", "saved": "Èyí Tí A Fipamọ́", "contribution": "Ìdáwọ́lé", "contributions": "Àwọn Ìdáwọ́lé",
        "investment": "Ìdókòwò", "investments": "Àwọn Ìdókòwò", "current_value": "Iye Lọ́wọ́lọ́wọ́",
        "cost_basis": "Iye Owó Ìbẹ̀rẹ̀", "gain_loss": "Èrè / Ìpàdánù", "net_worth": "Ọlá-ìní Apapọ̀",
        "period": "Àkókò", "category": "Ẹ̀ka", "merchant": "Oníṣòwò", "payment_method": "Ọ̀nà Ìsanwó",
        "recurring": "Tí Ó Ń Ṣẹlẹ̀ Léraléra", "one_time": "Ẹ̀ẹ̀kan", "forecast": "Àsọtẹ́lẹ̀", "monthly_forecast": "Àsọtẹ́lẹ̀ Oṣooṣù",
        "income_breakdown": "Ìpín Owó Tí Wọlé", "expense_breakdown": "Ìpín Ìnáwó", "recent_transactions": "Àwọn Ìṣòwò Tó Ṣẹ̀ṣẹ̀",
        "view_all": "Wo Gbogbo Rẹ̀", "no_data": "Kò sí dátà", "start_date": "Ọjọ́ Ìbẹ̀rẹ̀", "end_date": "Ọjọ́ Òpin",
        "original_amount": "Iye Àtilẹ̀wá", "original_currency": "Owó Àtilẹ̀wá", "display_currency": "Owó Ìfihàn",
        "exchange_rate": "Oṣuwọn Pàṣípààrọ̀", "rate_date": "Ọjọ́ Oṣuwọn", "converted_amount": "Iye Tí A Yí Padà",
        "conversion_unavailable": "Pàṣípààrọ̀ owó kò sí lọ́wọ́lọ́wọ́.", "historical_rate": "Oṣuwọn pàṣípààrọ̀ ìtàn",
        "account_balance": "Ìwọ̀ntúnwọ̀nsì Àkọọ́lẹ̀", "transaction_date": "Ọjọ́ Ìṣòwò", "financial_summary": "Àkótán Ọ̀rọ̀ Ajé",
    },
    "ha": {
        "total_income": "Jimillar Kuɗin Shiga", "total_expenses": "Jimillar Kuɗaɗen Kashewa", "net_savings": "Adadin Kuɗin Ajiya",
        "current_balance": "Ma'aunin Yanzu", "financial_health": "Lafiyar Kuɗi", "financial_position": "Matsayin Kuɗi",
        "total_budget": "Jimillar Kasafin Kuɗi", "budget_used": "Kasafin da Aka Yi Amfani da Shi", "spent": "An Kashe", "remaining": "Ya Rage",
        "target": "Manufa", "saved": "An Ajiye", "contribution": "Gudummawa", "contributions": "Gudummawowi",
        "investment": "Zuba Jari", "investments": "Zuba Jari", "current_value": "Darajar Yanzu",
        "cost_basis": "Asalin Kuɗin Saye", "gain_loss": "Riba / Asara", "net_worth": "Jimillar Dukiya",
        "period": "Lokaci", "category": "Rukuni", "merchant": "Dan Kasuwa", "payment_method": "Hanyar Biyan Kuɗi",
        "recurring": "Mai Maimaituwa", "one_time": "Sau ɗaya", "forecast": "Hasashe", "monthly_forecast": "Hasashen Wata",
        "income_breakdown": "Rarraba Kuɗin Shiga", "expense_breakdown": "Rarraba Kuɗaɗen Kashewa", "recent_transactions": "Ma'amaloli na Kwanan Nan",
        "view_all": "Duba Duka", "no_data": "Babu bayanai", "start_date": "Ranar Farawa", "end_date": "Ranar Ƙarshe",
        "original_amount": "Adadin Asali", "original_currency": "Nau'in Kuɗin Asali", "display_currency": "Nau'in Kuɗin Nuni",
        "exchange_rate": "Farashin Musayar Kuɗi", "rate_date": "Ranar Farashi", "converted_amount": "Adadin da Aka Musanya",
        "conversion_unavailable": "Ba a samun musayar kuɗi a yanzu.", "historical_rate": "Farashin musayar kuɗi na baya",
        "account_balance": "Ma'aunin Asusun", "transaction_date": "Ranar Ma'amala", "financial_summary": "Taƙaitaccen Kuɗi",
    },
    "fr": {
        "total_income": "Revenu total", "total_expenses": "Dépenses totales", "net_savings": "Épargne nette",
        "current_balance": "Solde actuel", "financial_health": "Santé financière", "financial_position": "Situation financière",
        "total_budget": "Budget total", "budget_used": "Budget utilisé", "spent": "Dépensé", "remaining": "Restant",
        "target": "Objectif", "saved": "Épargné", "contribution": "Contribution", "contributions": "Contributions",
        "investment": "Investissement", "investments": "Investissements", "current_value": "Valeur actuelle",
        "cost_basis": "Coût de revient", "gain_loss": "Gain / Perte", "net_worth": "Patrimoine net",
        "period": "Période", "category": "Catégorie", "merchant": "Commerçant", "payment_method": "Mode de paiement",
        "recurring": "Récurrent", "one_time": "Ponctuel", "forecast": "Prévision", "monthly_forecast": "Prévision mensuelle",
        "income_breakdown": "Répartition des revenus", "expense_breakdown": "Répartition des dépenses", "recent_transactions": "Transactions récentes",
        "view_all": "Tout afficher", "no_data": "Aucune donnée disponible", "start_date": "Date de début", "end_date": "Date de fin",
        "original_amount": "Montant d'origine", "original_currency": "Devise d'origine", "display_currency": "Devise d'affichage",
        "exchange_rate": "Taux de change", "rate_date": "Date du taux", "converted_amount": "Montant converti",
        "conversion_unavailable": "La conversion de devises est actuellement indisponible.", "historical_rate": "Taux de change historique",
        "account_balance": "Solde du compte", "transaction_date": "Date de transaction", "financial_summary": "Résumé financier",
    },
    "es": {
        "total_income": "Ingresos totales", "total_expenses": "Gastos totales", "net_savings": "Ahorro neto",
        "current_balance": "Saldo actual", "financial_health": "Salud financiera", "financial_position": "Situación financiera",
        "total_budget": "Presupuesto total", "budget_used": "Presupuesto utilizado", "spent": "Gastado", "remaining": "Restante",
        "target": "Objetivo", "saved": "Ahorrado", "contribution": "Aportación", "contributions": "Aportaciones",
        "investment": "Inversión", "investments": "Inversiones", "current_value": "Valor actual",
        "cost_basis": "Coste de adquisición", "gain_loss": "Ganancia / Pérdida", "net_worth": "Patrimonio neto",
        "period": "Período", "category": "Categoría", "merchant": "Comerciante", "payment_method": "Método de pago",
        "recurring": "Recurrente", "one_time": "Una vez", "forecast": "Previsión", "monthly_forecast": "Previsión mensual",
        "income_breakdown": "Desglose de ingresos", "expense_breakdown": "Desglose de gastos", "recent_transactions": "Transacciones recientes",
        "view_all": "Ver todo", "no_data": "No hay datos disponibles", "start_date": "Fecha de inicio", "end_date": "Fecha de finalización",
        "original_amount": "Importe original", "original_currency": "Moneda original", "display_currency": "Moneda de visualización",
        "exchange_rate": "Tipo de cambio", "rate_date": "Fecha del tipo", "converted_amount": "Importe convertido",
        "conversion_unavailable": "La conversión de moneda no está disponible actualmente.", "historical_rate": "Tipo de cambio histórico",
        "account_balance": "Saldo de la cuenta", "transaction_date": "Fecha de transacción", "financial_summary": "Resumen financiero",
    },
    "pt": {
        "total_income": "Rendimento total", "total_expenses": "Despesas totais", "net_savings": "Poupança líquida",
        "current_balance": "Saldo atual", "financial_health": "Saúde financeira", "financial_position": "Posição financeira",
        "total_budget": "Orçamento total", "budget_used": "Orçamento utilizado", "spent": "Gasto", "remaining": "Restante",
        "target": "Meta", "saved": "Poupado", "contribution": "Contribuição", "contributions": "Contribuições",
        "investment": "Investimento", "investments": "Investimentos", "current_value": "Valor atual",
        "cost_basis": "Custo de aquisição", "gain_loss": "Ganho / Perda", "net_worth": "Património líquido",
        "period": "Período", "category": "Categoria", "merchant": "Comerciante", "payment_method": "Método de pagamento",
        "recurring": "Recorrente", "one_time": "Único", "forecast": "Previsão", "monthly_forecast": "Previsão mensal",
        "income_breakdown": "Detalhamento dos rendimentos", "expense_breakdown": "Detalhamento das despesas", "recent_transactions": "Transações recentes",
        "view_all": "Ver tudo", "no_data": "Não há dados disponíveis", "start_date": "Data de início", "end_date": "Data de fim",
        "original_amount": "Valor original", "original_currency": "Moeda original", "display_currency": "Moeda de apresentação",
        "exchange_rate": "Taxa de câmbio", "rate_date": "Data da taxa", "converted_amount": "Valor convertido",
        "conversion_unavailable": "A conversão de moeda não está disponível no momento.", "historical_rate": "Taxa de câmbio histórica",
        "account_balance": "Saldo da conta", "transaction_date": "Data da transação", "financial_summary": "Resumo financeiro",
    },
}

_NOTIFICATION_TRANSLATIONS = {
    "en": {"budget_exceeded_title": "Budget Exceeded", "budget_warning_title": "Budget Warning", "budget_critical_title": "Budget Critical", "goal_achieved_title": "Goal Achieved", "goal_due_title": "Goal Due", "goal_behind_title": "Goal Behind Schedule", "low_balance_title": "Low Balance", "payment_success_title": "Payment Successful", "subscription_expiring_title": "Subscription Expiring"},
    "yo": {"budget_exceeded_title": "A ti Isuna ti kọja", "budget_warning_title": "Ikilọ Isuna", "budget_critical_title": "Isuna Nira", "goal_achieved_title": "A ti ṣaṣeyọri Àfojúsùn", "goal_due_title": "Àfojúsùn ti tó", "goal_behind_title": "Àfojúsùn ti pẹ́", "low_balance_title": "Owó tó kù díẹ̀", "payment_success_title": "Ìsanwó ṣàṣeyọrí", "subscription_expiring_title": "Ìforúkọsílẹ̀ ń parí"},
    "ha": {"budget_exceeded_title": "An Wuce Kasafin Kuɗi", "budget_warning_title": "Gargadin Kasafin Kuɗi", "budget_critical_title": "Matsalar Kasafin Kuɗi", "goal_achieved_title": "An Cimma Manufa", "goal_due_title": "Lokacin Manufa Ya Yi", "goal_behind_title": "Manufa Ta Koma Baya", "low_balance_title": "Ragowar Kuɗi Ya Yi Kaɗan", "payment_success_title": "An Yi Biyan Kuɗi Cikin Nasara", "subscription_expiring_title": "Biyan Kuɗin Shiga Zai Ƙare"},
    "fr": {"budget_exceeded_title": "Budget dépassé", "budget_warning_title": "Alerte budget", "budget_critical_title": "Budget critique", "goal_achieved_title": "Objectif atteint", "goal_due_title": "Échéance de l'objectif", "goal_behind_title": "Objectif en retard", "low_balance_title": "Solde faible", "payment_success_title": "Paiement réussi", "subscription_expiring_title": "Abonnement bientôt expiré"},
    "es": {"budget_exceeded_title": "Presupuesto excedido", "budget_warning_title": "Aviso de presupuesto", "budget_critical_title": "Presupuesto crítico", "goal_achieved_title": "Objetivo alcanzado", "goal_due_title": "Objetivo pendiente", "goal_behind_title": "Objetivo retrasado", "low_balance_title": "Saldo bajo", "payment_success_title": "Pago realizado", "subscription_expiring_title": "Suscripción próxima a vencer"},
    "pt": {"budget_exceeded_title": "Orçamento excedido", "budget_warning_title": "Aviso de orçamento", "budget_critical_title": "Orçamento crítico", "goal_achieved_title": "Meta alcançada", "goal_due_title": "Prazo da meta", "goal_behind_title": "Meta atrasada", "low_balance_title": "Saldo baixo", "payment_success_title": "Pagamento concluído", "subscription_expiring_title": "Subscrição prestes a expirar"},
}
for _locale, _entries in _NOTIFICATION_TRANSLATIONS.items():
    CATALOGUE[_locale].update(_entries)


_REPORT_TRANSLATIONS = {
    "en": {"report_title":"FOCOST — FINANCIAL REPORT","generated":"Generated","period":"Period","category":"Category","all_time":"All time","present":"Present","all_categories":"All Categories","current_financial_position":"CURRENT FINANCIAL POSITION","total_cash_income":"Total cash income","less_cash_expenses":"Less: total cash expenses","available_savings_balance":"Available / savings balance","cumulative_goal_contributions":"Add: cumulative goal contributions","current_investment_value":"Add: current investment value","estimated_net_worth":"Estimated net worth","note":"Note","period_total_income":"Period Total Income","period_total_expenses":"Period Total Expenses","period_net_savings":"Period Net Savings","period_savings_rate":"Period Savings Rate (%)","transactions":"Transactions","income_by_category":"Income by Category","expense_by_category":"Expense by Category","report_summary":"Report Summary","financial_position":"Financial Position","statement_financial_position":"FOCOST — STATEMENT OF FINANCIAL POSITION","current_position":"Current position","component":"Component","amount":"Amount","accounting_context":"Accounting context","transaction_detail":"Transaction Detail","type":"Type","date":"Date","source_merchant":"Source / Merchant","original_currency":"Original Currency","display_amount":"Display Amount","recurring":"Recurring","notes":"Notes","income":"Income","expense":"Expense","no_data":"No data"},
    "yo": {"report_title":"FOCOST — ÌRÒYÌN Ọ̀RỌ̀ AJÉ","generated":"Ọjọ́ Ìṣẹ̀dá","period":"Àkókò","category":"Ẹ̀ka","all_time":"Gbogbo àkókò","present":"Lọ́wọ́lọ́wọ́","all_categories":"Gbogbo Ẹ̀ka","current_financial_position":"IPÒ Ọ̀RỌ̀ AJÉ LỌ́WỌ́LỌ́WỌ́","total_cash_income":"Àpapọ̀ owó tí wọlé","less_cash_expenses":"Yọ: gbogbo ìnáwó","available_savings_balance":"Ìwọ̀ntúnwọ̀nsì / ìfowópamọ́ tó wà","cumulative_goal_contributions":"Fi kún: gbogbo ìdáwọ́lé àfojúsùn","current_investment_value":"Fi kún: iye ìdókòwò lọ́wọ́lọ́wọ́","estimated_net_worth":"Ọlá-ìní apapọ̀ tí a fojú díwọ̀n","note":"Àkíyèsí","period_total_income":"Àpapọ̀ owó tí wọlé ní àkókò yìí","period_total_expenses":"Àpapọ̀ ìnáwó ní àkókò yìí","period_net_savings":"Ìfowópamọ́ apapọ̀ ní àkókò yìí","period_savings_rate":"Ìpín ìfowópamọ́ (%)","transactions":"Àwọn ìṣòwò","income_by_category":"Owó tí wọlé nípa ẹ̀ka","expense_by_category":"Ìnáwó nípa ẹ̀ka","report_summary":"Àkótán ìròyìn","financial_position":"Ipò ọ̀rọ̀ ajé","statement_financial_position":"FOCOST — ÀKỌSÍLẸ̀ IPÒ Ọ̀RỌ̀ AJÉ","current_position":"Ipò lọ́wọ́lọ́wọ́","component":"Apá","amount":"Iye","accounting_context":"Àlàyé ìṣirò","transaction_detail":"Àlàyé ìṣòwò","type":"Irú","date":"Ọjọ́","source_merchant":"Orísun / Oníṣòwò","original_currency":"Owó àtilẹ̀wá","display_amount":"Iye ìfihàn","recurring":"Léraléra","notes":"Àwọn àkíyèsí","income":"Owó tí wọlé","expense":"Ìnáwó","no_data":"Kò sí dátà"},
    "ha": {"report_title":"FOCOST — RAHOTON KUƊI","generated":"An Ƙirƙira","period":"Lokaci","category":"Rukuni","all_time":"Duk lokaci","present":"Yanzu","all_categories":"Duk Rukuni","current_financial_position":"MATSAYIN KUƊI NA YANZU","total_cash_income":"Jimillar kuɗin shiga","less_cash_expenses":"Rage: jimillar kuɗin fita","available_savings_balance":"Ma'aunin kuɗin da ake da shi / ajiya","cumulative_goal_contributions":"Ƙara: jimillar gudummawar manufa","current_investment_value":"Ƙara: darajar zuba jari ta yanzu","estimated_net_worth":"Ƙiyasin dukiya gaba ɗaya","note":"Bayani","period_total_income":"Jimillar kuɗin shiga na lokaci","period_total_expenses":"Jimillar kuɗin kashewa na lokaci","period_net_savings":"Adadin ajiyar lokaci","period_savings_rate":"Kason ajiyar kuɗi (%)","transactions":"Ma'amaloli","income_by_category":"Kuɗin shiga bisa rukuni","expense_by_category":"Kuɗin kashewa bisa rukuni","report_summary":"Taƙaitaccen rahoto","financial_position":"Matsayin kuɗi","statement_financial_position":"FOCOST — BAYANIN MATSAYIN KUƊI","current_position":"Matsayin yanzu","component":"Abu","amount":"Adadi","accounting_context":"Bayanin lissafi","transaction_detail":"Cikakken ma'amala","type":"Nau'i","date":"Rana","source_merchant":"Tushe / Dan kasuwa","original_currency":"Nau'in kuɗin asali","display_amount":"Adadin nuni","recurring":"Mai maimaituwa","notes":"Bayanan kula","income":"Kuɗin shiga","expense":"Kuɗin kashewa","no_data":"Babu bayanai"},
    "fr": {"report_title":"FOCOST — RAPPORT FINANCIER","generated":"Généré le","period":"Période","category":"Catégorie","all_time":"Toute la période","present":"Présent","all_categories":"Toutes les catégories","current_financial_position":"SITUATION FINANCIÈRE ACTUELLE","total_cash_income":"Total des revenus encaissés","less_cash_expenses":"Moins : dépenses totales","available_savings_balance":"Solde disponible / épargne","cumulative_goal_contributions":"Ajouter : contributions cumulées aux objectifs","current_investment_value":"Ajouter : valeur actuelle des investissements","estimated_net_worth":"Patrimoine net estimé","note":"Remarque","period_total_income":"Revenus totaux de la période","period_total_expenses":"Dépenses totales de la période","period_net_savings":"Épargne nette de la période","period_savings_rate":"Taux d'épargne (%)","transactions":"Transactions","income_by_category":"Revenus par catégorie","expense_by_category":"Dépenses par catégorie","report_summary":"Résumé du rapport","financial_position":"Situation financière","statement_financial_position":"FOCOST — ÉTAT DE LA SITUATION FINANCIÈRE","current_position":"Situation actuelle","component":"Élément","amount":"Montant","accounting_context":"Contexte comptable","transaction_detail":"Détail des transactions","type":"Type","date":"Date","source_merchant":"Source / Marchand","original_currency":"Devise d'origine","display_amount":"Montant affiché","recurring":"Récurrent","notes":"Notes","income":"Revenu","expense":"Dépense","no_data":"Aucune donnée"},
    "es": {"report_title":"FOCOST — INFORME FINANCIERO","generated":"Generado","period":"Período","category":"Categoría","all_time":"Todo el período","present":"Actualidad","all_categories":"Todas las categorías","current_financial_position":"SITUACIÓN FINANCIERA ACTUAL","total_cash_income":"Ingresos totales en efectivo","less_cash_expenses":"Menos: gastos totales","available_savings_balance":"Saldo disponible / ahorro","cumulative_goal_contributions":"Añadir: aportaciones acumuladas a objetivos","current_investment_value":"Añadir: valor actual de inversiones","estimated_net_worth":"Patrimonio neto estimado","note":"Nota","period_total_income":"Ingresos totales del período","period_total_expenses":"Gastos totales del período","period_net_savings":"Ahorro neto del período","period_savings_rate":"Tasa de ahorro (%)","transactions":"Transacciones","income_by_category":"Ingresos por categoría","expense_by_category":"Gastos por categoría","report_summary":"Resumen del informe","financial_position":"Situación financiera","statement_financial_position":"FOCOST — ESTADO DE SITUACIÓN FINANCIERA","current_position":"Situación actual","component":"Componente","amount":"Importe","accounting_context":"Contexto contable","transaction_detail":"Detalle de transacciones","type":"Tipo","date":"Fecha","source_merchant":"Origen / Comerciante","original_currency":"Moneda original","display_amount":"Importe mostrado","recurring":"Recurrente","notes":"Notas","income":"Ingreso","expense":"Gasto","no_data":"Sin datos"},
    "pt": {"report_title":"FOCOST — RELATÓRIO FINANCEIRO","generated":"Gerado em","period":"Período","category":"Categoria","all_time":"Todo o período","present":"Atual","all_categories":"Todas as categorias","current_financial_position":"POSIÇÃO FINANCEIRA ATUAL","total_cash_income":"Total de receitas em dinheiro","less_cash_expenses":"Menos: despesas totais","available_savings_balance":"Saldo disponível / poupança","cumulative_goal_contributions":"Adicionar: contribuições acumuladas para metas","current_investment_value":"Adicionar: valor atual dos investimentos","estimated_net_worth":"Património líquido estimado","note":"Nota","period_total_income":"Receitas totais do período","period_total_expenses":"Despesas totais do período","period_net_savings":"Poupança líquida do período","period_savings_rate":"Taxa de poupança (%)","transactions":"Transações","income_by_category":"Receitas por categoria","expense_by_category":"Despesas por categoria","report_summary":"Resumo do relatório","financial_position":"Posição financeira","statement_financial_position":"FOCOST — DEMONSTRAÇÃO DA POSIÇÃO FINANCEIRA","current_position":"Posição atual","component":"Componente","amount":"Valor","accounting_context":"Contexto contabilístico","transaction_detail":"Detalhe das transações","type":"Tipo","date":"Data","source_merchant":"Origem / Comerciante","original_currency":"Moeda original","display_amount":"Valor apresentado","recurring":"Recorrente","notes":"Notas","income":"Receita","expense":"Despesa","no_data":"Sem dados"},
}
for _locale, _entries in _REPORT_TRANSLATIONS.items():
    CATALOGUE[_locale].update(_entries)


_AI_ROUTE_TRANSLATIONS = {
    "en": {"ai_normal_users_only":"FOCOST AI is available only to normal users.", "ai_message_limit":"Please keep your FOCOST AI message within 4,000 characters.", "ai_enter_message":"Please enter a message.", "ai_currency_unavailable":"I can't prepare an accurate financial answer in your selected display currency because a required exchange rate is unavailable. Please try again later or temporarily select the original transaction currency."},
    "yo": {"ai_normal_users_only":"FOCOST AI wà fún àwọn olùlò déédéé nìkan.", "ai_message_limit":"Jọ̀wọ́ jẹ́ kí ìfiranṣẹ́ FOCOST AI rẹ má ju lẹ́tà 4,000 lọ.", "ai_enter_message":"Jọ̀wọ́ kọ ìfiranṣẹ́ kan.", "ai_currency_unavailable":"Mi ò lè pèsè ìdáhùn ọ̀rọ̀ ajé tó péye ní owó ìfihàn tí o yàn nítorí oṣuwọn pàṣípààrọ̀ kan kò sí. Jọ̀wọ́ tún gbìyànjú lẹ́yìn náà tàbí yan owó ìṣòwò àtilẹ̀wá fún ìgbà díẹ̀."},
    "ha": {"ai_normal_users_only":"FOCOST AI yana samuwa ga masu amfani na yau da kullum kawai.", "ai_message_limit":"Da fatan za a takaita saƙon FOCOST AI zuwa haruffa 4,000.", "ai_enter_message":"Da fatan za a shigar da saƙo.", "ai_currency_unavailable":"Ba zan iya ba da ingantacciyar amsar kuɗi a kuɗin nunin da kuka zaɓa ba saboda ba a samun farashin musaya da ake buƙata. A sake gwadawa daga baya ko a zaɓi kuɗin asalin ma'amala na ɗan lokaci."},
    "fr": {"ai_normal_users_only":"FOCOST AI est réservé aux utilisateurs standard.", "ai_message_limit":"Veuillez limiter votre message FOCOST AI à 4 000 caractères.", "ai_enter_message":"Veuillez saisir un message.", "ai_currency_unavailable":"Je ne peux pas fournir une réponse financière fiable dans la devise d'affichage choisie, car un taux de change nécessaire est indisponible. Réessayez plus tard ou sélectionnez temporairement la devise d'origine."},
    "es": {"ai_normal_users_only":"FOCOST AI solo está disponible para usuarios normales.", "ai_message_limit":"Limita tu mensaje de FOCOST AI a 4.000 caracteres.", "ai_enter_message":"Introduce un mensaje.", "ai_currency_unavailable":"No puedo preparar una respuesta financiera precisa en la moneda de visualización seleccionada porque falta un tipo de cambio necesario. Inténtalo más tarde o selecciona temporalmente la moneda original de la transacción."},
    "pt": {"ai_normal_users_only":"O FOCOST AI está disponível apenas para utilizadores comuns.", "ai_message_limit":"Limite a sua mensagem do FOCOST AI a 4.000 caracteres.", "ai_enter_message":"Introduza uma mensagem.", "ai_currency_unavailable":"Não consigo preparar uma resposta financeira precisa na moeda de apresentação selecionada porque falta uma taxa de câmbio necessária. Tente novamente mais tarde ou selecione temporariamente a moeda original da transação."},
}
for _locale, _entries in _AI_ROUTE_TRANSLATIONS.items():
    CATALOGUE[_locale].update(_entries)



_REPORT_EXTRA_TRANSLATIONS = {
    "en": {"savings_rate_label":"Savings Rate", "yes":"Yes", "no":"No", "financial_position_note":"Goal contributions are designated savings already deducted from available cash; investment value is the current carrying value of active investments.", "financial_position_explanation":"Available / savings balance = total cash income − total cash expenses. Net worth = available / savings balance + cumulative goal contributions + current investment value. Goal contributions are designated savings already deducted from available cash and are therefore added back once only. Investment valuation gains/losses affect the carrying value of investments and do not increase or reduce spendable cash until realized."},
    "yo": {"savings_rate_label":"Ìpín ìfowópamọ́", "yes":"Bẹ́ẹ̀ni", "no":"Rárá", "financial_position_note":"Àwọn ìdáwọ́lé àfojúsùn jẹ́ ìfowópamọ́ tí a ti yọ kúrò nínú owó tó wà; iye ìdókòwò ni iye ìṣirò lọ́wọ́lọ́wọ́ ti àwọn ìdókòwò tó ń ṣiṣẹ́.", "financial_position_explanation":"Ìwọ̀ntúnwọ̀nsì / ìfowópamọ́ tó wà = gbogbo owó tí wọlé − gbogbo ìnáwó. Ọlá-ìní apapọ̀ = ìwọ̀ntúnwọ̀nsì tó wà + gbogbo ìdáwọ́lé àfojúsùn + iye ìdókòwò lọ́wọ́lọ́wọ́. A fi ìdáwọ́lé àfojúsùn kún un lẹ́ẹ̀kan ṣoṣo nítorí a ti yọ wọn kúrò nínú owó tó wà. Èrè tàbí ìpàdánù iye ìdókòwò kò yí owó tí a lè ná padà títí tí a ó fi rí owó náà gẹ́gẹ́ bí owó gidi."},
    "ha": {"savings_rate_label":"Kason Ajiya", "yes":"Eh", "no":"A'a", "financial_position_note":"Gudummawar manufa ajiyar kuɗi ce da aka riga aka cire daga kuɗin da ake da shi; darajar zuba jari ita ce darajar kadarorin zuba jari masu aiki a yanzu.", "financial_position_explanation":"Ma'aunin kuɗin da ake da shi / ajiya = jimillar kuɗin shiga − jimillar kuɗin fita. Dukiya gaba ɗaya = kuɗin da ake da shi + gudummawar manufa da aka tara + darajar zuba jari ta yanzu. Ana ƙara gudummawar manufa sau ɗaya kawai saboda an riga an cire su daga kuɗin da ake da shi. Canjin darajar zuba jari ba ya ƙara ko rage kuɗin da za a iya kashewa har sai an sayar da jarin."},
    "fr": {"savings_rate_label":"Taux d'épargne", "yes":"Oui", "no":"Non", "financial_position_note":"Les contributions aux objectifs sont une épargne déjà déduite de la trésorerie disponible ; la valeur des investissements correspond à leur valeur comptable actuelle.", "financial_position_explanation":"Solde disponible / épargne = revenus encaissés − dépenses décaissées. Patrimoine net = solde disponible + contributions cumulées aux objectifs + valeur actuelle des investissements. Les contributions aux objectifs ne sont ajoutées qu'une seule fois, car elles ont déjà été déduites de la trésorerie disponible. Les variations de valeur des investissements ne modifient pas la trésorerie disponible tant qu'elles ne sont pas réalisées."},
    "es": {"savings_rate_label":"Tasa de ahorro", "yes":"Sí", "no":"No", "financial_position_note":"Las aportaciones a objetivos son ahorro ya descontado del efectivo disponible; el valor de inversión es el valor contable actual de las inversiones activas.", "financial_position_explanation":"Saldo disponible / ahorro = ingresos en efectivo − gastos en efectivo. Patrimonio neto = saldo disponible + aportaciones acumuladas a objetivos + valor actual de inversiones. Las aportaciones a objetivos se suman una sola vez porque ya se descontaron del efectivo disponible. Las variaciones de valoración de inversiones no modifican el efectivo disponible hasta que se realizan."},
    "pt": {"savings_rate_label":"Taxa de poupança", "yes":"Sim", "no":"Não", "financial_position_note":"As contribuições para metas são poupanças já deduzidas do dinheiro disponível; o valor do investimento é o valor contabilístico atual dos investimentos ativos.", "financial_position_explanation":"Saldo disponível / poupança = receitas em dinheiro − despesas em dinheiro. Património líquido = saldo disponível + contribuições acumuladas para metas + valor atual dos investimentos. As contribuições para metas são adicionadas apenas uma vez, pois já foram deduzidas do dinheiro disponível. As variações de avaliação dos investimentos não alteram o dinheiro disponível até serem realizadas."},
}
for _locale, _entries in _REPORT_EXTRA_TRANSLATIONS.items():
    CATALOGUE[_locale].update(_entries)


_NOTIFICATION_MORE_TITLES = {
    "en": {"income_added_title":"Income Added", "expense_recorded_title":"Expense Recorded", "bill_due_title":"Bill Due", "ai_insight_title":"FOCOST AI Insight"},
    "yo": {"income_added_title":"A Ti Fi Owó Tí Wọlé Kún", "expense_recorded_title":"A Kọ Ìnáwó Sílẹ̀", "bill_due_title":"Owó Gbọdọ̀ San", "ai_insight_title":"Ìmọ̀ràn FOCOST AI"},
    "ha": {"income_added_title":"An Ƙara Kuɗin Shiga", "expense_recorded_title":"An Yi Rikodin Kuɗin Kashewa", "bill_due_title":"Lokacin Biyan Kuɗi", "ai_insight_title":"Shawarar FOCOST AI"},
    "fr": {"income_added_title":"Revenu ajouté", "expense_recorded_title":"Dépense enregistrée", "bill_due_title":"Facture à payer", "ai_insight_title":"Conseil FOCOST AI"},
    "es": {"income_added_title":"Ingreso añadido", "expense_recorded_title":"Gasto registrado", "bill_due_title":"Factura pendiente", "ai_insight_title":"Información de FOCOST AI"},
    "pt": {"income_added_title":"Receita adicionada", "expense_recorded_title":"Despesa registada", "bill_due_title":"Fatura a pagar", "ai_insight_title":"Sugestão do FOCOST AI"},
}
for _locale, _entries in _NOTIFICATION_MORE_TITLES.items():
    CATALOGUE[_locale].update(_entries)

NOTIFICATION_MESSAGE_TEMPLATES = {
    "en": {"budget_percentage_message": "{name} budget has reached {percentage}%.", "goal_achieved_message": "You achieved your '{name}' goal.", "goal_due_message": "Your goal '{name}' is due in {days} day(s).", "goal_behind_message": "'{name}' is only {percentage}% funded.", "budget_exceeded_message": "{name} exceeded by {amount}.", "low_balance_message": "Current balance is {amount}.", "income_added_message": "{amount} income received from {source}.", "expense_recorded_message": "{amount} spent on {category}."},
    "yo": {"budget_percentage_message": "Ètò ìnáwó {name} ti dé {percentage}%.", "goal_achieved_message": "O ti ṣàṣeyọrí àfojúsùn '{name}'.", "goal_due_message": "Àfojúsùn rẹ '{name}' yóò pé ní ọjọ́ {days}.", "goal_behind_message": "'{name}' ní ìnáwó tó tó {percentage}% nìkan.", "budget_exceeded_message": "{name} ti kọjá iye isuna pẹ̀lú {amount}.", "low_balance_message": "Owó tó wà lọ́wọ́lọ́wọ́ jẹ́ {amount}.", "income_added_message": "A gba {amount} owó wọlé láti ọ̀dọ̀ {source}.", "expense_recorded_message": "A ná {amount} lórí {category}."},
    "ha": {"budget_percentage_message": "Kasafin kuɗin {name} ya kai {percentage}%.", "goal_achieved_message": "Ka cimma manufarka ta '{name}'.", "goal_due_message": "Manufarka ta '{name}' za ta cika nan da kwanaki {days}.", "goal_behind_message": "An samar da kuɗin '{name}' da kashi {percentage}% kawai.", "budget_exceeded_message": "An wuce kasafin {name} da {amount}.", "low_balance_message": "Ragowar kuɗin yanzu shi ne {amount}.", "income_added_message": "An karɓi kuɗin shiga {amount} daga {source}.", "expense_recorded_message": "An kashe {amount} a kan {category}."},
    "fr": {"budget_percentage_message": "Le budget {name} a atteint {percentage} %.", "goal_achieved_message": "Vous avez atteint votre objectif « {name} ».", "goal_due_message": "Votre objectif « {name} » arrive à échéance dans {days} jour(s).", "goal_behind_message": "L'objectif « {name} » n'est financé qu'à {percentage} %.", "budget_exceeded_message": "Le budget {name} est dépassé de {amount}.", "low_balance_message": "Le solde actuel est de {amount}.", "income_added_message": "Un revenu de {amount} a été reçu de {source}.", "expense_recorded_message": "Une dépense de {amount} a été effectuée pour {category}."},
    "es": {"budget_percentage_message": "El presupuesto {name} ha alcanzado el {percentage}%.", "goal_achieved_message": "Has alcanzado tu objetivo '{name}'.", "goal_due_message": "Tu objetivo '{name}' vence en {days} día(s).", "goal_behind_message": "'{name}' solo está financiado al {percentage}%.", "budget_exceeded_message": "{name} ha superado el presupuesto por {amount}.", "low_balance_message": "El saldo actual es {amount}.", "income_added_message": "Se recibieron {amount} de ingresos de {source}.", "expense_recorded_message": "Se gastaron {amount} en {category}."},
    "pt": {"budget_percentage_message": "O orçamento {name} atingiu {percentage}%.", "goal_achieved_message": "Atingiu a sua meta '{name}'.", "goal_due_message": "A sua meta '{name}' vence dentro de {days} dia(s).", "goal_behind_message": "'{name}' está financiada em apenas {percentage}%.", "budget_exceeded_message": "{name} excedeu o orçamento em {amount}.", "low_balance_message": "O saldo atual é {amount}.", "income_added_message": "Foi recebida uma receita de {amount} de {source}.", "expense_recorded_message": "Foram gastos {amount} em {category}."},
}

NOTIFICATION_TEXT_KEYS = {
    "Budget Exceeded": "budget_exceeded_title", "Budget Warning": "budget_warning_title",
    "Budget Critical": "budget_critical_title", "Goal Achieved": "goal_achieved_title",
    "Goal Due": "goal_due_title", "Goal Behind Schedule": "goal_behind_title",
    "Low Balance": "low_balance_title", "Payment Successful": "payment_success_title",
    "Subscription Expiring": "subscription_expiring_title",
    "Income Added": "income_added_title", "Expense Recorded": "expense_recorded_title",
    "Bill Due": "bill_due_title", "FOCOST AI Insight": "ai_insight_title",
    "FOCOST AI is available only to normal users.": "ai_normal_users_only",
    "Please keep your FOCOST AI message within 4,000 characters.": "ai_message_limit",
    "Please enter a message.": "ai_enter_message",
    "I can't prepare an accurate financial answer in your selected display currency because a required exchange rate is unavailable. Please try again later or temporarily select the original transaction currency.": "ai_currency_unavailable",
}

for _language_code, _entries in _CROSS_MODULE_TRANSLATIONS.items():
    CATALOGUE[_language_code].update(_entries)

TEXT_KEY_MAP.update({
    "Total Income": "total_income", "Total Expenses": "total_expenses", "Net Savings": "net_savings",
    "Current Balance": "current_balance", "Financial Health": "financial_health", "Financial Position": "financial_position",
    "Total Budget": "total_budget", "Budget Used": "budget_used", "Spent": "spent", "Remaining": "remaining",
    "Target": "target", "Saved": "saved", "Contribution": "contribution", "Contributions": "contributions",
    "Investment": "investment", "Investments": "investments", "Current Value": "current_value",
    "Cost Basis": "cost_basis", "Gain / Loss": "gain_loss", "Net Worth": "net_worth",
    "Period": "period", "Category": "category", "Merchant": "merchant", "Payment Method": "payment_method",
    "Recurring": "recurring", "One-time": "one_time", "Forecast": "forecast", "Monthly Forecast": "monthly_forecast",
    "Income Breakdown": "income_breakdown", "Expense Breakdown": "expense_breakdown", "Recent Transactions": "recent_transactions",
    "View All": "view_all", "No data available": "no_data", "Start Date": "start_date", "End Date": "end_date",
    "Original Amount": "original_amount", "Original Currency": "original_currency", "Display Currency": "display_currency",
    "Exchange Rate": "exchange_rate", "Rate Date": "rate_date", "Converted Amount": "converted_amount",
    "Account Balance": "account_balance", "Transaction Date": "transaction_date", "Financial Summary": "financial_summary",
})
