# TraceMark status

Updated: 2026-10-17. Application validation results below were measured on 2026-10-05.

The application now uses direct native Python and static frontend hosting. Obsolete infrastructure, duplicate publication/history documents and unused launch/proxy helpers are removed. Core watermarking, private registry isolation and exports are retained.

Native production-configured restart validation passed: SQLite mappings survived, old output/report links returned 404, the saved protected image still verified, new operations and both exports succeeded, and clearing removed metadata. Production Secure/HttpOnly cookie flags and disabled API docs were checked through an explicit loopback ingress harness.

Dependency audits, Bandit, pip consistency and compilation passed. A real Windows child-teardown failure was repaired with retained resources and closed admission until reaping. The final Make test run passed 50 Python / 9 frontend tests with 86.49% coverage. Both lint command families passed.

The final direct-API production-build browser report passed 12/12 with no failures, retries or skipped tests at 1440/1366/768/390 px. It includes actual protection, downloaded-file reupload, private evidence, PDF/JSON exports, reset/clear/repeat, invalid/oversized/corrupt/unmarked/offline states, refresh/direct routes and automated accessibility/layout checks. Four current screenshots were refreshed and the mobile evidence layout inspected.

## Final direct-deployment gates

| Check | Result |
|---|---|
| Make lint and PowerShell lint | PASS: Ruff lint/format, strict MyPy, ESLint, TypeScript and Prettier |
| Make tests | PASS: 50 Python / 9 frontend; 86.49% coverage |
| PowerShell tests | PASS: 50 Python / 9 frontend; 86.38% coverage |
| Make and PowerShell benchmark | PASS: real robust/LSB operations; strict JSON snapshot in docs/benchmark-quick.json |
| Make and PowerShell restart | PASS: actual production-configured Uvicorn processes, retained SQLite mapping, expired artifacts, resumed/new operations, exports and clear |
| Production-build browser suite | PASS: 12/12; no failures, retries or skips; automated axe and four viewports |
| Default / HTTPS API frontend builds | PASS: JS 296.27 / 296.30 kB, gzip 93.03 / 93.05 kB; CSS 13.40 kB, gzip 3.60 kB |
| Runtime/frontend audits and security | PASS: pip-audit and pnpm audit found no known vulnerabilities; Bandit, pip check and compilation passed |
| Setup and package installation | PASS: setup.ps1 with existing local cache, locked pnpm install, both production wheels built and installed |
| Local startup | PASS: native API readiness, Vite Protect/Verify routes and development API proxy |
| Publication scan | PASS: no obsolete deployment references, development-tool attribution or private/generated publication candidates; four current screenshots |

Quick benchmark: robust clean 2/2, JPEG-85 2/2, resize-75 0/2; LSB clean 2/2, JPEG-85 0/2, resize-75 0/2. Each engine detected 0/2 unmarked controls. Two synthetic fixtures do not establish general robustness or a population false-positive rate.

The HTTPS-configured build embeds its public API prefix and no configured backend secret. A routing dependency contains a localhost parsing fallback; it is not the application's configured API endpoint.

Accessible generated reports, builds, caches and obsolete infrastructure directories were removed. Windows permission-protected remnants remain under three ignored test-cache trees; ownership recovery was denied by the OS. They are absent from Git publication candidates and are not runtime dependencies. Full local cache deletion requires an account able to repair those ACLs. Dependencies, local secrets and private application metadata were preserved.

An upstream Starlette TestClient/httpx deprecation warning remains. Automated accessibility checks and local ingress simulation do not certify a live provider's HTTPS, cookie/CORS, resource limits or persistent mount. These require deployment-time smoke checks; one worker/instance and same-site HTTPS domains are the reference model.

Verdict: **GO — READY FOR GITHUB AND DIRECT DEPLOYMENT**, with the documented operational and watermark limitations. No commits, tags, pushes or public deployments were made during the validation pass.

## GitHub publication — 2026-10-17

The owner authorized publication to [mosaddiqurr/TraceMark](https://github.com/mosaddiqurr/TraceMark). The destination was confirmed empty. Current publication candidates and existing local history were checked for private files and credential patterns; no findings were detected. The prepared source was published to main in commit eaeb2ebf3696dfeb0c733e0b9a697b235f377d1f.

GitHub's email-privacy protection initially rejected the local author address. Only the unpublished author/committer email fields were replaced with the verified account's no-reply address; source trees and authorship were preserved, and originals remain in a local-only backup ref. No account privacy settings were changed. The live demo remains a placeholder; application hosting is a separate deployment step.
