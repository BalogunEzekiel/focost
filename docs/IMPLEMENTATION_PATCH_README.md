# FOCOST investment and communications patch

This patch is designed for the uploaded FOCOST project snapshot. It preserves the existing investment service and accounting rules; it changes the default User RBAC permission set so normal users can use the already owner-scoped investment management routes.

## Files included

- `app/rbac/constants.py` — grants `investments.manage` to the standard User role; admin-group forbidden permissions remain unchanged.
- `app/models/announcement.py` — multi-audience compatibility, signature, background, and action-label fields.
- `app/services/announcement_service.py` — audience matching, All Audiences exclusivity, rich-text sanitization, safe URL validation, HTML email rendering, and plain-text delivery to notification/push channels.
- `app/routes/admin_communications.py` — create, draft-edit, publish, and delete workflows.
- `app/templates/admin/communications.html` — rich-text creation UI, audience multi-select, functional URL guidance, optional email signature, and message management/viewing.
- `app/templates/admin/communications_edit.html` — draft editing UI.
- `app/templates/emails/announcement.html` — responsive FOCOST-branded email layout.
- `app/templates/dashboard/dashboard.html` and `app/templates/layouts/dashboard.html` — safe rich message rendering and message backgrounds.
- `app/services/web_push_service.py` — strips HTML from push notification bodies.
- `app/__init__.py` — registers a sanitizer for rich HTML at template-render time, including legacy announcement content.
- `migrations/versions/f1a9c7d2e604_communications_rich_content_and_audiences.py` — adds announcement columns without dropping existing data.
- `requirements.txt` — adds Bleach for HTML sanitization.

## Deployment sequence

1. Back up the production database and project directory.
2. Copy the included files into the matching paths, preserving all other project files.
3. Install the new dependency in the production virtual environment:
   `pip install -r requirements.txt`
4. Apply the database migration:
   `flask db upgrade`
5. Synchronize RBAC so existing standard User role assignments receive the new permission:
   `flask seed-rbac`
6. Reload the PythonAnywhere web application.
7. Test investment valuation update and partial/full liquidation using a normal User account that owns the investment.
8. Test draft creation/editing, multi-audience selection, publish, view and delete; test Action URL and Image/Flyer URL with publicly accessible HTTPS resources; test email signature on an actual test email.

## Important behavior

- The `investments.manage` permission is granted only to the standard User role. The existing administrative group deny-list still excludes it. Investment routes continue to filter records by `current_user.id`; the investment service and its accounting rules are not changed.
- The current implementation stores the rich message as sanitized HTML. It uses Quill 1.3.7 from jsDelivr. For a production environment with a strict Content Security Policy or no CDN access, self-host Quill assets and update the template references.
- The All Audiences group is mutually exclusive both in the browser and server-side validation.
- Drafts can be edited. Published communications can be viewed and deleted, but not edited in place; create a new draft to issue a revision and preserve publication history.
- Action URL appears as a CTA in dashboard/email renderings. Image/Flyer URL appears in dashboard flyer cards and email. Browser push payloads deliberately accept only same-origin relative paths; external Action URLs therefore fall back to the dashboard in push notifications, preserving the existing anti-open-redirect control.
- Email signature is optional. The default signature includes FOCOST website and support links. Add verified official social profile URLs in the signature editor before publishing; do not publish guessed social URLs.
- Rich text is sanitized before storage and again at rendering boundaries. Do not remove either sanitization layer.

## Validation performed on this patch

- Python bytecode compilation passed for the modified application and migration files.
- Jinja template parsing passed for the updated admin, dashboard, layout and email templates (with the app's sanitizer filter registered).
- Node syntax checks passed for both rich-text editor scripts.
- Full pytest execution could not be performed in this runtime because Flask is not installed in the analysis environment. Run the project's test suite in the FOCOST virtual environment before production deployment.
