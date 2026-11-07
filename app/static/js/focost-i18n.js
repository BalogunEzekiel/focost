/* Shared localization runtime for FOCOST legacy and newly localized components. */
(function (window, document) {
  "use strict";
  const config = window.FOCOST_I18N || {};
  const translations = config.translations || {};
  const englishFallback = window.FOCOST_ENGLISH || {};
  const textKeys = config.textKeys || {};

  function t(key, fallback) {
    return translations[key] || englishFallback[key] || fallback || key;
  }

  function applyTextNodes(root) {
    const scope = root || document;
    const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || /^(SCRIPT|STYLE|TEXTAREA|INPUT|CODE|PRE)$/i.test(parent.tagName)) return NodeFilter.FILTER_REJECT;
        const source = node.nodeValue || "";
        const trimmed = source.trim();
        return textKeys[trimmed] ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const source = node.nodeValue || "";
      const leading = source.match(/^\s*/)?.[0] || "";
      const trailing = source.match(/\s*$/)?.[0] || "";
      node.nodeValue = leading + t(textKeys[source.trim()], source.trim()) + trailing;
    });
  }

  function apply(root) {
    const scope = root || document;
    if (scope.matches && scope.matches("[data-i18n]")) {
      const key = scope.getAttribute("data-i18n");
      const textNode = Array.from(scope.childNodes).find((child) => child.nodeType === Node.TEXT_NODE);
      if (textNode) textNode.textContent = t(key, textNode.textContent);
    }
    scope.querySelectorAll?.("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      const textNode = Array.from(node.childNodes).find((child) => child.nodeType === Node.TEXT_NODE);
      if (textNode) textNode.textContent = t(key, textNode.textContent);
    });
    scope.querySelectorAll?.("[data-i18n-placeholder]").forEach((node) => {
      node.setAttribute("placeholder", t(node.getAttribute("data-i18n-placeholder"), node.getAttribute("placeholder")));
    });
    scope.querySelectorAll?.("[data-i18n-title]").forEach((node) => {
      node.setAttribute("title", t(node.getAttribute("data-i18n-title"), node.getAttribute("title")));
    });
    scope.querySelectorAll?.("[data-i18n-aria-label]").forEach((node) => {
      node.setAttribute("aria-label", t(node.getAttribute("data-i18n-aria-label"), node.getAttribute("aria-label")));
    });
    scope.querySelectorAll?.("[data-i18n-value]").forEach((node) => {
      node.value = t(node.getAttribute("data-i18n-value"), node.value);
    });
    scope.querySelectorAll?.("[data-i18n-alt]").forEach((node) => {
      node.setAttribute("alt", t(node.getAttribute("data-i18n-alt"), node.getAttribute("alt")));
    });
    applyTextNodes(scope);
  }

  window.FOCOST = window.FOCOST || {};
  window.FOCOST.t = t;
  window.FOCOST.applyTranslations = apply;
  window.FOCOST.setLanguage = function (language, locale, nextTranslations) {
    config.language = language || "en";
    config.locale = locale || config.locale || "en-NG";
    if (nextTranslations && typeof nextTranslations === "object") {
      Object.keys(translations).forEach((key) => delete translations[key]);
      Object.assign(translations, nextTranslations);
    }
    document.documentElement.lang = config.language;
    document.documentElement.dir = config.direction || "ltr";
    apply(document);
    document.dispatchEvent(new CustomEvent("focost:language-changed", {
      detail: { language: config.language, locale: config.locale }
    }));
  };
  document.addEventListener("DOMContentLoaded", () => {
    apply(document);
    const observer = new MutationObserver((mutations) => mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => { if (node.nodeType === 1) apply(node); });
    }));
    observer.observe(document.body, { childList: true, subtree: true });
  });
})(window, document);
