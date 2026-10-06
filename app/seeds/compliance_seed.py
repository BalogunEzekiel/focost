from app.extensions import db
from app.services.compliance_service import ComplianceService

POLICY_VERSION = "1.1"

POLICIES = {
    "terms": {
        "title": "FOCOST Terms of Service",
        "document_type": "terms",
        "summary": "The terms governing access to and use of FOCOST.",
        "content_html": """
<h2>1. About FOCOST</h2>
<p>FOCOST is an AI-powered personal financial advisor and conversational coach. It provides tools for recording financial information, budgeting, goals, reporting, forecasting, investment tracking and data-grounded financial insights.</p>
<h2>2. Eligibility and account responsibility</h2>
<p>You must be legally able to enter into these Terms. You are responsible for the accuracy of information you enter, maintaining the confidentiality of your credentials, keeping your email address current and reviewing activity on your account.</p>
<h2>3. Email verification and account security</h2>
<p>New accounts may require email verification before activation. You must not share authentication credentials, verification links or password-reset links. FOCOST may apply authentication throttling, account restrictions or other controls to protect the service.</p>
<h2>4. Financial records and calculations</h2>
<p>FOCOST calculates financial metrics from application records according to its published product logic. You remain responsible for reviewing records and correcting inaccurate information. Non-cash investment valuation changes are not treated as ordinary cash income or expenses in FOCOST cash-flow calculations; investment funding and other transaction classifications follow the application's accounting rules.</p>
<h2>5. AI and financial information</h2>
<p>FOCOST AI provides automated analysis, explanations and educational suggestions. AI output may be incomplete, inaccurate or inappropriate for a particular circumstance. It is not regulated investment, tax, legal, accounting or fiduciary advice and is not a guarantee of financial results.</p>
<h2>6. Subscriptions and payments</h2>
<p>FOCOST offers a configured free trial and paid subscription plans. Prices, entitlements, billing intervals and applicable taxes are displayed at the point of offer. Web payments are processed through the configured payment provider. FOCOST does not intentionally collect full payment-card credentials through ordinary application forms.</p>
<h2>7. Acceptable use</h2>
<p>You must not abuse, reverse engineer, attack, scrape, overload, impersonate another person, bypass access controls, attempt credential stuffing, interfere with payment or security systems, or use FOCOST for unlawful activity. The Acceptable Use Policy forms part of these Terms.</p>
<h2>8. Availability and third parties</h2>
<p>FOCOST is provided on a commercially reasonable basis. Maintenance, outages, network failures, third-party AI or payment-provider failures and security events may temporarily affect availability.</p>
<h2>9. Suspension and termination</h2>
<p>FOCOST may restrict or suspend access where reasonably necessary for security, fraud prevention, payment issues, legal compliance, abuse prevention or material breach. Users may request account deletion through available account controls.</p>
<h2>10. Intellectual property</h2>
<p>FOCOST software, branding, interface and service materials remain protected by applicable intellectual-property rights. You retain rights in information you lawfully provide to the service, subject to the permissions necessary to operate FOCOST.</p>
<h2>11. Changes</h2>
<p>FOCOST may update these Terms as the service, law or risk environment changes. Material changes will be communicated through appropriate in-product or email notices where required. Continued use after the effective date may require renewed acceptance.</p>
<h2>12. Contact</h2>
<p>For general support, contact <a href="mailto:focostsupport@gmail.com">focostsupport@gmail.com</a>. Security reports should use the published security contact.</p>
""",
    },
    "privacy": {
        "title": "FOCOST Privacy Policy",
        "document_type": "privacy",
        "summary": "How FOCOST processes personal data, including financial, account, AI, subscription and security information.",
        "content_html": """
<h2>1. Scope</h2>
<p>This Privacy Policy explains how FOCOST processes personal data in connection with its website and application. It is intended to provide transparent information about collection, use, disclosure, security, retention and data-subject rights.</p>
<h2>2. Applicable framework</h2>
<p>For users and processing subject to Nigerian data-protection law, FOCOST operates with reference to the Nigeria Data Protection Act 2023 and applicable implementing requirements, including the Nigeria Data Protection Act General Application and Implementation Directive (GAID) 2025. Other laws may apply depending on the user's location and the nature of processing.</p>
<h2>3. Information we process</h2>
<ul><li>Account details such as name, email address, country, currency and occupation where provided.</li><li>Financial information entered by you, including income, expenses, budgets, goals, contributions and investment records.</li><li>Profile information and images you choose to upload.</li><li>AI prompts, relevant conversation history and application-generated financial context used to answer requests.</li><li>Subscription, payment-reference and billing lifecycle information.</li><li>Security, authentication, audit and technical information such as request identifiers, session information and security events.</li><li>Notification and preference settings.</li></ul>
<h2>4. Purposes and legal bases</h2>
<p>Depending on the circumstances, FOCOST may process data to provide and secure the service, perform a contract, respond to requests, process subscriptions, prevent fraud and abuse, maintain auditability, comply with legal obligations, protect legitimate interests, or obtain consent where consent is the appropriate basis.</p>
<h2>5. Financial information</h2>
<p>Financial information is used to provide the features you request. FOCOST's deterministic application services are intended to remain the authoritative source for financial calculations displayed by the application and supplied to its AI explanation layer.</p>
<h2>6. AI processing</h2>
<p>When you use AI features, relevant prompts and the minimum financial context needed for the requested feature may be processed by the AI provider configured by FOCOST. AI providers may process data under their own terms and privacy documentation. Do not submit information to the AI feature that you are not authorised to disclose or that you do not want processed for that feature.</p>
<h2>7. Payments and processors</h2>
<p>Subscription payments may be processed by payment providers such as Paystack. FOCOST is designed to minimise payment-card data exposure and retain payment references, subscription identifiers and reconciliation information rather than full card credentials. FOCOST may also use hosting, database, email, storage, AI and other service providers.</p>
<h2>8. International processing</h2>
<p>Some service providers may process data outside Nigeria. Where applicable, FOCOST will use the transfer mechanisms and safeguards required by applicable law and maintain appropriate processor and security controls.</p>
<h2>9. Security</h2>
<p>FOCOST uses measures such as access controls, password hashing, email verification, password-reset controls, CSRF protection, secure sessions, security headers, audit logging, environment-managed secrets, controlled migrations and server-side payment verification. No internet-connected system can guarantee absolute security.</p>
<h2>10. Retention</h2>
<p>Personal data is retained for as long as necessary for the purposes described in this Policy, service continuity, security, dispute handling, accounting and applicable legal obligations. Specific retention periods are documented internally in FOCOST's data-retention schedule.</p>
<h2>11. Your rights</h2>
<p>Subject to applicable law and relevant exceptions, you may have rights to request access, correction, deletion, portability, restriction, objection and other forms of control over your personal data. Requests can be made through the available account controls or by contacting <a href="mailto:focostsupport@gmail.com">focostsupport@gmail.com</a>. Identity and account-ownership checks may be required.</p>
<h2>12. Data deletion and legal retention</h2>
<p>Account deletion does not necessarily require immediate deletion of every record where retention is required by law, security, fraud prevention, payment reconciliation, dispute resolution or another lawful exception.</p>
<h2>13. Children</h2>
<p>FOCOST is intended for people who can lawfully enter into the service Terms. FOCOST does not knowingly seek to provide the service to children where doing so would be unlawful or require safeguards that have not been implemented.</p>
<h2>14. Changes</h2>
<p>This Policy may be updated when FOCOST, its processors, processing purposes or applicable legal requirements change. The current version and effective date are displayed in the service.</p>
<h2>15. Privacy contact</h2>
<p>Privacy enquiries: <a href="mailto:focostprivacy@gmail.com">focostprivacy@gmail.com</a>.</p>
""",
    },
    "cookies": {
        "title": "FOCOST Cookie Notice",
        "document_type": "cookie",
        "summary": "How FOCOST uses essential session/security cookies and optional technologies.",
        "content_html": """
<h2>1. Essential cookies</h2><p>FOCOST uses essential session and security cookies required for authentication, CSRF protection, account state and basic operation. These are necessary for the secure operation of the service.</p>
<h2>2. Optional cookies</h2><p>The core FOCOST application does not require advertising cookies for financial functionality. Optional non-essential technologies should only be enabled where the applicable consent requirements have been satisfied.</p>
<h2>3. Cookie preferences</h2><p>Where optional cookies are offered, the cookie preference control allows you to choose whether to permit them. Browser settings can also restrict or delete cookies, although this may affect authentication or other functionality.</p>
<h2>4. Changes</h2><p>This notice may be updated as the application adds or changes technologies.</p>
""",
    },
    "ai-disclosure": {
        "title": "FOCOST AI & Financial Disclaimer",
        "document_type": "ai_disclosure",
        "summary": "Important information about FOCOST's AI-assisted financial features and limitations.",
        "content_html": """
<h2>1. What FOCOST AI does</h2><p>FOCOST AI can summarise and explain financial information, identify patterns, answer questions about application calculations, and provide educational suggestions based on the financial context supplied by FOCOST.</p>
<h2>2. The application's calculations are authoritative</h2><p>Where FOCOST supplies a financial figure to the AI, the application services are intended to be the authoritative source for that figure. The AI should explain supplied calculations rather than inventing independent totals.</p>
<h2>3. No professional or regulated advice</h2><p>FOCOST AI is not a bank, broker, investment adviser, tax adviser, lawyer, accountant or fiduciary. AI output is not regulated financial, investment, tax, legal or accounting advice and is not a guarantee of results.</p>
<h2>4. Accuracy and limitations</h2><p>AI systems can produce incomplete, outdated or incorrect output. Verify material decisions against your records and appropriate qualified professionals or authoritative sources.</p>
<h2>5. Human control</h2><p>You remain responsible for decisions made using FOCOST. FOCOST does not automatically execute an investment, banking or other financial transaction merely because the AI recommends or discusses it.</p>
<h2>6. AI data processing</h2><p>Prompts and the financial context necessary to answer them may be processed by the AI provider configured by FOCOST. Avoid submitting unnecessary secrets or information you are not authorised to disclose.</p>
<h2>7. Investment valuation</h2><p>Non-cash investment valuation gains and losses are not ordinary cash income or expenses in FOCOST's financial calculations. They remain part of investment value and should not be interpreted as cash available for spending.</p>
""",
    },
    "acceptable-use": {
        "title": "FOCOST Acceptable Use Policy",
        "document_type": "acceptable_use",
        "summary": "Security, abuse-prevention and responsible-use requirements for FOCOST.",
        "content_html": """
<h2>1. Prohibited activity</h2><p>You must not attempt credential stuffing, brute force, malware deployment, denial of service, unauthorised access, data scraping, privilege escalation, payment abuse, impersonation, security-control bypass or unlawful processing.</p>
<h2>2. Data and privacy</h2><p>Do not upload or disclose personal information belonging to another person unless you have a lawful basis and appropriate authority to do so.</p>
<h2>3. Security testing</h2><p>Do not conduct destructive, intrusive or high-volume testing against FOCOST without prior written authorisation. Responsible vulnerability reports should follow the Security page's disclosure guidance.</p>
<h2>4. Enforcement</h2><p>FOCOST may rate-limit, suspend or terminate access when necessary to protect users, the platform, third parties, payment systems or legal compliance.</p>
""",
    },
}


def seed_policies():
    """
    Seed compliance policies using the centralized immutable
    policy publication service.

    Existing policy versions are never overwritten.

    If the requested slug/version already exists:
        - its content hash is verified
        - the existing published record is left untouched

    If the requested slug/version does not exist:
        - the previous current version is retired
        - the new version is created as current

    To publish a future version, deliberately change POLICY_VERSION,
    e.g. from 1.1 to 1.2, only after the policy content has actually
    been reviewed and approved.
    """
    for slug, data in POLICIES.items():
        ComplianceService.publish_policy(
            slug=slug,
            title=data["title"],
            version=POLICY_VERSION,
            document_type=data["document_type"],
            summary=data["summary"],
            content_html=data["content_html"],
        )

    db.session.commit()