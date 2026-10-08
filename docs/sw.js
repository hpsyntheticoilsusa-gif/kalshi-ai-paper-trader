// App shell only; use network data when online, never cache market snapshots.
const CACHE='kalshi-paper-shell-v1';
const ROOT='/kalshi-ai-paper-trader/';
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll([
    ROOT, ROOT+'paper-ticket.html', ROOT+'icon-192.png', ROOT+'icon-512.png', ROOT+'manifest.webmanifest'
  ])).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET'||url.origin!==self.location.origin)return;
  if(url.pathname.endsWith('.json')||url.pathname.endsWith('.csv'))return; // Always obtain fresh data.
  if(event.request.mode==='navigate'){
    event.respondWith(fetch(event.request).catch(()=>caches.match(event.request,{ignoreSearch:true}).then(response=>response||caches.match(ROOT))));
  }
});
