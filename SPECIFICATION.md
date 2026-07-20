# TraceMark Frozen Specification

## Product statement

TraceMark is an educational and research-oriented still-image forensics platform for ownership verification, controlled-distribution tracing, provenance analysis, collection search, and robustness evaluation. Findings are evidence, not conclusive legal proof and not proof of a recipient's intent.

## Supported scope

- Input/output formats: JPEG, PNG, and WebP.
- Real authentication, per-user isolation, private object storage, queued processing, audit events, and versioned APIs.
- Optional visible text/logo watermark and authenticated invisible ownership or distribution watermark.
- Educational LSB engine and an independently implemented blind classical transform-domain engine.
- Exact hashing, perceptual hashing, ORB/RANSAC visual confirmation, optional C2PA evidence, internal indexed collections, and explicitly authorized public URL scanning.
- Robustness experiments, HTML/PDF/JSON reports, responsive accessible UI, reproducible local deployment, seed/demo assets, automated tests, and security validation.

Out of scope are video/audio, unrestricted internet search, authenticated scraping, access-control bypasses, paid core APIs, blockchain marketing, and personal information embedded in pixels.

## Core behavior

1. A user can register an image, inspect safe metadata/fingerprints, configure protection, generate and download a protected output, and inspect PSNR/SSIM/file-size/pixel-difference evidence.
2. A user can create separately tokenized distribution copies and later recover an authorized distribution mapping without the original image.
3. Extraction is blind, returns diagnostics, and accepts identifiers only after error correction and HMAC verification.
4. Verification layers exact hashes, watermark evidence, perceptual distances, local features, and provenance into deterministic evidence classifications without a fabricated aggregate score.
5. Users can create/index/search collections from images, batches, safe ZIP files, generated demo data, or query uploads.
6. Users can scan only direct public images or a single explicitly submitted public page with DNS, redirect, robots, size, timeout, and content restrictions.
7. Users can run repeatable quick, standard, aggressive, or custom transformations and export measured results and reports.
8. Long operations use queued/running/completed/failed/cancelled jobs with progress and controlled errors.

## Security requirements

Argon2id credentials, opaque cookie sessions, CSRF protection, restricted CORS, rate limiting, generic auth failures, authorization-scoped queries, MIME/content validation, decompression-bomb limits, safe storage keys, metadata removal, archive traversal/expansion controls, SSRF defenses, escaped reports, secret separation, private buckets, timeouts, quotas, and temporary-file cleanup are mandatory.

## Definition of done

Completion requires: clean documented startup; working authentication; visible, LSB, and robust blind watermark round trips; forged/wrong-key rejection; unique distribution recovery; exact/perceptual/local-feature evidence; collection indexing/search; safe URL scan; real robustness results including negative controls; report exports; cross-user isolation; real-UI end-to-end coverage; security and production builds passing; complete required documentation; no fake core feature or mandatory TODO; honest limitations; and an accurate final `STATUS.md`.

