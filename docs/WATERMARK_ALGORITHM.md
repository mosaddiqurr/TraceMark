# Watermark algorithm

## Authenticated payload

The retained 38-byte format contains two-byte magic, payload version, ownership/distribution type, algorithm version, key version, a 128-bit opaque token, CRC-32 and a 96-bit truncated HMAC-SHA-256 tag. RS(58,38) adds 20 parity bytes; a deterministic key-derived permutation interleaves the codeword.

CRC detects accidental corruption. Constant-time HMAC verification authenticates the payload. HKDF-SHA-256 derives domain-separated placement, interleaving and authentication keys. Private recipient labels remain in the registry, never in pixels.

Payload authenticity does not certify unmodified image pixels or legal ownership. Exact hashes and visual measurements remain separate evidence.

## LSB baseline

The educational engine writes the interleaved payload into keyed least-significant RGB channel bits and extracts blindly. It checks capacity and integrity. Recompression and resizing commonly destroy it; it remains for extraction compatibility and CLI comparison.

## Robust blind engine

The robust v2 engine converts RGB to luminance and preserves alpha. One orthonormal Haar transform yields LH/HL detail bands divided into 8 × 8 blocks. A key/version/geometry-derived permutation selects distinct blocks and one of four mid-frequency DCT coefficients.

Parity quantization embeds each bit. Its step adapts to median block activity and configured strength. Three disjoint repetitions carry the codeword. Extraction reads coefficient parity/reliability, tries weighted votes and individual repetitions, corrects symbols and authenticates the payload.

The bounded search tries identity, ±1-degree rotations, scales 0.99/1.01 and four one-pixel offsets. It does not provide general crop/resize synchronization. The focused API searches strengths 32/36/42 and key version 1 under a killable deadline.

Insufficient block capacity is rejected. The API decodes and extracts the actual saved PNG before reporting successful protection; content-dependent recovery failures are explicit.

## Quality and limits

The retained measurements include PSNR, windowed SSIM, absolute/RMS error, changed-pixel ratio and maximum channel delta. Alpha is restored; protection applies orientation and strips source metadata.

The quick benchmark recovers robust clean and JPEG-85 cases at 2/2, with 0/2 after a 75% resize. LSB recovers clean 2/2 and neither transformed case. The two-fixture negative set has no accepted marks; it cannot establish a population false-positive rate.

See [Evaluation](../EVALUATION.md), [Benchmark guide](BENCHMARK_GUIDE.md) and [Limitations](../LIMITATIONS.md).
