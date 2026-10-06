FOCOST Public Web Documentation

Public information architecture

The FOCOST public experience separates product education, company information,
customer support and product feedback into clear destinations.

Public routes

/showcase/platform — platform overview and capabilities

/showcase/pricing — current public subscription catalogue

/showcase/faq — frequently asked questions

/showcase/about — FOCOST story, mission and information about its builder

/feedback/ — internal FOCOST feedback submission

/showcase/support — support centre and contact channels

/showcase/security — security controls and responsible disclosure

/.well-known/security.txt — machine-readable security contact and policy URL

/privacy — current privacy policy

/terms — current terms of service

/cookies — cookie notice

/ai-disclosure — AI and financial disclaimer

/acceptable-use — acceptable use policy

Navigation model

The primary public navigation contains:

Platform

Pricing

FAQ

About

Feedback

Login / Dashboard

Get Started / Logout

Support intentionally remains in the public footer rather than the primary
navigation so that the topbar stays focused on product discovery and
conversion.

Internal feedback management

FOCOST feedback is stored in the application database rather than an external
form provider.

Authenticated submissions are associated with the submitting FOCOST account.
Anonymous visitors may submit feedback while optionally providing a name and
email address.

Authorized administrators can:

search and filter feedback

review category and rating

assign priority

move feedback through its workflow

add internal notes

track the reviewing administrator and review timestamp

The administrative workflow is:

New → Under Review → Planned / In Progress → Resolved → Closed

The feedback model and FeedbackService are the authoritative sources for
feedback persistence and workflow rules.

Contact model

General support: focostsupport@gmail.com

Security reporting: the published security contact

Transactional email sender: focostteam@gmail.com

Do not publish SMTP credentials, API keys, Paystack secrets, database
credentials or other private configuration in this documentation.

Policy versioning

The application stores policy documents in the policy_documents table.
seed_policies() upserts the current public versions. Updating the stored
version causes the existing policy-acceptance check to require re-acceptance
before an authenticated user continues.

Current public policy version in this package: 1.1.

Legal status

This documentation is operational product documentation, not a substitute for
legal review. Before public launch, the final legal entity details, privacy
contact, data-protection role/designation, retention periods, processor
agreements, cross-border transfer mechanisms and regulatory registration or
filing obligations should be confirmed for the actual FOCOST operator and
processing activities.