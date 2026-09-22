# FOCOST Implementation Update

Implemented in this build:

1. AI historical data
- AI context now includes complete available income and expense records, historical monthly series, budgets, goals/contributions, assets/investments, financial-health data and user currency.
- Natural-language historical month parsing supports examples such as July, July 2026, August, July and August, ISO dates and date ranges.
- Operating expenses are distinguished from investment and goal-transfer cash outflows.

2. Session-only AI chat
- AI conversation history is stored only in the active Flask session.
- ChatSession/ChatMessage are no longer used by the current AI service.
- Logout and Clear Chat remove the session conversation.

3. AI usage
- Usage is tied to the active trial/subscription billing period instead of the calendar month.
- Historical AI usage records remain persistent.
- Super Admin dashboard now shows platform AI consumption and per-user usage.
- Super Admins with `ai.configure` permission can reset a user's current-period usage without deleting historical usage.

4. User settings
- Replaced the non-functional duplicate settings modal with a single functional settings engine.
- Save and Reset use the server API and persist preferences.
- Theme, density, dashboard widgets, AI preferences and notification preferences are applied immediately.

5. Profile avatars
- Uploaded avatars are stored with unique filenames.
- Previous uploaded avatar is cleaned up after replacement.
- Topbar and sidebar now display the uploaded avatar.
- Avatar serving is restricted to the authenticated user's own avatar file.

6. Data export
- Export includes profile, income, expenses, budgets, goals/contributions, assets, settings, subscription records and AI usage.
- Passwords and secrets are excluded.

7. Investments
- Investment purchases can originate from the Expense workflow.
- The cash outflow reduces available cash but is classified as an investment/asset rather than an operating expense.
- Investments are linked to their source expense and can be edited from the Assets & Investments page.
- Reporting excludes investment cash transfers from operating expense totals while retaining their cash-flow impact.

8. Goals
- Goal contributions now create linked internal cash-outflow transactions.
- Contributions reduce available cash and are excluded from operating expense totals.
- Editing/deleting a contribution keeps the linked cash transaction synchronized.
- Legacy standalone contributions are backfilled by the accounting migration.

Migration:
    flask --app run.py db upgrade

The attached development database has already been updated to the new schema revision for immediate local use.

Security:
- The project `.env` file is intentionally excluded from the distribution ZIP. Use `.env.example` and configure secrets locally.
- Do not commit or share production API keys, Paystack secrets, AI keys or Flask SECRET_KEY.
