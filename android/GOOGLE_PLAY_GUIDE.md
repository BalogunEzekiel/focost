# FOCOST Android / Google Play Publishing Guide

## Recommended architecture

Keep the existing FOCOST backend as the authoritative service:

```text
FOCOST Android App
        |
        | HTTPS / JSON API
        v
FOCOST Python/Flask Backend
        |
        +---- Database
        +---- AI providers
        +---- Subscription domain
        +---- Payment providers
```

Do not put database credentials, AI provider secrets, Paystack secret keys, webhook secrets or privileged API credentials in the Android application.

## 1. Android project

Use Android Studio with Kotlin and a current stable Android Gradle Plugin/JDK combination compatible with the target SDK.

Recommended application ID:

```text
ai.focost.app
```

Before publishing, verify that the ID is available and permanently choose it because changing an Android application ID creates a different Play application identity.

## 2. Native vs web wrapper

For a finance product, the preferred long-term architecture is a native Android client consuming FOCOST's authenticated backend API.

A Trusted Web Activity can be considered for a fast initial public web-to-mobile distribution, but it should not be used as a shortcut around Google Play payment rules.

## 3. Backend API

The Android client should call HTTPS endpoints such as:

```text
/auth/*
/ai/*
/billing/*
/profile/*
/assets/*
/notifications/*
```

For a production native client, add a versioned API namespace such as `/api/v1/` and return stable JSON contracts rather than coupling Android screens to HTML templates.

## 4. Authentication

Use short-lived access credentials with secure refresh/session handling. Never store passwords or server secrets in plaintext SharedPreferences.

Use Android Keystore-backed secure storage for tokens where appropriate.

Require TLS and reject insecure HTTP production endpoints.

## 5. Deep links

Configure Android App Links for verified HTTPS domains. Use deep links for:

- authentication completion;
- subscription status;
- notification actions;
- financial reports;
- goal/asset details.

Validate every deep-link identifier server-side. Never treat a deep-link URL as proof of payment.

## 6. Payments

The FOCOST web application can continue using Paystack for web subscriptions.

For a Play-distributed Android application, do **not** simply put the web Paystack checkout inside the Android app for digital FOCOST subscriptions. Google Play's payments policy generally requires Google Play Billing for digital subscriptions and financial-management software sold inside a Play-distributed app, subject to the policy's exceptions and regional programs. citeturn1search0turn1search1

Therefore implement a provider-neutral subscription layer:

```text
Subscription domain
   |
   +-- Paystack provider (web)
   |
   +-- Google Play provider (Android)
```

The existing `provider` field in FOCOST subscription/payment records is designed to support this separation.

For Google Play purchases, the Android client should send the Google purchase token to the backend. The backend must validate the purchase with Google's APIs before granting entitlements. The client should never grant premium access solely because a local Android callback says a purchase succeeded.

## 7. App signing

Use Play App Signing. Keep upload-key material secure and backed up separately from source code.

Never commit:

- `.jks` / `.keystore` files;
- signing passwords;
- Play service-account JSON credentials;
- API secrets.

Google requires apps to be digitally signed; Play Console supports Play App Signing. citeturn0search8

## 8. Target SDK — current 2026 requirement

As of August 31, 2026, new Android apps and updates submitted to Google Play must target **Android 16 / API 36 or higher**. Existing apps must target Android 15 / API 35 or higher to remain available to new users on newer Android versions. Google also describes an extension mechanism through November 1, 2026 for affected apps. citeturn0search0turn0search5

Set the release build's target SDK to the current Play requirement at submission time and re-check Google's policy before every release.

## 9. Build configuration

The release build should define:

- `applicationId`
- `minSdk`
- `targetSdk`
- `versionCode`
- `versionName`
- release signing configuration
- production backend URL

Increase `versionCode` for every Play update. Google Play requires version codes to increase between releases. citeturn0search8

## 10. Permissions

Request only permissions genuinely required by FOCOST. A normal finance application should not request broad device permissions without a feature requiring them.

If profile pictures are selected, use the modern Android photo picker where possible rather than requesting broad media access.

## 11. Branding

Prepare:

- launcher icon;
- adaptive icon;
- splash screen;
- app name;
- monochrome icon where appropriate;
- privacy policy URL;
- support contact;
- store screenshots;
- feature graphic.

Keep the Android visual identity consistent with the FOCOST web application.

## 12. Play Console listing

Prepare:

- short description;
- full description;
- app category;
- screenshots for supported form factors;
- privacy policy;
- developer contact details;
- app access instructions for reviewers;
- content rating;
- Data Safety declarations;
- subscription pricing and renewal disclosures.

Google requires subscription offers to be clear about price, billing frequency, renewal terms and material conditions. citeturn1search4

## 13. Testing sequence

Use Play Console tracks in this order:

1. Internal testing
2. Closed testing
3. Production rollout

Test at minimum:

- fresh install;
- registration;
- login/logout;
- expired session;
- subscription purchase;
- subscription renewal;
- cancellation;
- payment failure;
- entitlement restoration;
- AI usage limits;
- notifications;
- profile/avatar;
- offline/network failure;
- deep links;
- dark mode;
- different screen sizes.

## 14. Crash and analytics monitoring

Use a production crash-reporting service and privacy-conscious analytics. Do not record financial transaction contents, AI prompts, payment credentials or sensitive personal financial data in analytics events.

Useful non-sensitive events include:

```text
app_open
login_success
subscription_screen_view
subscription_purchase_started
subscription_purchase_verified
ai_request_started
ai_request_completed
notification_opened
```

## 15. Play policy and payment review

Google Play's payments policy explicitly includes subscription services and financial-management software among digital functionality generally requiring Play Billing when sold in a Play-distributed app, unless a listed exception/program applies. citeturn1search0turn1search1

Because Play policies and regional billing programs can change, re-check the official Play Console policy immediately before submission.

## 16. Release checklist

- [ ] Production backend uses HTTPS
- [ ] No server secrets in APK/AAB
- [ ] Release signing configured
- [ ] Play App Signing configured
- [ ] Target SDK 36+ for a new app/update under the August 31, 2026 rule
- [ ] Version code incremented
- [ ] Privacy policy published
- [ ] Data Safety completed accurately
- [ ] App access instructions supplied
- [ ] Subscription terms clearly displayed
- [ ] Google Play Billing implemented for in-app digital subscriptions where required
- [ ] Backend verifies purchase tokens
- [ ] Premium access is server-authoritative
- [ ] Internal testing passed
- [ ] Closed testing passed
- [ ] Production monitoring enabled
