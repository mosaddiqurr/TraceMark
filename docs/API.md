# Focused API v1

Base: `/api/v1`. JSON errors contain a safe code/message and correlation ID. No image bytes or sensitive keys appear in logs. Binary responses use private/no-store caching.

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Process liveness |
| GET | /ready | SQLite readiness |
| POST | /workspace | Create/rehydrate an anonymous HttpOnly browser workspace; return CSRF and configured limits |
| DELETE | /workspace | Clear only this workspace's private traces and memory artifacts |
| POST | /protect | Multipart image and optional reference_label; authenticated blind watermark and output summary |
| GET | /outputs/{random_artifact_id}/download | Workspace-scoped transient protected PNG |
| POST | /verification | Multipart image; automatic independent evidence checks and report link |
| GET | /reports/{random_artifact_id}/download?format=json or pdf | Scoped authenticated report export |

All mutating processing/clear requests require the workspace cookie and `X-CSRF-Token`. Bootstrap validates the exact Origin. CORS is credentialed and explicitly allowlisted. Missing/foreign transient records return 404; expired/missing workspaces return 401.

Protection returns identifier, reference label, sanitized filename, dimensions, source hash, profile, measured quality, timestamp, download URL/expiry and trace expiry. Source/output pixels are not stored in SQLite. Labels are private registry metadata; each protected copy gets a new opaque identifier.

Verification returns `verified`, `classification`, authorized identifier/label/source timestamp when available, file details, watermark integrity/ECC, exact-hash kind, visual checks, optional provenance state, limitations, timestamp and report download/expiry.

Classifications: valid_ownership_watermark, valid_distribution_watermark, authenticated_unresolved, invalid_authenticated_payload, exact_registered_hash, possible_visual_match, no_evidence. Only the first two produce `verified=true`. Unknown/foreign tokens remain unresolved and do not expose private mappings. Similarity thresholds are heuristic; no calibrated population confidence is claimed.

Limits and errors: 413 oversized body/file; 422 invalid/corrupt/animated/insufficient-capacity input; 403 invalid CSRF/origin; 429 rate limiting; 503 processor/buffer capacity; 504 hard processing timeout. Failed processing never returns a success result or fake identifier.

Retired accounts, assets, collections, scanners, search, benchmark, history and job endpoints are not exposed. JSON reports use canonical HMAC-SHA256 snapshots with a separate key. They are deployment-authenticated evidence, not public-key certificates or legal proof.

