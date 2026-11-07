/* FOCOST shared currency formatting and conversion runtime. */
(function (window, document) {
  "use strict";
  const config = window.FOCOST_I18N || {};
  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || "";

  function formatMoney(amount, currency = config.currency || "NGN", options = {}) {
    const value = Number(amount);
    if (!Number.isFinite(value)) return "—";
    return new Intl.NumberFormat(config.locale || "en-NG", {
      style: "currency", currency,
      minimumFractionDigits: options.minimumFractionDigits ?? 2,
      maximumFractionDigits: options.maximumFractionDigits ?? 2,
      currencyDisplay: options.currencyDisplay || "symbol"
    }).format(value);
  }

  async function convertMoney(amount, fromCurrency = config.baseCurrency || "NGN", toCurrency = config.currency || "NGN", date = null) {
    const response = await fetch("/settings/currency/convert", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "Accept": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify({ amount, from_currency: fromCurrency, to_currency: toCurrency, ...(date ? { date } : {}) })
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) {
      const error = new Error(payload.message || "Currency conversion is unavailable.");
      error.code = payload.code || "CURRENCY_CONVERSION_FAILED";
      throw error;
    }
    return { ...payload, formatted: formatMoney(payload.converted_amount, payload.to_currency) };
  }

  window.FOCOST = window.FOCOST || {};
  window.FOCOST.formatMoney = formatMoney; // Formats an amount already denominated in the requested currency.
  window.FOCOST.convertMoney = convertMoney; // Converts source amount, then formats it.
})(window, document);
