# Evaluation

The release uses the v3 canonical and v2 robust DWT/DCT/QIM engines, an HMAC/ECC payload, the LSB comparison baseline, exact SHA-256 and actual perceptual/ORB/RANSAC measurements.

## Acceptance model

A positive result requires successful payload integrity verification and a matching trace owned by the active anonymous workspace. A hash or similarity match alone must remain NOT VERIFIED. Wrong keys, forged authentication, unknown identifiers, foreign workspaces and expired mappings must never expose a private identifier or reference label.

The real journey protects an image, saves the delivered PNG, reuploads those exact bytes, checks the recovered identifier/hash and downloads both report formats. Backend regressions also examine JPEG recompression, resizing (which must verify with v3) and cropping (which must not). Link checks are tested against a fake fetcher, including page parsing, ranking, refusal of non-public addresses, and signed trace export/import with tampering. Every successful protection independently extracts its saved PNG before returning it.

## Engine benchmark

Run `make benchmark` or `./scripts/benchmark.ps1` after setup.

The deterministic generator writes local, licence-safe fixtures plus their seed/provenance manifest to `datasets/generated`. The quick profile selects the first four sorted images and measures the v3, v2 and LSB engines against clean output, JPEG 85, a 75% resize, a 50% resize followed by JPEG 80, a 150% upscale, WebP 80 and a 5% center crop. Standard uses all generated images and also JPEG 70 and 60. The benchmark uses its documented public test key, never production keys.

Results are written to `artifacts/benchmark-results.json`: every attempt, authenticated extraction, corrected symbols, repetitions, duration, failure reason and PSNR/SSIM against the protected image where dimensions match. Unmarked inputs are checked with every engine. Exports use strict JSON; infinite PSNR for identical pixels and metrics for incomparable dimensions are `null`. The release snapshot is `docs/benchmark-quick.json`.

Do not remove failed cases from the denominator. Unmarked negative counts are reported as counts, not statistically meaningful false-positive rates. A pHash distance threshold and ORB/RANSAC inliers indicate similarity; they are not calibrated confidence percentages. Crops, rotation, chained edits, wider natural-image sets and independent cryptographic review remain future work. Update this page only from captured output. The benchmark is a CLI research tool and is intentionally absent from the application navigation.

## Interface and deployment

Playwright exercises Home, Protect, Verify and About at 1440, 1366, 768 and 390 px. It checks centering, overflow, keyboard navigation, WCAG A/AA rules with axe, branding assets, downloads/reuploads, refresh/reset, private workspace clearing, expanded evidence, reports and invalid/oversized/corrupt/unmarked/offline states against the actual API. Automated accessibility rules do not replace assistive-technology testing.

Ruff formatting/lint, strict MyPy, TypeScript, ESLint, Prettier, Vitest, pytest coverage, dependency audits and Bandit are explicit gates. Direct deployment acceptance requires a real production-configured Uvicorn restart, retained SQLite metadata, expired transient links and new successful Protect/Verify operations. Browser tests build Vite with a direct API prefix and run the delivered static assets against the real native backend.

## Latest measured results (2026-10-22)

| Check | Result |
|---|---|
| Ruff, format, strict MyPy, ESLint, TypeScript, Prettier | PASS |
| Python tests | PASS: 66 tests, 88.51% coverage |
| Frontend unit tests | PASS: 9 |
| Production-build browser suite | PASS: 16/16 at 1440/1366/768/390 px, no retries; includes axe, layout, real protect/download/re-upload/verify, reports, link-check refusal and trace backup/restore |
| Restart check | PASS: native production startup/restart, SQLite retention, transient expiry, resumed/new Protect/Verify, exports and clear |
| Bandit, pip-audit, pnpm audit, pip check | PASS: no findings |
| Production build | JS 309 kB (gzip 97 kB), CSS 26 kB (gzip 6 kB) |
| Home page load (local preview, 1440 px, cache disabled) | FCP 224 ms; throttled 9 Mbps / 170 ms: FCP 716 ms, hero photo 483 ms; 331 KB transferred |

Quick benchmark: v3 recovers 4/4 for clean, JPEG-85, resize-75, resize-50 + JPEG-80, upscale-150 and WebP-80, and 0/4 for a 5% center crop. v2 recovers clean and JPEG-85 only; LSB clean only. No engine accepted an unmarked control. v3 PSNR is about 39–40 dB.

Automated checks and local ingress simulation do not certify a live provider's HTTPS, cookie/CORS, resource limits or persistent mount; those need deployment-time smoke checks. Practical limits are listed in [Limitations](LIMITATIONS.md).
