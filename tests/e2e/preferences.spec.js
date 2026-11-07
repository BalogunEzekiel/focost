const { test, expect } = require('@playwright/test');

const email = process.env.FOCOST_E2E_EMAIL;
const password = process.env.FOCOST_E2E_PASSWORD;

test.skip(!email || !password, 'Set FOCOST_E2E_EMAIL and FOCOST_E2E_PASSWORD for an authorized staging account.');

test('currency and language preferences persist and initialize shared browser runtimes', async ({ page }) => {
  await page.goto('/login');
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.locator('form button[type="submit"], form input[type="submit"]').first().click();
  await page.waitForURL(/dashboard/);

  const settingsTrigger = page.locator('[data-bs-target="#settingsModal"]').first();
  await settingsTrigger.click();
  await expect(page.locator('#settingsModal')).toBeVisible();
  await page.locator('[data-bs-target="#focostRegional"]').click();
  await page.locator('#preferredCurrency').selectOption('GBP');
  await page.locator('#preferredLanguage').selectOption('ha');
  await page.locator('#saveDashboardPreferences').click();
  await expect(page.locator('#settingsModal')).toContainText(/saved successfully/i);

  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ha');
  await expect(page.locator('html')).toHaveAttribute('data-currency-code', 'GBP');

  const runtime = await page.evaluate(async () => {
    const response = await fetch('/settings/api', { credentials: 'same-origin' });
    const payload = await response.json();
    return {
      ok: response.ok,
      currency: payload.preferences.currency,
      language: payload.preferences.language,
      formatter: window.FOCOST.formatMoney(1234.5, 'GBP'),
      translatedLabel: window.FOCOST.t('total_income'),
    };
  });

  expect(runtime.ok).toBeTruthy();
  expect(runtime.currency).toBe('GBP');
  expect(runtime.language).toBe('ha');
  expect(runtime.formatter).toContain('£');
  expect(runtime.translatedLabel).not.toBe('Total Income');
});

test('core authenticated financial pages render without server errors', async ({ page }) => {
  await page.goto('/login');
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.locator('form button[type="submit"], form input[type="submit"]').first().click();
  await page.waitForURL(/dashboard/);

  for (const path of ['/dashboard/', '/income/', '/expense/', '/budget/', '/goal/', '/assets/', '/reports/']) {
    const response = await page.goto(path);
    expect(response, `No response for ${path}`).not.toBeNull();
    expect(response.status(), `${path} returned ${response.status()}`).toBeLessThan(500);
  }
});
