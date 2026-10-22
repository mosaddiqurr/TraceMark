# Architectural decisions

## D013 — Focused accountless application

Use React/Vite, one FastAPI process and private SQLite metadata. Random HttpOnly browser workspace cookies, CSRF and exact origins preserve owner isolation without accounts. Cookie loss prevents access to private mappings; an authentic unresolved watermark remains distinct from verified private evidence.

## D003 / D004 / D005 — Authenticated classical watermark and separate evidence

Embed a random 128-bit token with version metadata, CRC, error correction and HMAC. Keep labels outside pixels. The independent wavelet/DCT/QIM engine uses keyed placement, repetition and Reed-Solomon correction. VERIFIED requires successful authentication and an authorized mapping. Hashes, visual features and optional provenance remain separate measurements.

## D014 — Retain descriptors, discard pixels

Persist session digests, opaque identifiers, private labels, source/output hashes, compact perceptual/ORB descriptors and timestamps. Protected downloads and authenticated report snapshots use bounded memory. Workspace expiry or explicit clearing removes metadata and temporary artifacts. Descriptors remain sensitive derived data.

## D015 / D016 — Hard deadlines and bounded memory transfer

Spawn one admitted processor by default and terminate overdue work. A thread timeout cannot stop CPU processing. Parent-owned shared memory transfers trusted internal arguments/results; no external serialized object is accepted. Completion/timeout kills and joins children, unlinks buffers, removes provenance temporary files and releases admission. Output serialization is capped at 32 MiB. Provision at least 128 MiB shared-memory capacity at default limits.

Cap OpenBLAS/OMP/MKL/NumExpr threads at one before imports. Extra API workers would break process-local rate and artifact behavior; throughput expansion needs a shared-state design.

## D017 — Safe framework logging

SQLAlchemy hides bound parameters. Application and Uvicorn formatting records exception types without values or tracebacks; access logging is disabled. Correlation IDs preserve limited diagnostics without exposing sensitive state.

## D018 — Results belong to the accepted file

Clear the prior Verify result and preview when rejecting a new file. A prior VERIFIED panel alongside a new unsupported-file error could misrepresent the rejected input. A browser regression exercises this transition.

## D019 — Readiness reads registry tables

Read one identifier from each required workspace/trace table and return a safe 503 on database failure. A constant query does not exercise those tables. Liveness is separate; read readiness does not guarantee a subsequent write or image operation.

## D020 — Direct native API and static hosting (2026-10-05)

Deploy the existing FastAPI application on a standard Python host and its production React build on Netlify/Vercel or equivalent. Keep SQLite because workspace capabilities and trace evidence must survive restarts. A persistent private mount, stable independent environment secrets, exact HTTPS origins and secure cookies are required.

Prefer HTTPS subdomains of one site to avoid third-party cookie restrictions. A same-origin hosting rewrite is optional and subject to provider timeouts. Run one API worker/instance under a least-privileged account with host resource and ingress limits; processing children share that account's permissions.

Acceptance includes a cold native Uvicorn restart with real HTTP Protect/Verify/export operations. SQLite mappings survive; temporary artifacts deliberately do not. The browser gate builds and serves the production frontend with a direct API URL. Live provider TLS, ingress and mount verification remains a deployment-time check.

## D021 — Defer cleanup until the operating system reaps a child

A delayed process exit exposed a live-process close error during real verification. After bounded terminate/kill waits, transfer shared buffers and temporary directories to a background reaper if the process remains alive. Block new processing admission until reaping and cleanup finish. This preserves completed evidence without closing a live process or releasing its resources prematurely; it also prevents overdue children from expanding processing concurrency. If OS reaping or cleanup cannot complete, admission stays closed until operational recovery. A lifecycle fault regression simulates delayed termination; real engine and restart/browser checks remain separate acceptance gates.

## Download and provenance contracts

Consume API-advertised output/report URLs with authenticated binary downloads and safe filenames. Search only the supported robust strengths (32, 36, 42). Optional C2PA dependency/platform failure cannot invalidate independent authenticated pixel evidence. All registry and artifact lookups remain owner-scoped.

## D022 — Resolution-independent v3 watermark (2026-10-22)

v2 derives placement from the submitted width/height and reads an 8 × 8 grid at native resolution, so any resize desynchronizes it (0/2 at 75% in the prior benchmark). v3 embeds into a fixed 256 × 256 canonical luminance image with 4 × 4 DCT blocks and four repetitions, adds the resampled residual over five closed-loop passes, and resamples every candidate copy to the same grid before reading. Strength 20 was chosen over 16 after measurement: WebP 80 survival rose from 5/8 to 8/8 while PSNR fell from ~41.4 to ~39.4 dB. New protections use v3 when both sides are at least 256 px; v2 remains for smaller images and for verifying earlier copies. The two marks use separate placement keys and do not cross-decode.

Rejected: a 512-px canonical grid with 8 × 8 blocks (fails 50% resizes), perceptual masking (negated by closed-loop correction), and a center-crop search (no real crops recovered, multi-second cost on every verification).

## D023 — User-initiated link checks instead of crawling

Finding copies is delegated to reverse image search engines that index visual content. TraceMark verifies only links a person submits: a direct image, or up to eight images referenced by one page. This reuses the DNS-pinned safe fetcher, keeps outbound traffic attributable and bounded, and avoids storing third-party content.

## D024 — Signed, moving trace exports

Private labels were lost with the cookie. A domain-separated HMAC export lets people back up and move records without accounts. Trace identifiers are global primary keys, so restoring a record held by another workspace moves it; the signed export is treated as the owner's credential.

## D025 — Rate-limit workspace creation, not re-confirmation

The frontend confirms its workspace on page load. Counting every confirmation against the 30-per-10-minute creation window rejected ordinary browsing. Only requests that create a workspace consume that window; re-confirmation uses the general request limit.

## D026 — Editorial redesign with a measured hero

The interface moved to a dark editorial system (Bodoni Moda, IBM Plex) with a hero photograph whose lens reveals the image redrawn from identifier characters, labelled as an illustration. The photo renders as a preloaded 40 KB WebP before any script; the character layer is built on idle and only animates while moving. Fonts are self-hosted to satisfy `font-src 'self'`. Home page transfer is ~330 KB.
