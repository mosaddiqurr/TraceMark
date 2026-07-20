# Watermark Algorithm

## Payload

TraceMark embeds a 38-byte authenticated payload: two-byte magic, payload version, ownership/distribution type, algorithm version, key version, random 128-bit token, CRC-32, and a 96-bit truncated HMAC-SHA-256 tag. RS(58,38) adds twenty parity bytes. A key-derived deterministic permutation interleaves the 58-byte codeword.

CRC detects accidental corruption but never establishes authenticity. Extraction accepts a token only after Reed-Solomon recovery and constant-time HMAC validation. HKDF-SHA-256 derives domain-separated placement, interleaving, and authentication keys from the runtime master key and key version.

## LSB baseline

The educational engine writes the interleaved codeword into keyed least-significant RGB channel bits and reads it blindly using the same key-derived positions. Capacity is checked before embedding. It is expected to fail after recompression or resizing and is not the default.

## Robust blind engine

The robust v2 engine converts the image to RGB luminance while preserving any alpha plane. It applies a one-level orthonormal Haar transform and divides LH and HL detail bands into 8 by 8 blocks. A key/version/geometry-derived pseudo-random permutation selects distinct blocks and one of four mid-frequency DCT coefficients.

Each bit is embedded with parity quantization. The quantization step adapts modestly to median block activity and the selected robustness strength. The complete RS codeword is placed three times in disjoint blocks. Extraction repeats the transform, reads coefficient parity and reliability, performs weighted voting, also tries each individual repetition, corrects the codeword, and authenticates the payload.

The extractor tries only a bounded identity, small rotation, scale, and one-pixel offset set. It returns diagnostics and ºw^~)Þtno valid watermark founféÝyø§yÝ rather than guessing. Images without enough distinct blocks are rejected.

## Quality and limitations

PSNR, windowed SSIM, absolute/RMS error, changed-pixel ratio, and maximum channel delta compare the original and output. Alpha is restored unchanged. JPEG compression and moderate pixel resampling are evaluation targets; severe crops, arbitrary rotation, repainting, or deliberate removal can defeat synchronization. See 'EVALUATION.md' for measured results and 'LIMITATIONS.md' for claims that must not be made.
