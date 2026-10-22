# Security Policy

TraceMark provides technical evidence, not legal adjudication. Report vulnerabilities privately to the repository owner.

Production requires three independently generated secret keys, HTTPS, secure HttpOnly cookies, exact frontend origins, a private persistent SQLite directory and a single API worker/replica. Startup rejects development keys, short/equal secrets, wildcard/path origins and unsafe cookie settings.

No uploaded pixels, credentials, cookie values, watermark keys or report keys belong in logs. The API suppresses sensitive exception contents and server access logs. Uploaded bytes are never executed. Public file storage, accounts and crawling are absent. The only outbound requests are user-submitted link checks through the DNS-pinned safe fetcher; see the threat model.

Default limits: 20 MiB input, 4 million decoded pixels, 4096 px per side, one image processor, 30 seconds processing, 30 processing requests per IP per 10 minutes, 128 MiB transient artifact memory, 100 traces per workspace, 1000 workspaces and 10,000 traces globally. Host ingress must also cap concurrent connections/body sizes and enforce resource limits.

Trace metadata is sensitive: visual descriptors can reveal aspects of source imagery. Restrict directory access and backups. Workspace records expire after 30 days by default; temporary outputs/reports after 15 minutes. Expiry is absolute and does not silently extend on access. SQL deletion does not guarantee forensic erasure from database pages, journals or backups.

Keep keys stable across deployments to preserve watermark authentication and private cookie resolution. This release supports key version 1 only; key rotation and migration require a separate design. Report HMACs authenticate snapshots to the deployment's secret, not to a public trust authority.

See [Deployment](docs/DEPLOYMENT.md), [Threat model](docs/THREAT_MODEL.md) and [Limitations](docs/LIMITATIONS.md).
