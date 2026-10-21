# TraceMark implementation plan

Updated: 2026-10-22. Redesign, resize-tolerant watermark, link checks and trace backup complete and validated locally; not yet committed or deployed.

| Milestone | State | Evidence |
|---|---|---|
| Preserve real Protect / Verify and private evidence | Complete | Existing engine, scoped SQLite mappings and PDF/JSON exports retained |
| Simplify local and hosted execution | Complete | Native Python API; Vite development; Netlify/Vercel static configurations |
| Remove obsolete infrastructure and duplicate release docs | Complete | Runtime scripts, CI and public instructions use the direct model |
| Validate native process restart | Complete | Production-configured HTTP harness passed retained mappings, transient expiry, resumed/new operations and exports |
| Run formal and browser gates | Complete | Both command families passed; real browser checks, audits, production builds and benchmark |
| Publish prepared source to GitHub | Complete | Published main to https://github.com/mosaddiqurr/TraceMark |
| Editorial interface redesign | Complete | Dark editorial system, hero trace lens, self-hosted fonts; axe and layout checks at four viewports (D026) |
| Resolution-independent v3 watermark | Complete | Canonical 256 px grid; resize/upscale/JPEG/WebP 4/4 vs v2 0/4; crop remains 0/4 (D022) |
| Link checks and search guidance | Complete | SSRF-safe image/page checks, reverse image search links (D023) |
| Signed trace backup and restore | Complete | HMAC export/import, tamper rejection, moving restore (D024) |
| Dependency advisories | Complete | Pillow 13.0.0 and Vite 6.4.4; pip-audit and pnpm audit clean |
| Commit, push and redeploy | Pending owner approval | Changes are local only |

Public hosting requires a persistent private directory, stable secrets, exact HTTPS origins, secure cookies and one API instance. Crop-tolerant synchronization, C2PA signing (needs a trusted certificate) and paid reverse-search API integration are future work.
