# Evaluation methodology

The focused release preserves the existing robust DWT/DCT/QIM engine, HMAC/ECC payload, LSB comparison baseline, exact SHA-256 and actual perceptual/ORB/RANSAC measurements.

## Acceptance model

A positive result requires successful payload integrity verification and a matching trace owned by the active anonymous workspace. A hash or similarity match alone must remain NOT VERIFIED. Wrong keys, forged authentication, unknown identifiers, foreign workspaces and expired mappings must never expose a private identifier or reference label.

The real journey protects an image, saves the delivered PNG, reuploads those exact bytes, checks the recovered identifier/hash and downloads both report formats. Backend regressions also examine JPEG recompression, resizing (which must verify with v3) and cropping (which must not). Link checks are tested against a fake fetcher, including page parsing, ranking, refusal of non-public addresses, and signed trace export/import with tampering. Every successful protection independently extracts its saved PNG before returning it.

## Engine benchmark

The quick CLI profile uses four deterministic synthetic fixtures and clean, JPEG-85, resize-75, resize-50 + JPEG-80, upscale-150, WebP-80 and 5% center-crop cases for the v3, v2 and LSB engines. Standard includes all fixtures plus JPEG-70 and JPEG-60. Results include failed attempts, integrity, corrected symbols, repetition counts, extraction time and image quality when comparable.

Unmarked negative counts are reported as counts, not statistically meaningful false-positive rates. A pHash distance threshold and ORB/RANSAC inliers indicate similarity; they are not calibrated confidence percentages. Wider natural-image sets, severe geometric attacks and independent cryptographic review remain future work.

Captured results live at `artifacts/benchmark-results.json`; the release snapshot is `docs/benchmark-quick.json`. Current measured acceptance results are recorded in `STATUS.md`.

## Interface and deployment

Playwright exercises Home, Protect, Verify and About at 1440, 1366, 768 and 390 px. It checks centering, overflow, keyboard navigation, WCAG A/AA rules with axe, branding assets, downloads/reuploads, refresh/reset, private workspace clearing, expanded evidence, reports and invalid/oversized/corrupt/unmarked/offline states against the actual API. Automated accessibility rules do not replace assistive-technology testing.

Ruff formatting/lint, strict MyPy, TypeScript, ESLint, Prettier, Vitest, pytest coverage, dependency audits and Bandit are explicit gates. Direct deployment acceptance requires a real production-configured Uvicorn restart, retained SQLite metadata, expired transient links and new successful Protect/Verify operations. Browser tests build Vite with a direct API prefix and run the delivered static assets against the real native backend.

The latest measured gates and practical limitations are recorded in STATUS.md and LIMITATIONS.md.
