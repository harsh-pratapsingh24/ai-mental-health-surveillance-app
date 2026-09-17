const CACHE_NAME = "aegismind-v1";
const STATIC_ASSETS = [
  "/",
  "/static/css/mobile.css",
  "/static/js/app.js",
  "/static/manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // API requests: network-only
  if (request.url.includes("/api/")) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(
          JSON.stringify({ error: "offline", message: "You appear to be offline." }),
          { headers: { "Content-Type": "application/json" }, status: 503 }
        );
      })
    );
    return;
  }

  // Static assets: cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      return cached || fetch(request).then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        return response;
      });
    })
  );
});
