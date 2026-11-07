// Service worker minimo: rende la webapp installabile e mostra l'ultima versione dell'interfaccia
// anche offline. I dati (/api) non vengono mai messi in cache: sono sempre quelli veri.
const CACHE = "money-shell-v1";
self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/"]))));
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api")) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request).then((r) => r || caches.match("/"))));
});
