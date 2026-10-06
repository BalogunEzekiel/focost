# FOCOST Android / iOS Production Checklist

The Flask application is the authoritative backend. A native Android/iOS client should consume a versioned HTTPS API and never contain database, AI, Paystack secret, encryption or webhook credentials.

## Android
- Current Play target SDK at submission time.
- Google Play Data Safety accurately matches final SDK/data flows.
- Privacy policy accessible in-app and in Play Console.
- Account deletion available and functional.
- Use secure token storage/Keystore.
- Google Play Billing for digital subscriptions where required by Play policy.
- Backend validates Google purchase tokens before granting entitlements.

## iOS
- App Store Connect App Privacy disclosures match actual SDK/data flows.
- Privacy policy and account deletion accessible in-app.
- Keychain-backed credential/token storage.
- Apple in-app purchase/subscription implementation where required.
- Backend remains authoritative for entitlements.

## Both
- HTTPS only.
- No secrets in app bundles.
- Deep links validated server-side.
- Crash reporting must not capture financial records, credentials, payment data or raw AI prompts.
- Test registration, email verification, login, logout, reset, account deletion, subscription lifecycle, AI limits, offline/error states and accessibility on supported devices.
