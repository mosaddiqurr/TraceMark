# Evaluation Dataset

Run 'python scripts/generate_dataset.py' to create deterministic, licence-safe fixtures under 'datasets/generated'. Generated binary files are ignored; the emitted manifest records dimensions, role, provenance, and seed.

The fixtures cover gradients, high texture, sharp edges, text-like detail, bright/dark images, portrait/landscape/square geometry, transparency, and all supported formats. Each clean fixture also serves as an unwatermarked negative control before benchmark-specific transformed copies are created.

