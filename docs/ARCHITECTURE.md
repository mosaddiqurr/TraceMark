# Focused architecture

React/TypeScript/Vite → FastAPI → bounded spawned image processor → existing independent watermark/forensic engine.

SQLite retains only private anonymous workspace capabilities and trace descriptors. The API holds transient protected output bytes and report snapshots in bounded memory. Netlify, Vercel or equivalent static hosting serves the frontend build. The public API prefix is set through build-time VITE_API_URL.

No original image store, PostgreSQL, Redis, MinIO, Dramatiq, account service, crawler or queue is needed. User-submitted link checks reuse the bounded safe fetcher inside the API process. One native API process and a persistent private SQLite directory cover the product.

The browser workspace cookie is random and HttpOnly. Only its keyed digest is stored. Every registry lookup and output/report download is owner-scoped. CSRF and exact origin checks protect mutations. Expiry cascades trace deletion.

The parent owns shared-memory buffers and provenance temporary directories and removes them after child completion/termination. Processing admission is bounded and immediate; a hard deadline terminates CPU work. See [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html) for the process lifecycle primitives.

Descriptor comparison reuses pHash-family fingerprints and real ORB/ratio-test/RANSAC checks without saving original pixels. VERIFIED requires HMAC authentication plus an authorized trace. The original classical robust and LSB algorithms remain independent of the API.

Run one API process/replica. Memory artifacts, admission and rate windows are not shared. An external trusted ingress must cover distributed abuse control if the design is extended. Default SQLite quotas make this a modest deployment, not an enterprise service.

