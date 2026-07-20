# Architecture

    Browser -> Nginx -> FastAPI -> PostgreSQL
                         |       -> Redis/Dramatiq -> Workers
                         |       -> private MinIO
                         + workers use the standalone watermark engine

The API owns authentication, authorization, validation, metadata, evidence classification, and object-download decisions. Workers receive opaque job and storage identifiers, re-check job ownership and state, and write immutable results. The watermark package has no dependency on FastAPI or storage.

## Trust boundaries

Browser input, uploaded bytes, archives, remote URL responses, database rows, queue messages, and object-store objects are untrusted at entry. Secrets are injected at runtime and split by purpose using HKDF. Buckets are private and object keys are randomized.

## Processing flow

Protection validates and normalizes an upload, stores the original, creates an opaque token, queues embedding, stores the protected output, computes metrics, and records audit evidence. Verification stores a temporary normalized input, then layers exact digest, authenticated extraction, perceptual hashes, local features, and provenance into a deterministic classification.

See 'DECISIONS.md' for rationale and 'docs/DATA_MODEL.md' for ownership relationships.

