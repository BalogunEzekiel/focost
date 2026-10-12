
"use strict";

// FOCOST service worker.
// Deliberately does not cache pages, financial data, API responses, or assets.

self.addEventListener("install", (event) => {
    event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
    event.waitUntil(self.clients.claim());
});

function parsePushPayload(event) {
    if (!event.data) {
        return {};
    }

    try {
        return event.data.json();
    } catch (_) {
        try {
            return { body: event.data.text() };
        } catch (_) {
            return {};
        }
    }
}

function safeNotificationUrl(value) {
    const fallback = new URL("/dashboard", self.location.origin).href;

    if (typeof value !== "string" || !value.trim()) {
        return fallback;
    }

    try {
        const url = new URL(value, self.location.origin);

        if (
            url.origin !== self.location.origin ||
            !["http:", "https:"].includes(url.protocol) ||
            url.username ||
            url.password
        ) {
            return fallback;
        }

        return url.href;
    } catch (_) {
        return fallback;
    }
}

self.addEventListener("push", (event) => {
    event.waitUntil((async () => {
        const payload = parsePushPayload(event);

        const title =
            typeof payload.title === "string" && payload.title.trim()
                ? payload.title.slice(0, 120)
                : "FOCOST Notification";

        const body =
            typeof payload.body === "string"
                ? payload.body.slice(0, 500)
                : "You have a new notification.";

        const url = safeNotificationUrl(payload.url);
        const tag =
            typeof payload.tag === "string" && payload.tag.trim()
                ? payload.tag.slice(0, 120)
                : "focost-notification";

        await self.registration.showNotification(title, {
            body,
            icon: "/static/images/pwa-192.png",
            badge: "/static/images/pwa-192.png",
            tag,
            data: { url },
            timestamp: Date.now(),
        });
    })());
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();

    event.waitUntil((async () => {
        const targetUrl = safeNotificationUrl(
            event.notification.data && event.notification.data.url
        );

        const windowClients = await self.clients.matchAll({
            type: "window",
            includeUncontrolled: true,
        });

        for (const client of windowClients) {
            try {
                const clientUrl = new URL(client.url);

                if (clientUrl.origin !== self.location.origin) {
                    continue;
                }

                if ("navigate" in client) {
                    const navigatedClient = await client.navigate(targetUrl);

                    if (navigatedClient) {
                        await navigatedClient.focus();
                        return;
                    }
                }

                await client.focus();
                return;
            } catch (_) {
                // Try another same-origin window if this one is unavailable.
            }
        }

        if (self.clients.openWindow) {
            await self.clients.openWindow(targetUrl);
        }
    })());
});
