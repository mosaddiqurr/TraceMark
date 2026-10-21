# Benchmark guide

Run `make benchmark` or `./scripts/benchmark.ps1` after setup.

The deterministic generator writes local, licence-safe fixtures plus their seed/provenance manifest to `datasets/generated`. The CLI quick profile selects the first four sorted images and measures the v3 canonical, v2 robust and LSB engines against clean output, JPEG 85, a 75% resize, a 50% resize followed by JPEG 80, a 150% upscale, WebP 80 and a 5% center crop. Standard uses all generated images and also JPEG 70 and 60.

Results are written to `artifacts/benchmark-results.json`: every attempt, authenticated extraction, corrected symbols, repetitions, duration, failure reason and PSNR/SSIM against the protected image where dimensions match. Unmarked inputs are checked with both engines. The benchmark uses its documented public test key, never production keys.

Do not remove failed cases from the denominator. A small synthetic run cannot establish universal robustness or a population false-positive rate. Crops, rotation, chained edits and wider natural-image calibration remain future evaluation work; they are not implemented benchmark profiles.

Exports use strict JSON. Infinite PSNR for identical pixels is represented as `null`; extraction results and counts are unchanged. Metrics are also `null` where image dimensions cannot be compared.

Update `EVALUATION.md` and `STATUS.md` only from captured output. The benchmark is a CLI research tool; it is intentionally absent from the application navigation.
