# Benchmark Guide

Run 'make benchmark' after setup. The generator creates only deterministic licence-safe local images and records seeds/provenance. Profiles cover clean, recompression, format conversion, resizing, crops, rotation, tonal changes, blur, sharpening, noise, overlays, and conversion chains.

Compare negative controls, LSB, and robust outputs. Record every attempted case, including failures, with detection, integrity, bit errors where ground truth exists, corrected symbols, votes, dimensions, size, PSNR/SSIM where meaningful, duration, and error reason.

Never remove a failed case from the denominator. Update 'EVALUATION.md' only from captured machine-readable results.

