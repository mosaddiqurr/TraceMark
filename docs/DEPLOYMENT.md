# Direct deployment

TraceMark uses a static React build and one native FastAPI process. SQLite is necessary for private workspace capabilities and trace mappings across restarts. Uploaded images are discarded; downloads and reports remain in bounded memory.

## Frontend: Netlify or Vercel

Use the repository root, Node 24 and pnpm 10.30.3. Install with `pnpm install --frozen-lockfile`, build with `pnpm --dir apps/web build`, publish `apps/web/dist`. The checked-in `netlify.toml`, SPA fallback/security headers and `vercel.json` support both hosts.

Set this **build-time, public** environment variable, substituting the actual API hostname:

```text
VITE_API_URL=https://api.your-domain.example/api/v1
```

Use HTTPS custom subdomains of one site, such as `images.your-domain.example` and `api.your-domain.example`, with SameSite=Lax cookies. Add the exact frontend origin to backend CORS. Tighten `connect-src` in both frontend header configurations to the chosen API origin. SPA fallback supports refresh and direct /protect, /verify and /about visits.

See the official [Netlify Vite guide](https://docs.netlify.com/build/frameworks/framework-setup-guides/vite/) and [Vercel Vite guide](https://vercel.com/docs/frameworks/frontend/vite).

## Backend: Render native Python service

Create a Python web service with the repository root, Python 3.12 and one instance. The same commands work on equivalent Python hosts with a persistent private directory and an assigned `PORT`.

Build:

```sh
python -m pip install -r requirements.txt
python -m pip install --no-deps ./packages/watermark_engine ./apps/api
```

Start:

```sh
python -m uvicorn tracemark_api.main:create_app --factory --host 0.0.0.0 --port "$PORT" --workers 1 --no-access-log --no-proxy-headers
```

Readiness path: `/api/v1/ready`; liveness: `/api/v1/health`. The hosting ingress supplies HTTPS. The app uses the connected peer address for rate limits. Enforce client-aware request/connection/body limits at the ingress; enable forwarded-header trust only for explicitly trusted proxy addresses.

Attach a private persistent disk at `/var/data` and set `TRACEMARK_DATA_ROOT=/var/data/tracemark`. Render's default filesystem is ephemeral, and persistent disks require an eligible paid service. Only files under the mount survive deployments. See [native FastAPI deployment](https://render.com/docs/deploy-fastapi) and [persistent disks](https://render.com/docs/disks).

Reserve at least 1.5 GiB RAM at default image limits and at least 128 MiB shared-memory capacity for the timed processor. Run under a least-privileged account with host CPU/memory limits and bounded temporary storage. Avoid horizontal scaling: admission, rate windows and artifacts are process-local. A single-instance disk deployment can have restart downtime.

## Backend environment

Configure these through the host's secret/environment interface; do not load or publish a local `.env` in production.

| Variable | Production setting |
|---|---|
| `TRACEMARK_ENV` | `production` |
| `TRACEMARK_DATA_ROOT` | Absolute path inside the persistent private mount |
| `TRACEMARK_ALLOWED_ORIGINS` | Exact HTTPS frontend origins, comma-separated; no wildcard/path/trailing slash |
| `TRACEMARK_COOKIE_SECURE` | `true` |
| `TRACEMARK_COOKIE_SAMESITE` | `lax` with same-site custom subdomains |
| `TRACEMARK_MASTER_KEY` | Independent random secret, at least 32 characters |
| `TRACEMARK_REPORT_KEY` | Separate independent random secret, at least 32 characters |
| `TRACEMARK_SESSION_PEPPER` | Separate independent random secret, at least 32 characters |

Generate three values with a secure secret manager or Python's `secrets.token_urlsafe(48)`. Keep them stable across restarts and deployments. Startup rejects insecure cookies, development/short/equal keys and non-HTTPS production origins. Additional upload, retention, processing and memory settings are listed in `.env.example`; production defaults retain metadata for 30 days and temporary artifacts for 15 minutes.

For unrelated frontend/backend sites, direct cookie requests require SameSite=None/Secure and may still be blocked by browsers. Prefer same-site custom subdomains. Alternatively, configure a same-origin host rewrite before the SPA fallback, leave `VITE_API_URL=/api/v1`, and retain the frontend's exact origin:

```text
/api/* https://your-real-api-host.example/api/:splat 200
/* /index.html 200
```

That example is Netlify syntax; see [Netlify proxies](https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/). Check the provider's proxy timeout against the image-processing deadline. The same-origin path is an optional hosting arrangement; the measured browser gate uses direct cross-origin API requests.

## Local startup and persistence

Use the root README's venv/pip and pnpm commands. `scripts/init_secrets.py` fills only empty local secret values and never prints them. Only `TRACEMARK_DATA_ROOT/registry.sqlite3` and SQLite journals persist; no original image store or migration command is needed.

Restrict directory and backup permissions. Prefer SQLite's backup API or an offline backup. Logical clearing is not secure erasure of database pages or backups. Previous enterprise stores are not read, migrated or deleted automatically.

Run `make restart` or `scripts/restart.ps1`. This launches actual production-configured Uvicorn processes, protects/verifies/exports, stops and restarts the API, checks retained private mappings, expired transient links, resumed and new operations, and explicit clearing. Its loopback HTTP harness carries the production Secure cookie explicitly to represent an HTTPS ingress; it does not certify a provider's TLS configuration.

Before public operation run the documented lint/tests/benchmark/build/audits and production-build browser suite. A live host still needs its own HTTPS, cookie, CORS, ingress and persistent-mount smoke check. No hosted deployment is claimed in the local validation results.

