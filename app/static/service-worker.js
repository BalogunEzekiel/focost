"use strict";

// FOCOST baseline service worker.
// Deliberately does not cache pages, financial data, API responses, or assets.

self.addEventListener("install", (event) => {
    event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
    event.waitUntil(self.clients.claim());
});
