/* sw.js — TTS Studio Service Worker
 * Strategie: Cache-First für App-Shell, Network-Only für API-Calls.
 * API-Requests (openai.com, localhost) werden nie gecacht.
 */

const CACHE_NAME = 'tts-studio-v1';

// App-Shell: alles was zum Laden der UI nötig ist
const SHELL_ASSETS = [
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

// ── INSTALL: Shell in Cache legen ──────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // addAll schlägt fehl wenn eine Datei nicht erreichbar ist —
      // einzeln cachen damit ein fehlender Asset nicht alles blockiert
      return Promise.allSettled(
        SHELL_ASSETS.map(url => cache.add(url).catch(() => {}))
      );
    }).then(() => self.skipWaiting())
  );
});

// ── ACTIVATE: alte Caches aufräumen ───────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// ── FETCH: Routing-Logik ───────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 1. API-Calls niemals cachen (OpenAI, lokaler Server, alle externen Hosts)
  if (
    url.hostname !== self.location.hostname &&
    url.hostname !== 'localhost' &&
    url.hostname !== '127.0.0.1' &&
    !url.hostname.endsWith(self.location.hostname)
  ) {
    // Auch Google Fonts und ähnliches durchlassen ohne Cache
    event.respondWith(fetch(event.request));
    return;
  }

  // 2. Localhost-Requests (lokaler TTS-Server) immer direkt netzwerk
  if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
    event.respondWith(fetch(event.request));
    return;
  }

  // 3. App-Shell: Cache-First, Fallback Network
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        // Nur erfolgreiche GET-Antworten cachen
        if (
          event.request.method === 'GET' &&
          response.status === 200 &&
          response.type !== 'opaque'
        ) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // Offline-Fallback: index.html für Navigation
        if (event.request.mode === 'navigate') {
          return caches.match('./index.html');
        }
      });
    })
  );
});
