# TraceMark implementation plan

Updated: 2026-10-17. Direct deployment migration and application validation complete; GitHub publication authorized.

| Milestone | State | Evidence |
|---|---|---|
| Preserve real Protect / Verify and private evidence | Complete | Existing engine, scoped SQLite mappings and PDF/JSON exports retained |
| Simplify local and hosted execution | Complete | Native Python API; Vite development; Netlify/Vercel static configurations |
| Remove obsolete infrastructure and duplicate release docs | Complete | Runtime scripts, CI and public instructions use the direct model |
| Validate native process restart | Complete | Production-configured HTTP harness passed retained mappings, transient expiry, resumed/new operations and exports |
| Run formal and browser gates | Complete | Both command families passed; 12/12 real browser checks, audits, production builds and benchmark |
| Final publication cleanup and verdict | Complete with local cleanup exception | Public candidates contain no private/generated files; three permission-protected ignored cache trees remain |
| Publish prepared source to GitHub | In progress | User authorized https://github.com/mosaddiqurr/TraceMark; destination is empty and publication/history scans passed |

Public hosting requires a persistent private directory, stable secrets, exact HTTPS origins, secure cookies and one API instance. GitHub source publication is authorized; hosted application deployment and provider/domain provisioning are not part of this publication task.
