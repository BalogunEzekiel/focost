# FOCOST Public Documentation & Security Update

This bundle contains the complete updated files for the public-facing documentation, navigation, security disclosure, support, pricing, FAQ and policy-version update.

## Files to copy into the FOCOST project

- `app/routes/showcase.py`
- `app/routes/auth.py`
- `app/config.py`
- `app/__init__.py`
- `app/seeds/compliance_seed.py`
- `app/templates/includes/public_navbar.html`
- `app/templates/includes/footer.html`
- `app/templates/auth/register.html`
- `app/templates/auth/reaccept.html`
- `app/templates/security.html`
- `app/templates/pricing.html`
- `app/templates/faq.html`
- `app/templates/support.html`
- `tests/test_public_documentation.py`
- `docs/PUBLIC_WEB_DOCUMENTATION.md`
- `docs/security.txt`

## What is corrected

1. Pricing is now a real route: `/showcase/pricing`.
2. FAQ is now a real route: `/showcase/faq`.
3. Support is now a real route: `/showcase/support`.
4. Security remains a real route: `/showcase/security` and now has a complete responsible-disclosure page.
5. `/.well-known/security.txt` is active and now points to the actual Security page instead of `/security`.
6. Security and support use the currently known active mailbox `focostsupport@gmail.com` by default; override via environment variables when dedicated domain mailboxes are provisioned.
7. The public navbar no longer uses dead `#pricing` or `#faq` anchors.
8. The footer links to real Privacy, Terms, Cookie Notice, AI Disclosure, Security and Support pages.
9. Policy documents are updated to version `1.1` and the seed function upserts them. This intentionally causes existing users who previously accepted version `1.0` to re-accept the current policies.
10. The email-verification audit constant import is corrected in `app/routes/auth.py`.
11. Public pricing is read from the authoritative subscription-plan catalogue rather than hard-coded plan names/prices.
12. FAQ and support explicitly document security, billing, AI, data and account questions.

## Apply

Copy the files into the matching paths in your working FOCOST project. Do not copy any `.env`, database, secret or credential file from this bundle.

Then run:

```powershell
flask seed-compliance
python -m pytest tests/test_public_documentation.py tests/test_static_contracts.py tests/test_config.py -q
python run.py
```

If your environment does not have the project's virtual environment activated, activate it first and install the project's requirements.

## Important policy step

`flask seed-compliance` updates the current policy records to version `1.1`. This is a data change, not an Alembic schema migration. Existing users whose acceptance records contain version `1.0` will be sent through the existing policy re-acceptance flow.

Back up the production database before running the command in production.

## Mailbox model

- Transactional/system email: `focostteam@gmail.com`
- General support/privacy/security contact currently published: `focostsupport@gmail.com`

Do not place Gmail App Passwords or other credentials in source files. Keep them in `.env`/the production secret configuration.

## Legal/compliance note

The policy wording is operationally structured for FOCOST's current feature set and Nigerian deployment context. Final publication should still be reviewed against the actual FOCOST operating entity, processor contracts, data flows, retention schedule, regulatory registration/filing status and any additional jurisdictions that apply.
