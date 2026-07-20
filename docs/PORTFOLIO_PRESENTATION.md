# Portfolio Presentation Outline

1. Problem: exact hashes fail after benign edits, while metadata can be stripped.
2. Evidence layers: authenticated pixel payload, exact digest, perceptual fingerprints, geometric local features, and optional C2PA provenance.
3. Architecture: isolated web/API/worker/data boundaries with private storage and queued image processing.
4. Technical contribution: versioned authenticated payload and blind DWT-DCT quantization engine with keyed placement, repetition, interleaving, and error correction.
5. Security: owner-scoped access, hostile-image controls, archive defenses, session security, SSRF-resistant scanning, secret separation, and safe reports.
6. Experiments: generated varied dataset, negative controls, fixed seeds, real quality/survival/timing measures, and LSB comparison.
7. Limitations: a watermark can be damaged or deliberately removed; similarity is not identity; distribution mapping is not proof of intent; scanner coverage is bounded.
8. Future work: calibrated engine adapters, trusted provenance credentials, expanded datasets, and a separately engineered video system.

