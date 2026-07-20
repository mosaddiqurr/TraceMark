# Architectural Decisions

## D001 — Modular monorepo

Use React/Vite for the web client, FastAPI/SQLAlchemy for the API, a framework-independent Python watermark package, and Dramatiq workers. PostgreSQL stores relational evidence, Redis stores sessions/queue state, and MinIO stores private binary artifacts.

## D002 — Server-side opaque sessions

Use random Redis-backed sessions in HTTP-only cookies plus CSRF tokens. This makes logout/revocation immediate and avoids placing authorization claims in browser-readable storage.

## D003 — Authenticated opaque pixel payload

Embed only a random 128-bit token plus version metadata, CRC, and truncated HMAC. Resolve people/assets from authorized database records; never embed labels or PII.

## D004 — Classical robust contribution

Implement the primary watermark internally with wavelet bands, keyed DCT coefficient placement, quantization modulation, repetition, interleaving, Reed-Solomon correction, and HMAC acceptance. Third-party watermark wrappers cannot replace it.

## D005 — Evidence, not an aggregate confidence score

Use deterministic classifications with constituent cryptographic, hash, feature, and provenance measurements shown separately.

## D006 — Bounded source scanning

Scan only a direct image or one explicitly supplied public HTML page. Do not recursively crawl. Validate and pin public DNS results and every redirect.

## D007 — Optional provenance adapter

Use `c2pa-python` when supported. Dependency or platform failures become explicit unsupported/unavailable states and cannot break the core pixel watermark.

## D008 — Reproducible containers plus native Windows workflow

Linux containers are the deployment reference. PowerShell scripts support local development, but container acceptance remains required before release completion.


## D009 — Development-only memory sessions

Native browser demonstration may select an in-memory session backend only outside production. Production settings validation mandates Redis. CSRF tokens are retained only inside the server-side session record so concurrent session rehydration is stable; only their HMAC digest is used for comparison and no token is written to relational storage or logs.

## D010 — Honest synchronous vertical slice

Core workflows execute real algorithms synchronously until Dramatiq orchestration is complete. Completed job resources describe the observed result, but the product is not called production-ready and cancellation/worker-isolation acceptance stays open.