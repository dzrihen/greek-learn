/* Greek Learn v8 — SRS, conversation, grammar, cached audio */
const CACHE_NAME = "greek-learn-v8";
const APP_SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./css/app.css",
  "./js/speech.js",
  "./js/progress.js",
  "./js/srs.js",
  "./js/engine.js",
  "./js/conversation.js",
  "./js/app.js",
  "./data/meta.js",
  "./data/files.js",
  "./data/curriculum.js",
  "./data/conversations.js",
  "./data/grammar.js",
  "./data/a1-part1.js",
  "./data/a1-part2.js",
  "./data/a2-part1.js",
  "./data/a2-part2.js",
  "./data/b1-part1.js",
  "./data/b1-part2.js",
  "./data/b2-part1.js",
  "./data/b2-part2.js",
  "./data/c1-part1.js",
  "./data/c1-part2.js",
  "./data/c2-part1.js",
  "./data/c2-part2.js",
  "./audio/manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) {
        if (/\.(js|css|webmanifest)$/.test(url.pathname)) {
          fetch(req).then((res) => {
            if (res && res.ok) {
              caches.open(CACHE_NAME).then((c) => c.put(req, res.clone()));
            }
          }).catch(() => {});
        }
        return cached;
      }
      return fetch(req).then((res) => {
        if (res && res.ok && (req.mode === "navigate" || isCacheable(url.pathname))) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
        }
        return res;
      }).catch(() => {
        if (req.mode === "navigate") return caches.match("./index.html");
        return caches.match(req);
      });
    })
  );
});

function isCacheable(pathname) {
  const p = pathname.replace(/\/+$/, "") || "/";
  return (
    p.endsWith("/index.html") ||
    p.endsWith("/manifest.webmanifest") ||
    p.endsWith("/sw.js") ||
    p.includes("/icons/") ||
    p.includes("/css/") ||
    p.includes("/js/") ||
    p.includes("/data/") ||
    p.includes("/audio/")
  );
}
