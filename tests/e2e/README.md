# FOCOST browser regression tests

These Playwright tests run against a **staging** FOCOST instance and an authorized test account.
They do not create or mutate production records other than the user's selected display preferences.

```powershell
cd tests/e2e
npm install
npx playwright install chromium
$env:FOCOST_E2E_BASE_URL = "http://127.0.0.1:5000"
$env:FOCOST_E2E_EMAIL = "staging-test-user@example.com"
$env:FOCOST_E2E_PASSWORD = "your-staging-test-password"
npm run test:e2e
```

Use a dedicated staging database and account. The test intentionally skips when credentials are not supplied.
