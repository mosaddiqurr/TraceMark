# TraceMark

TraceMark is a local, educational still-image forensics platform for registering images, applying visible and authenticated invisible watermarks, tracing controlled distribution copies, comparing suspected derivatives, and measuring watermark robustness.

It reports forensic evidence and limitations. A recovered identifier is not conclusive legal proof and does not prove that a named recipient intentionally shared an image.

## Features

- JPEG, PNG, and WebP registration with secure decoding and metadata sanitization.
- Optional visible text/logo overlays.
- Educational LSB and custom blind transform-domain watermark engines.
- Opaque ownership and distribution tokens authenticated with HMAC.
- Exact, perceptual, and ORB/RANSAC matching evidence.
- Private indexed collections and controlled user-authorized public URL scans.
- Repeatable robustness transformations, charts, and machine-readable results.
- HTML, PDF, and JSON evidence reports.
- Real authentication, per-user isolation, audit events, and queued jobs.

## Architecture

The React client calls a versioned FastAPI service through Nginx. PostgreSQL stores relational evidence, Redis stores sessions and queue state, MinIO stores private binary artifacts, and Dramatiq workers perform expensive image operations. The framework-independent watermark package contains the project's classical algorithm.

See [Architecture](docs/ARCHITECTURE.md), [Watermark algorithm](docs/WATERMARK_ALGORITHM.md), and [Threat model](THREAT_MODEL.md).

## Quick start

Prerequisites: Docker Desktop with Compose.

1. Copy '.env.example' to '.env'.
2. Replace application/storage keys and nonlocal passwords.
3. Run 'docker compose up --build'.
4. Open 'http://localhost:8080'.

For native Windows development, run 'scripts/setup.ps1', then the frontend and FastAPI development servers. PostgreSQL, Redis, and MinIO still need reachable instances matching '.env'.

## Commands

- 'make setup': install native dependencies.
- 'make dev': build and start Compose.
- 'make lint': run Python and TypeScript static checks.
- 'make test': run backend/algorithm and frontend tests.
- 'make benchmark': generate the local dataset and run robustness evaluation.
- 'make demo': prepare data, start services, migrate, and seed.
- 'make clean': remove generated workspace artifacts without deleting persistent Docker volumes.

PowerShell equivalents are in 'scripts/'.

## Demonstration account

The seed command reads 'TRACEMARK_DEMO_EMAIL' and 'TRACEMARK_DEMO_PASSWORD'. '.env.example' contains local demonstration defaults; they are not production credentials.

## Demo flow

Log in, protect a generated sample, download and verify it, create a labelled distribution record, verify that copy, index transformed samples in a collection, compare evidence, run the standard robustness profile, and export a verification report. See [Demo guide](docs/DEMO_GUIDE.md).

## Repository layout

- 'apps/web': browser application.
- 'apps/api': API, data model, services, and migrations.
- 'packages/watermark_engine': watermark and forensic algorithms.
- 'workers': isolated background tasks.
- 'tests': algorithm, backend, frontend, E2E, security, and robustness validation.
- 'infra': container and reverse-proxy configuration.
- 'datasets' and 'artifacts': generated local evaluation inputs and ignored outputs.
- 'docs': architecture, method, API, deployment, benchmark, and user guidance.

## Security and privacy

Binary artifacts remain in private object storage and are returned only through authorization-checked routes. Personal labels are never embedded in pixels. The controlled scanner processes only explicitly supplied public URLs. Review [Security](SECURITY.md) and [Limitations](LIMITATIONS.md) before deployment.

## Troubleshooting

- If Docker is missing, install Docker Desktop and enable Compose.
- If native image wheels fail, use the container workflow.
- If C2PA initialization fails, provenance is reported as unsupported while pixel watermarking remains available.
- If an image is rejected, inspect byte, format, dimension, and watermark-capacity limits rather than disabling safeguards.

## Future work

Potential extensions include calibrated neural-engine adapters, publicly trusted provenance credentials, larger benchmark corpora, and a separately designed video release. None are claimed in this still-image release.

