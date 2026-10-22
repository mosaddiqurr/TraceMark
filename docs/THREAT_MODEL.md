# Threat Model

Updated: 2026-10-22 for link checks and trace exports.

The browser, static host/proxy, FastAPI process, SQLite directory, child image processor, temporary provenance directory and untrusted input bytes are separate boundaries.

| Threat | Control |
|---|---|
| Spoofed, corrupt, animated or huge images | Signature/MIME agreement, decoded verification, byte/pixel/dimension/frame caps |
| Slow uploads / multipart expansion | Actual-body cap before parser/spooling, upload deadline, proxy body cap |
| CPU exhaustion | Immediate bounded admission, spawned child process, hard termination deadline |
| Persistent image leakage | No original image store; private TTL-bounded output memory; parent-owned temporary cleanup |
| Cross-browser IDOR | Owner-scoped metadata queries and transient output/report lookups; uniform 404 |
| Forged watermark | ECC recovery followed by constant-time HMAC verification; opaque identifiers only |
| Similarity falsely presented as authentication | VERIFIED requires both integrity and an authorized trace; separate hash/visual evidence |
| CSRF / session theft | Random capability cookie, HttpOnly, production Secure, exact origins, CSRF on mutations |
| Session/database leakage | HMAC session digests; no keys or plaintext cookies in the registry |
| Report tampering | Canonical immutable evidence snapshot, independent HMAC key, integrity check at every export |
| XSS / report injection | React escaping, bounded single-line labels, PDF text escaping, CSP, safe filenames |
| Abuse / memory and disk growth | Per-IP fixed windows, bounded limiter cardinality, output byte/count cap, trace/workspace quotas, expiry cleanup |
| Secret leakage in errors/logs | Error codes and correlation IDs; exception types only, no bodies/credentials/session/key values |
| Infrastructure exposure | Least-privileged API account, private SQLite directory, host resource limits, HTTPS at hosting ingress |
| SSRF through link checks | HTTP(S) only, ports 80/443, no userinfo, every resolved address and the connected peer must be public, re-validated on each of at most three redirects, byte cap per response, at most eight page images, 60-second scan budget |
| Link-check abuse as a fetch proxy | CSRF-protected endpoint, separate per-IP window (10 per 10 minutes by default), responses never returned to the client, kill switch `TRACEMARK_LINK_CHECKS=false` |
| Forged or crafted trace imports | Domain-separated HMAC over the canonical export, strict schema/size validation, quotas; unsigned or foreign files rejected |
| Stolen trace export | Treated as a bearer secret in the UI and docs; resolving marks still requires this deployment's keys |

Operational boundaries: one Uvicorn worker and one API replica. Rate limits and transient memory are process-local. Client IPs are not trusted from arbitrary forwarded headers. Add a trusted ingress limiter for distributed deployments. Descriptors are sensitive derived data and can reveal image structure; they are not anonymized.

The processor child shares the API's operating-system account and permissions. Its separation bounds lifetime and resources; a compromised native decoder can threaten that account. Keep codec dependencies patched and enforce least privilege, host resource limits and bounded temporary storage.

Cookie loss or expiry removes access to private mappings. Unresolved authentic watermarks do not expose another workspace's identifier, filename, label or timestamp. Clearing a workspace invalidates in-flight evidence and cascades metadata deletion.

No crawler is reachable. The only outbound network workflow is the user-initiated link check above, built on the DNS-pinned safe fetcher and its regression tests. Fetched pages are parsed only for image URLs; scripts are never executed.
