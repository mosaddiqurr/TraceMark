# Threat Model

## Assets and trust boundaries

Protected assets, originals, distribution mappings, watermark/report keys, sessions, reports, audit events, and user identity are sensitive. Browser, reverse proxy, API, Redis, worker, PostgreSQL, MinIO, uploaded bytes, archives, and public network fetches are separate trust boundaries.

## Threats and required mitigations

| Threat | Mitigation |
|---|---|
| Malicious/corrupt/decompression-bomb image | Byte, pixel, frame, MIME and decode limits; isolated timed worker; metadata sanitization |
| Path traversal or unsafe storage | Random object keys; no user paths; canonical archive extraction checks |
| ZIP slip/expansion | Entry/count/size/ratio limits; no symlinks, absolute paths, traversal, or nested archives |
| IDOR/unauthorized download | Owner-scoped queries and authorization checks before every object operation |
| Forged/wrong-key payload | Reed-Solomon correction followed by constant-time HMAC verification; never trust CRC alone |
| Stored XSS/report injection | React escaping, server validation, CSP, HTML/PDF escaping, safe filenames |
| SQL injection | SQLAlchemy bound statements and allow-listed sorting/filtering |
| CSRF/CORS/session theft | CSRF token, HttpOnly/SameSite/Secure cookies, restricted origins, rotation and logout invalidation |
| Brute force/job denial of service | Per-IP/account rate limits, per-user quotas, bounded queues, concurrency and timeout limits |
| SSRF/redirect/DNS rebinding | HTTP(S) only, public-address validation, DNS pinning, peer verification, manual redirects, response caps |
| Unsafe report replay/tampering | Immutable evidence snapshots and versioned HMAC-authenticated JSON exports |
| Secret leakage | Mounted/env secrets, key versions only in DB, redacted structured logs, private object buckets |
| Stale temporary data | Unique job directories, `finally` cleanup, periodic abandoned-job cleanup |

Security tests must exercise each mitigation before release.

