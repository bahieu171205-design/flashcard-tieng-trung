// Lưu sẵn các file của app để mở được khi không có mạng.
// Khi có bản mới: service worker mới tải trọn bộ file mới về, rồi trang tự tải lại (xem index.html).
// Luôn hỏi lại máy chủ (bỏ qua bộ nhớ đệm 10 phút của trình duyệt) để bản mới tới ngay.
const CACHE = "flashcard-zh-v5";
const FILES = ["./", "./index.html", "./vocab.js", "./manifest.webmanifest",
               "./icons/icon-180.png", "./icons/icon-192.png", "./icons/icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES.map(f => new Request(f, { cache: "reload" })))));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async cache => {
    const cached = await cache.match(e.request, { ignoreSearch: true });
    // không truyền thẳng e.request (yêu cầu điều hướng không cho đổi tuỳ chọn cache)
    const fresh = fetch(e.request.url, { cache: "no-cache", credentials: "same-origin" }).then(res => {
      if (res.ok) cache.put(e.request, res.clone());
      return res;
    }).catch(() => cached);
    return cached || fresh;
  }));
});
