# FOCOST World-Class Product Roadmap

## Purpose

This roadmap defines the ongoing product, engineering, security, financial-integrity,
AI, subscription, and production-readiness direction for FOCOST.

FOCOST is an AI-powered financial-management platform designed to help individuals,
businesses, churches, and NGOs make better-informed financial decisions through
financial tracking, reporting, budgeting, goals, investments, notifications,
AI-assisted analysis, forecasting, and subscription-based services.

This roadmap complements the implementation and production documentation already
maintained in the `docs/` directory.

---

## 1. Current Foundation

FOCOST 2.1 currently provides the following major capabilities:

- Income and expense management
- Budget management
- Financial goals and contributions
- Asset and investment tracking
- Dashboard financial summaries
- Reports and filtered transaction analysis
- Financial-position reconciliation
- Notifications
- Authentication and authorization
- Role and permission controls
- CSRF protection
- Security headers
- Request identification
- API health and readiness endpoints
- AI-assisted financial coaching
- AI usage and token accounting
- Statistical forecasting
- Subscription and entitlement management
- Trial lifecycle
- Paystack payment integration
- Server-side payment verification
- Paystack webhook processing
- Production deployment documentation
- Privacy and Play Store preparation documentation

The `DashboardService` remains the authoritative source for current dashboard
financial-position calculations, while report-period calculations remain separate
from current financial-position data.

---

## 2. Engineering Principles

Future development should preserve these principles:

### Functional preservation

Enhancements must not silently remove or alter existing user-facing functionality.

### Single source of truth

Financial calculations should have one authoritative implementation wherever
possible. Duplicated financial logic should be avoided.

### Security by default

Authentication, authorization, CSRF protection, secure session configuration,
secret management, payment verification, and input validation must remain part of
the normal application architecture.

### Data integrity

Financial records must remain internally consistent across income, expenses,
goals, investments, assets, reports, and dashboard calculations.

### Production safety

Production changes must use controlled migrations, backups, environment-based
configuration, and explicit deployment procedures.

### Testability

New functionality should include appropriate unit, integration, route, security,
or service-level tests.

### Privacy

Sensitive financial, authentication, payment, and AI-related information must
be handled according to the application's privacy requirements and applicable
platform policies.

---

## 3. Product Roadmap

### Phase A — Core Financial Platform

Status: Implemented / continuously maintained

- Income tracking
- Expense tracking
- Budgets
- Goals
- Assets
- Investments
- Dashboard summaries
- Transaction filtering
- Financial reports
- Financial-position reconciliation
- Notifications

Primary objective:

Maintain accurate, explainable financial calculations while improving usability
without breaking existing workflows.

---

### Phase B — AI Financial Coach

Status: Implemented / continuously improving

- Provider/model abstraction
- AI conversations
- Database-derived financial context
- AI usage tracking
- Token accounting
- Financial coaching
- Statistical forecasting
- Provider configuration
- Runtime availability reporting

Future improvements:

- Better prompt/context efficiency
- Stronger token-budget controls
- Improved failure handling
- Provider failover
- Response-quality monitoring
- More explainable financial recommendations
- Safer handling of sensitive financial context
- Automated AI service regression tests

AI output should assist users with analysis and education while clearly separating
computed financial facts from model-generated interpretation.

---

### Phase C — Subscription and Billing

Status: Implemented / production activation required

- 30-day trial lifecycle
- Paid subscription plans
- Entitlements
- Server-side transaction initialization
- Server-side payment verification
- Paystack webhook handling
- Subscription status management
- Plan-based AI usage controls

Future improvements:

- Comprehensive billing event auditing
- Idempotent webhook processing
- Subscription renewal monitoring
- Failed-payment handling
- Cancellation and expiration workflows
- Customer billing history
- Operational billing dashboards
- Automated billing integration tests

Production Paystack credentials must remain outside source control and must be
configured through the production secret/environment mechanism.

---

### Phase D — Security and Privacy

Status: Implemented / continuously maintained

Current foundation includes:

- Authentication
- Authorization
- Role-based access control
- CSRF protection
- Security headers
- Secure session configuration
- Secret/environment configuration
- Request IDs
- API authentication contracts
- Privacy preparation

Future improvements:

- Periodic dependency auditing
- Security regression testing
- Rate-limit monitoring
- Login and authentication event auditing
- Stronger operational logging
- Secret rotation procedures
- Backup and recovery testing
- Privacy documentation reviews
- Data-retention and deletion workflows

No production credential, payment secret, AI API key, encryption key, or session
secret should be committed to the repository.

---

### Phase E — Reporting and Financial Analytics

Status: Implemented / continuously improving

Current capabilities include:

- Income analysis
- Expense analysis
- Category analysis
- Monthly trends
- Multi-year reporting
- Financial-position reporting
- Filtered report data
- Export support

Future improvements:

- Additional management dashboards
- Cash-flow analysis
- Financial-health indicators
- Budget variance analysis
- Goal progress analytics
- Investment performance analytics
- Improved export formatting
- More configurable reporting periods
- Visualization accessibility improvements

All new financial metrics should be reconciled against the authoritative financial
services before being exposed in the user interface.

---

## 4. Data and Database Roadmap

Priorities:

1. Preserve migration safety.
2. Avoid destructive production database operations.
3. Maintain appropriate indexes for frequently queried financial data.
4. Review database constraints as new financial workflows are introduced.
5. Keep development and production database configuration separate.
6. Maintain tested backup and restoration procedures.
7. Monitor query performance as transaction volume increases.

Production schema changes should use the project's migration mechanism rather than
destructive database recreation.

---

## 5. Testing Roadmap

The automated test suite should continue expanding around these areas:

- Model behavior
- Service calculations
- Financial-integrity rules
- Route authentication
- Authorization
- CSRF behavior
- Security headers
- API contracts
- Reporting
- Dashboard reconciliation
- AI service behavior
- Subscription lifecycle
- Paystack verification
- Webhook idempotency
- Export functionality
- Production configuration

Every material financial or security change should have a corresponding regression
test where practical.

---

## 6. Production Readiness

Before a production release, verify:

- Production `SECRET_KEY` is configured securely.
- Database configuration points to the intended production database.
- Production AI credentials are configured through secrets/environment variables.
- Paystack live credentials are configured only on the server.
- `SESSION_COOKIE_SECURE=true` is enabled where HTTPS is used.
- Database migrations have been reviewed.
- A verified database backup exists.
- Webhook endpoints are reachable and signature verification is enabled.
- Health and readiness endpoints respond correctly.
- Application logs are operational.
- Error handling does not expose sensitive information.
- Static assets are present.
- Required documentation is current.
- Automated tests pass.

See `docs/FOCOST_PRODUCTION_GUIDE.md` for detailed deployment procedures.

---

## 7. Android and Platform Distribution

Status: Preparation / policy-dependent

The Android application should remain aligned with:

- FOCOST backend APIs
- Authentication requirements
- Subscription entitlements
- Privacy disclosures
- Data-safety declarations
- Applicable Google Play payment requirements

Android release work should follow `android/GOOGLE_PLAY_GUIDE.md` and the privacy
checklist rather than duplicating platform-specific requirements in application
code.

---

## 8. Observability and Operations

Future operational capabilities should include:

- Structured application logging
- Error monitoring
- Request tracing using request IDs
- AI provider availability monitoring
- Payment/webhook monitoring
- Database health monitoring
- Background-job monitoring where applicable
- Operational alerts
- Deployment health checks

Operational telemetry should avoid unnecessarily recording sensitive financial
information, credentials, payment secrets, or private AI conversation content.

---

## 9. User Experience

Future UX improvements should prioritize:

- Clear financial terminology
- Responsive layouts
- Accessible controls
- Mobile-friendly workflows
- Consistent navigation
- Fast dashboard rendering
- Clear validation messages
- Useful empty states
- Explainable financial metrics
- Consistent currency and number formatting
- Clear subscription status
- Clear AI availability and error states

Visual improvements should preserve existing business logic and server-side
contracts.

---

## 10. Quality Gates

A significant FOCOST release should satisfy the following gates:

### Functional

- Core financial workflows operate correctly.
- Financial calculations reconcile.
- Reports agree with authoritative financial services.

### Security

- Authentication and authorization tests pass.
- CSRF protection remains enabled.
- Security headers remain present.
- Production secrets are externalized.

### Data

- Database migrations are tested.
- Financial records remain consistent.
- Backups and restoration procedures are documented.

### AI

- Provider configuration is valid.
- AI failures degrade gracefully.
- Usage accounting remains accurate.
- Sensitive financial context is handled appropriately.

### Billing

- Payment verification occurs server-side.
- Webhooks are authenticated and idempotent.
- Subscription entitlements match payment state.

### Deployment

- Health and readiness checks pass.
- Static assets and templates are present.
- Production configuration is verified.

---

## 11. Long-Term Direction

The long-term objective is to evolve FOCOST into a dependable financial-management
platform that combines:

- Personal finance management
- Organizational financial management
- Financial analytics
- AI-assisted financial coaching
- Forecasting
- Goal planning
- Investment tracking
- Subscription services
- Secure payment processing
- Actionable financial intelligence

Growth should remain incremental and test-driven. New capabilities should be
introduced without compromising financial correctness, security, privacy,
maintainability, or existing user workflows.

---

## 12. Documentation Map

Key project documentation includes:

- `README.md` — project overview and major capabilities
- `docs/FOCOST_PRODUCTION_GUIDE.md` — production, GitHub, PythonAnywhere and
  Paystack deployment guidance
- `docs/IMPLEMENTATION_NOTES.md` — external activation requirements
- `docs/IMPLEMENTATION_UPDATE.md` — implementation summary
- `docs/IMPLEMENTATION_UPDATE_FINANCIAL_INTEGRITY.md` — financial-integrity changes
- `docs/PRIVACY_POLICY_CHECKLIST.md` — privacy and Play Store preparation
- `android/GOOGLE_PLAY_GUIDE.md` — Android and Google Play guidance
- `docs/WORLDCLASS_ROADMAP.md` — product and engineering roadmap

---

## 13. Change Management

Roadmap items are directional and should be implemented only after reviewing
their impact on:

- Existing functionality
- Database schema
- Financial calculations
- Authentication and authorization
- AI usage
- Subscription entitlements
- Payment processing
- Privacy
- Test coverage
- Production deployment

A roadmap item should not be considered complete merely because its UI exists.
The corresponding backend behavior, data integrity, security requirements,
automated tests, and production implications should also be considered.

---

## Version

Roadmap: FOCOST 2.1  
Status: Living document  
Last reviewed: September 2026
