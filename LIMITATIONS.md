# Known Limitations

- TraceMark supports JPEG, PNG, and WebP still images only; video, audio, animation, and nested archives are out of scope.
- A recovered distribution token identifies the database copy that carried it. It does not prove who shared the file, recipient intent, authorship, or a legal conclusion.
- Severe crops, geometric distortion, repainting, or deliberate watermark removal can defeat a classical blind watermark.
- The recorded quick benchmark recovered 0/2 robust marks after 75% resizing. Resize synchronization requires further research and is not represented as working.
- The present negative benchmark is deliberately small; it demonstrates integrity behavior but is not a statistically meaningful population false-positive estimate.
- Perceptual and local-feature matches indicate visual similarity, not cryptographic identity. The current API vertical slice uses pHash thresholds for classification and exposes ORB/RANSAC through the engine interface; wider calibration is unfinished.
- C2PA is optional. The SDK/native binding was unavailable on this host, so the browser demonstration correctly reported `unsupported`; signing with development credentials was not exercised.
- Public scanning is limited to a supplied direct image or one HTML page. It is not a crawler and cannot establish absence from the internet. Robots enforcement is not yet complete.
- Protection, scan, collection rescan, benchmark, and report generation currently run synchronously in the API vertical slice. Dramatiq queues exist but are not yet the execution path, so production cancellation/timeouts/quotas are not accepted.
- The generated PDF path is covered by API behavior but has not received the required rendered-page visual review.
- The frontend production bundle is about 718 kB before gzip and emits a code-splitting advisory.
- Docker Desktop is unavailable on the host. PostgreSQL, Redis, MinIO, Nginx, worker isolation, Compose health, persistence, and full container E2E remain unverified.