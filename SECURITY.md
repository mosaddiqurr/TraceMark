# Security Policy and Operating Guidance

TraceMark is a research application, not a legal adjudication service. Report vulnerabilities privately to the repository owner and do not test against systems or URLs without authorization.

Production deployments must replace demonstration credentials and keys, enable TLS and secure cookies, restrict CORS, use private MinIO buckets, rotate key versions, set database/Redis authentication, apply resource limits, and retain only necessary evidence. Never expose FastAPI tracebacks or internal storage keys.

The source scanner must remain disabled if validated DNS pinning and redirect peer verification are unavailable. Uploaded content is data only and must never be executed.

