// Minimal service worker — presence satisfies PWA install requirements.
// No fetch interception; all network requests flow through normally.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", () => self.clients.claim());
