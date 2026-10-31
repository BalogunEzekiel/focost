# FOCOST incremental communications and audit patch

This patch extends the previously generated `focost_investment_communications_patch.zip`. Apply this patch **after** the earlier investment/communications patch. It is an overlay: it does not replace the earlier migration, announcement model, RBAC files, rich-text editor, or dashboard templates.

## Included files

- `app/services/announcement_service.py`
  - Adds the `subscription_expired` audience option.
  - Resolves it from the latest subscription belonging to a normal User account, using expiry dates/status without creating a trial or mutating subscription state.
  - Delivers bulk email separately to each matching recipient and renders `Dear First Last,` with a safe `Hello,` fallback.
  - Builds the absolute URL for the existing exact `app/static/images/pwa-512.png` asset.
- `app/routes/admin.py`
  - Adds a permission-protected JSON detail endpoint for an individual audit event.
- `app/templates/admin/audit_logs.html`
  - Adds the missing Bootstrap modal and fetches details from the protected endpoint. Text is inserted with `textContent` to avoid HTML injection.
- `app/templates/emails/announcement.html`
  - Responsive table-based email markup for common email clients.
  - Uses the exact PWA logo asset with fixed proportional dimensions (no redraw or alteration).
  - Personalized greeting, CTA, flyer image, FOCOST signature, website/support links, and clickable Facebook/LinkedIn icons without displaying social URLs.

## Official signature links used

- Website: `https://focost.pythonanywhere.com`
- Support: `mailto:focostsupport@gmail.com`
- Facebook: `https://www.facebook.com/profile.php?id=61595405655287`
- LinkedIn: `https://www.linkedin.com/company/focost/`

The social URLs are destinations only; the visible email signature shows icon links, not the URLs.

## Deployment

1. Back up the production project and database.
2. Apply the earlier investment/communications patch first if it has not already been applied.
3. Copy these four files to the exact matching project paths, overwriting those files only.
4. No additional database migration is required for `subscription_expired`; the earlier patch's `audience_groups` JSON column stores the audience slug.
5. Reload the application.

## Verification

1. In Communications Center, confirm **Subscription Expired** appears in Audience groups.
2. Test with a normal User whose latest trial has an expiry in the past, and with a normal User whose paid `current_period_end` is in the past. Confirm active/renewed subscriptions are excluded. Admin accounts must never match this group.
3. Create a draft targeting Subscription Expired, then test preview/publication and email delivery with a controlled test mailbox.
4. Confirm the email greeting uses each recipient's first and last name; users with missing names receive `Hello,`.
5. Confirm the logo image loads from the deployed static URL and the Facebook/LinkedIn icons open the official destinations.
6. Open Audit Logs and click View. Confirm the modal loads event data and displays an error if the event cannot be retrieved.

## Important notes

- This patch does not change subscription billing, renewal, trial creation, plan entitlements, or the underlying subscription status lifecycle.
- Subscription Expired intentionally excludes users who have never had a subscription record; it is for accounts whose trial or paid subscription has expired/cancelled.
- HTML email rendering depends on the mail provider accepting remote images. Some recipients may need to enable image display in their email client.
- The complete project test suite and live SMTP delivery cannot be executed in this isolated patch-building environment. Test with a controlled recipient before sending a production bulk campaign.
