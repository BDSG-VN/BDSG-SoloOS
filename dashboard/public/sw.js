const CACHE = "soloos-offline-v1";
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(["/offline.html", "/soloos-icon.svg"])),
  );
});
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("soloos-offline-") && key !== CACHE)
            .map((key) => caches.delete(key)),
        ),
      ),
  );
});
// Never cache API responses, authenticated pages, public shares, or user data.
self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate") return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match("/offline.html")),
  );
});
