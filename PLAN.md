# TraceMark Implementation Plan

Updated: 2026-07-20

| Milestone | State | Validation gate |
|---|---|---|
| 1. Repository contract and durable documentation | Complete | Required root documents exist and Git is initialized |
| 2. Monorepo and runnable infrastructure | Implemented; container validation blocked | Native startup works; Docker Desktop is unavailable |
| 3. Watermark and forensic engine | Complete for v0.1 | Clean/wrong-key/security tests and quick benchmark pass |
| 4. Identity, secure ingestion, assets | Complete for native slice | Auth, CSRF, upload, download, session stability, and isolation tests pass |
| 5. Protection and distributions | Complete for native slice | Real protect/download/distribution browser workflows pass |
| 6. Verification and matching | Complete for native slice | Authenticated extraction and transparent evidence pass; ORB remains an optional constituent signal |
| 7. Collections and controlled URL tracing | Partial | Individual/ZIP/dedupe/search/rescan/delete and SSRF controls exist; robots and queued operation remain |
| 8. Robustness laboratory and reports | Partial | Real quick/standard/aggressive API profiles and JSON/HTML/PDF output exist; full transform matrix remains |
| 9. Complete responsive UI | Implemented | Production build and real desktop browser journey pass; mobile Playwright journey remains |
| 10. Demo assets, documentation, and CI | Implemented | Deterministic dataset, guides, scripts, diagrams, and CI exist |
| 11. Formal validation stages 1-10 | Partial | Native lint/type/test/build/benchmark/browser stages recorded; containers/security expansion remain |
| 12. Independent review and release audit | Pending | Requires Docker availability and completion of remaining release gates |

## Next release gates

1. Install Docker Desktop and run Compose config, build, startup, readiness, migrations, seed, and persistence checks.
2. Route long-running workflows through the defined Dramatiq queues with cancellation, quotas, worker timeouts, and cleanup.
3. Finish robots.txt enforcement and validate DNS-pinned peer checks in the Linux reference environment.
4. Expand robustness transformations and tune bounded resize/crop/rotation synchronization against the complete negative set.
5. Run desktop/mobile Playwright end to end, cross-user UI isolation, PDF render inspection, security scans, and independent cryptography/authorization/accessibility reviews.

Formal validation order remains environment/build, algorithm, backend integration, frontend, browser E2E, security, robustness, performance, manual demonstration, and independent review.