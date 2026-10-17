# TraceMark Repository Instructions

## Mission

Build and maintain TraceMark as an honest, secure still-image forensic watermarking and tracing platform. Core workflows must be real; never substitute mocked detections, invented benchmark results, or unsupported claims.

## Working rules

- Read `SPECIFICATION.md`, `PLAN.md`, `STATUS.md`, `DECISIONS.md`, and `THREAT_MODEL.md` before substantial work.
- Update `PLAN.md` and `STATUS.md` after every substantial milestone.
- Record architectural or security tradeoffs in `DECISIONS.md` and technical shortfalls in `LIMITATIONS.md`.
- Preserve user isolation on every object lookup and download.
- Never log image bytes, credentials, session values, watermark keys, or report-authentication keys.
- Do not embed recipient labels or personal information in images; use opaque tokens only.
- Do not accept an extracted token without successful integrity verification.
- Keep URL scanning bounded to explicitly supplied public URLs and enforce SSRF protections on every redirect.
- Build features before expanding exhaustive tests; run focused smoke checks continuously and the formal suites after mandatory features exist.
- Use `apply_patch` for hand-authored edits. Avoid overlapping concurrent edits.
- Do not push to a remote without explicit user permission.

## Required checks

Use `make lint`, `make test`, `make benchmark`, and the PowerShell equivalents. Direct deployment readiness also requires a production frontend build, real browser journeys and `make restart` against a native FastAPI process.
