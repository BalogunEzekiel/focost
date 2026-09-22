# Implementation Notes and External Activation Steps

The codebase has been enhanced without embedding production credentials.

## Requires external activation

1. **Paystack live/test credentials:** must be supplied by the merchant from Paystack. The application cannot generate Paystack secret/public credentials on the merchant's behalf.
2. **Paystack monthly plan codes:** the project can create missing plans with `flask --app run.py create-paystack-plans`, or existing plan codes can be configured.
3. **AI provider keys:** Groq/Cerebras keys must be supplied through environment secrets.
4. **Outbound email:** requires SMTP provider credentials if email notifications are enabled.
5. **Android Google Play Billing:** the web Paystack provider is intentionally not reused as an in-app digital subscription payment method. A native Android provider adapter and Google purchase-token verification should be added when the Android client is built. This is required because Play's current payments policy generally requires Play Billing for digital subscriptions sold inside Play-distributed apps, subject to applicable exceptions/programs.

## Intentionally not fabricated

No fake Paystack credentials, Paystack plan codes, Google Play credentials, SMTP credentials, AI API keys, signing keys or payment tokens are included.

This is necessary for a secure production deployment.
