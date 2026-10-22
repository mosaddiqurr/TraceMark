# Architecture

React/TypeScript/Vite → FastAPI → bounded spawned image processor → existing independent watermark/forensic engine.

SQLite retains only private anonymous workspace capabilities and trace descriptors. The API holds transient protected output bytes and report snapshots in bounded memory. Netlify, Vercel or equivalent static hosting serves the frontend build. The public API prefix is set through build-time VITE_API_URL.

No original image store, PostgreSQL, Redis, MinIO, Dramatiq, account service, crawler or queue is needed. User-submitted link checks reuse the bounded safe fetcher inside the API process. One native API process and a persistent private SQLite directory cover the product.

The browser workspace cookie is random and HttpOnly. Only its keyed digest is stored. Every registry lookup and output/report download is owner-scoped. CSRF and exact origin checks protect mutations. Expiry cascades trace deletion.

The parent owns shared-memory buffers and provenance temporary directories and removes them after child completion/termination. Processing admission is bounded and immediate; a hard deadline terminates CPU work. See [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html) for the process lifecycle primitives.

Descriptor comparison reuses pHash-family fingerprints and real ORB/ratio-test/RANSAC checks without saving original pixels. VERIFIED requires HMAC authentication plus an authorized trace. The original classical robust and LSB algorithms remain independent of the API.

Run one API process/replica. Memory artifacts, admission and rate windows are not shared. An external trusted ingress must cover distributed abuse control if the design is extended. Default SQLite quotas make this a modest deployment, not an enterprise service.

## Data model

| Table | Stored fields |
|---|---|
| browser_workspaces | Random workspace ID, HMAC digest of capability cookie, CSRF value, absolute expiry |
| image_traces | Opaque watermark identifier, owner workspace ID, safe source filename, private label, payload kind, original/output SHA-256, compact fingerprint/ORB descriptor, UTC creation timestamp |

Trace owner is a cascading foreign key. All trace queries filter the active workspace. No image bytes, master/report keys or plaintext cookie values are stored. Descriptors are private derived data, not anonymized.

Protected PNGs and sealed reports use random artifact IDs in private bounded process memory with independent expiry. Artifact IDs are not watermark identifiers. Downloads require the owner cookie. Restarting the API loses transient artifacts while SQLite traces survive.

Expired workspace deletion and explicit clearing remove logical records. Disk pages/WAL/backup copies can retain remnants; no secure-erasure claim is made.

## API v1

Base: `/api/v1`. JSON errors contain a safe code/message and correlation ID. No image bytes or sensitive keys appear in logs. Binary responses use private/no-store caching.

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Process liveness |
| GET | /ready | SQLite readiness |
| POST | /workspace | Create/rehydrate an anonymous HttpOnly browser workspace; return CSRF and configured limits |
| DELETE | /workspace | Clear only this workspace's private traces and memory artifacts |
| GET | /workspace/export | Signed JSON backup of this workspace's trace records |
| POST | /workspace/import | Restore a signed backup into this workspace; tampered or foreign files are rejected |
| POST | /protect | Multipart image and optional reference_label; authenticated blind watermark and output summary |
| GET | /outputs/{random_artifact_id}/download | Workspace-scoped transient protected PNG |
| POST | /verification | Multipart image; automatic independent evidence checks and report link |
| POST | /verification/link | Public image or page URL; up to eight fetched images verified, strongest result first |
| GET | /reports/{random_artifact_id}/download?format=json or pdf | Scoped authenticated report export |

All mutating requests require the workspace cookie and `X-CSRF-Token`. Bootstrap validates the exact Origin. CORS is credentialed and explicitly allowlisted. Missing/foreign transient records return 404; expired/missing workspaces return 401.

Protection returns identifier, reference label, sanitized filename, dimensions, source hash, profile, measured quality, timestamp, download URL/expiry and trace expiry. Labels are private registry metadata; each protected copy gets a new opaque identifier.

Verification returns `verified`, `classification`, authorized identifier/label/source timestamp when available, file details, watermark integrity/ECC, exact-hash kind, visual checks, optional provenance state, limitations, timestamp and report download/expiry. Link checks add the source URL to the evidence and report.

Classifications: valid_ownership_watermark, valid_distribution_watermark, authenticated_unresolved, invalid_authenticated_payload, exact_registered_hash, possible_visual_match, no_evidence. Only the first two produce `verified=true`. Unknown/foreign tokens remain unresolved and do not expose private mappings. Similarity thresholds are heuristic; no calibrated population confidence is claimed.

Limits and errors: 413 oversized body/file; 422 invalid/corrupt/animated/insufficient-capacity input or refused link; 403 invalid CSRF/origin; 429 rate limiting; 503 processor/buffer capacity; 504 hard processing timeout. Failed processing never returns a success result or fake identifier.

JSON reports and trace backups use HMAC-SHA256 under the report key with separate domains. They are deployment-authenticated evidence, not public-key certificates or legal proof.
