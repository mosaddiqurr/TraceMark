# Evaluation Methodology

## Dataset

A deterministic generator will produce licence-safe synthetic images covering high/low texture, gradients, edges, text-like detail, bright/dark scenes, portrait/landscape/square geometry, supported dimensions, alpha channels, and unwatermarked negatives. Provenance and random seeds will be recorded.

## Measurements

For clean and transformed images record detection, HMAC integrity, bit error rate where ground truth exists, corrected symbols, valid votes, PSNR/SSIM where meaningful, file size, dimensions, duration, and failure reason. Compare unwatermarked negatives, LSB, and robust engines.

## Targets

- 100% clean extraction on valid supported clean fixtures.
- Zero accepted forged identifiers and zero wrong-key acceptance.
- Default robust outputs normally maintain SSIM >= 0.95.
- Robust extraction materially outperforms LSB under recompression and resizing.
- False-positive rate is measured against the complete negative set.

## Recorded quick benchmark - 2026-07-20

Command: `.venv\Scripts\python.exe scripts\run_benchmark.py --profile quick`

- Dataset: 2 generated fixtures (`alpha-gradient.png`, `dark-gradient.jpg`), seed 20260720.
- Clean authenticated extraction: robust 2/2; LSB 2/2.
- JPEG quality 85 survival: robust 2/2; LSB 0/2.
- 75% resize survival: robust 0/2; LSB 0/2.
- Unwatermarked false positives: robust 0/2; LSB 0/2.
- Robust extraction latency: 123-198 ms for clean/JPEG cases and 1.48-1.54 s for failed resize searches.
- JPEG-transformed robust outputs retained SSIM 0.9988 against the protected source in this run.

The quick run confirms that the robust engine materially outperforms LSB under JPEG recompression, but not under resizing. The resize failure is a current synchronization limitation and is not hidden. Machine-readable per-case evidence is generated at `artifacts/benchmark-results.json`.


## Validation record - 2026-07-20

- `.venv\Scripts\python.exe -m ruff check apps packages workers tests scripts`: pass.
- strict mypy across API, engine, worker, and scripts: 42 source files, no issues.
- pytest with an isolated temporary directory: 27 passed in 10.92 seconds; one upstream TestClient deprecation warning.
- `pnpm --dir apps/web typecheck` and `lint`: pass.
- Vitest: 2 files and 6 tests pass in 6.17 seconds.
- Vite production build: 2,262 modules built in 11.45 seconds; 717.84 kB minified JavaScript (208.28 kB gzip).
- Real in-app browser journey: landing, login, secure-session reload, upload, robust protect, asset history, ownership verify, distribution create, quick benchmark chart, and report list passed with no browser warning/error entries.
- Docker commands: unavailable because the `docker` executable is not installed. No container result is inferred from native results.