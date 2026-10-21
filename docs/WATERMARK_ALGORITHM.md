# Watermark algorithm

## Authenticated payload

The retained 38-byte format contains two-byte magic, payload version, ownership/distribution type, algorithm version, key version, a 128-bit opaque token, CRC-32 and a 96-bit truncated HMAC-SHA-256 tag. RS(58,38) adds 20 parity bytes; a deterministic key-derived permutation interleaves the codeword.

CRC detects accidental corruption. Constant-time HMAC verification authenticates the payload. HKDF-SHA-256 derives domain-separated placement, interleaving and authentication keys. Private recipient labels remain in the registry, never in pixels.

Payload authenticity does not certify unmodified image pixels or legal ownership. Exact hashes and visual measurements remain separate evidence.

## LSB baseline

The educational engine writes the interleaved payload into keyed least-significant RGB channel bits and extracts blindly. It checks capacity and integrity. Recompression and resizing commonly destroy it; it remains for extraction compatibility and CLI comparison.

## Canonical v3 engine (default)

The v3 engine (`canonical-dwt-dct-qim`, algorithm version 3) makes reading independent of the copy's resolution. Luminance is resampled bicubically to a 256 × 256 canonical image. One Haar level yields 128 × 128 LH/HL bands, divided into 4 × 4 blocks (2,048 slots). A key-derived permutation, independent of image size, chooses 4 × 464 slots and one of four low/mid DCT coefficients per slot. Parity quantization uses an activity-adapted step around strength 20.

Embedding is closed-loop: for five passes, the current image is resampled to the canonical grid, quantized, and the canonical difference is resampled back and added to full-resolution luminance. Extraction resamples the copy to 256 × 256 once, reads all bits in a batch, and tries the weighted vote and each repetition before RS correction and HMAC authentication. Embedding takes ~0.3 s and extraction ~0.05 s for a 1200 × 900 image.

Because the canonical mapping depends on the full frame, cropping shifts every slot and is not survived.

## Robust blind engine (v2)

The robust v2 engine converts RGB to luminance and preserves alpha. One orthonormal Haar transform yields LH/HL detail bands divided into 8 × 8 blocks. A key/version/geometry-derived permutation selects distinct blocks and one of four mid-frequency DCT coefficients.

Parity quantization embeds each bit. Its step adapts to median block activity and configured strength. Three disjoint repetitions carry the codeword. Extraction reads coefficient parity/reliability, tries weighted votes and individual repetitions, corrects symbols and authenticates the payload.

The bounded search tries identity, ±1-degree rotations, scales 0.99/1.01 and four one-pixel offsets. It does not provide general crop/resize synchronization. The focused API searches strengths 32/36/42 and key version 1 under a killable deadline.

Insufficient block capacity is rejected. The API decodes and extracts the actual saved PNG before reporting successful protection; content-dependent recovery failures are explicit.

## Quality and limits

The retained measurements include PSNR, windowed SSIM, absolute/RMS error, changed-pixel ratio and maximum channel delta. Alpha is restored; protection applies orientation and strips source metadata.

The quick benchmark (four fixtures) recovers v3 at 4/4 for clean, JPEG-85, 75% resize, 50% resize + JPEG-80, 150% upscale and WebP-80, and 0/4 for a 5% center crop. v2 recovers clean and JPEG-85 only; LSB recovers clean only. No engine accepted an unmarked control; four controls cannot establish a population false-positive rate.

See [Evaluation](../EVALUATION.md), [Benchmark guide](BENCHMARK_GUIDE.md) and [Limitations](../LIMITATIONS.md).
