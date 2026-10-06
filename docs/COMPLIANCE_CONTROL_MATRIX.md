# FOCOST Compliance & Production Control Matrix

This document is an implementation baseline, not legal advice. A Nigerian privacy professional/DPO and qualified counsel should review the final public policies, data flows, contracts and regulatory classification before launch.

## Nigeria
- Nigeria Data Protection Act 2023 (NDP Act).
- NDP Act General Application and Implementation Directive (GAID) 2025.
- Data Protection Officer / privacy governance where required.
- Record of Processing Activities (ROPA).
- Data Processing Agreements with relevant processors.
- Data Privacy Impact Assessment (DPIA) for high-risk processing, including AI/data-intensive processing where applicable.
- Cross-border transfer assessment and lawful mechanism.
- Data-subject request handling and retention schedule.
- Incident/breach response and regulator notification assessment.

## Global / engineering
- GDPR principles and rights where GDPR territorial/material scope applies.
- NIST CSF 2.0 for cybersecurity governance.
- OWASP ASVS authentication, session, input-validation and recovery principles.
- PCI DSS v4.0.1 scoping principles for payment-card environments. FOCOST should minimise PCI scope by using Paystack/other hosted payment components and never storing full card credentials.
- Secure SDLC: code review, dependency review, secrets management, migration review, backup/recovery tests and security regression tests.

## Implemented in application
- CSRF protection and security headers.
- Secure/HTTP-only/SameSite session configuration with production HTTPS flag.
- Request correlation IDs and audit logging.
- RBAC and least privilege.
- Email verification and activation.
- Hashed, one-time, expiring verification and password-reset tokens.
- Login and recovery throttling.
- Generic password-reset responses to reduce account enumeration.
- Policy/version acceptance records.
- Cookie preference control.
- User data export.
- Account deletion workflow.
- Super Administrator document archive with upload/download/delete audit trail.
- Server-authoritative payment verification.
- Non-cash investment valuation excluded from income/expense cash-flow totals.
- Central authoritative income breakdown query for AI and future consumers.

## Required before public launch
- Legal review and approval of all public policies.
- Confirm actual controller/legal entity and privacy contacts.
- Complete ROPA, DPIA, processor inventory and DPAs.
- Complete retention schedule and deletion exceptions.
- Configure transactional email and verify SPF/DKIM/DMARC.
- Production HTTPS, secure secret storage and backups.
- Vulnerability scanning and penetration/security testing.
- Disaster recovery restoration test.
- Android Data Safety and Apple App Privacy disclosures based on the final native app/SDK inventory.
- Store-specific billing implementation for digital subscriptions where required.
