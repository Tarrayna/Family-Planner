// Family Planner service worker.
// Strategy: app shell cached for offline boot; API responses are
// network-first with a cached fallback so the TV can show the last known
// plan when the server is unreachable.

const SHELL = 'planner-shell-v1';
const DATA = 'planner-data-v1';
const SHELL_FILES = ['/', '/index.html', '/manifest.json'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL && k !== DATA).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  // Never cache the event stream.
  if (url.pathname.startsWith('/api/stream')) return;

  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(DATA).then((c) => c.put(e.request, copy));
          return res;
        })
        .catch(() =>
          caches.match(e.request).then(
            (hit) =>
              hit ||
              new Response(JSON.stringify({ stale: true, error: 'offline' }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' },
              })
          )
        )
    );
    return;
  }

  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
