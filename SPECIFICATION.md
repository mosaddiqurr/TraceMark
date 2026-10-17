# TraceMark Focused Specification

Updated: 2026-10-05. This user-directed scope replaces the original enterprise specification.

## Purpose

Protect a still image with an authenticated, opaque identifier; download the protected copy; later verify an image, inspect trace evidence, and export a concise report. Evidence does not prove legal ownership, authorship, recipient intent, or who shared a file.

## Product

- Home, Protect, Verify, About. No accounts, teams, dashboards, collections, scanners, history, job UI or benchmark UI.
- JPEG, PNG and WebP still-image inputs. Lossless PNG protected output.
- Existing blind Haar-DWT / DCT / QIM engine; error correction and HMAC acceptance. Labels never enter pixels.
- Optional private reference/recipient label gives a separately tokenized distribution copy.
- Bounded extraction across existing strengths 32/36/42 and the existing educational LSB baseline.
- Authentication, exact SHA-256 hashes, perceptual fingerprints, actual ORB/RANSAC checks and optional C2PA availability remain separate evidence.
- VERIFIED requires an authenticated watermark and a trace in the current private browser workspace. Exact hashes and visual similarity alone never suffice. Authentic unresolved marks are reported explicitly.
- Generated sample workflow and PDF/JSON reports attached to each result.

## Architecture and privacy

One React/TypeScript/Vite client, one native FastAPI process, a persistent private SQLite metadata directory. No PostgreSQL, Redis, S3/MinIO, external worker or queue dependencies. Private anonymous HttpOnly cookies and CSRF preserve isolation without accounts.

Uploaded pixels are discarded. Protected downloads and report snapshots remain in bounded private memory for 15 minutes by default. Identifiers, source/output hashes, compact visual descriptors, private labels and timestamps persist until the workspace expires (30 days by default) or is explicitly cleared. Temporary C2PA files are parent-managed and cleaned even after worker termination.

## Security

Strict signatures/content types, byte/pixel/dimension/frame limits, bounded request bodies including chunked uploads, safe filenames, timed isolated processing, bounded concurrency, fixed registry quotas, exact CORS, CSRF, scoped downloads and reports, stable safe errors, sensitive-input-free logs, distinct environment secrets and a least-privileged execution account and host resource limits.

## Acceptance

Real Protect → Download → Re-upload → Verify → Evidence → Export journey; honest invalid/unmarked/altered/offline states; private workspace isolation; embed/extract/wrong-key/forged-payload tests; frontend accessibility/layout at 1440/1366/768/390; lint/format/types/build, dependency audits and measured CLI benchmark. Direct deployment acceptance also requires native process restart/persistence checks and production-build browser journeys. Report unavailable validation honestly.
