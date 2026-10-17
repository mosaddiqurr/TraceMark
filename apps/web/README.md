# TraceMark frontend

React + TypeScript + Vite. Four destinations: Home, Protect, Verify, About.

`pnpm dev`, `pnpm build`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm e2e`.

Set build-time `VITE_API_URL` to the complete API prefix (default `/api/v1`). Development proxies to `http://127.0.0.1:8000`; override `TRACEMARK_API_PROXY_TARGET` as needed. Browser downloads use validated Blob responses with safe filenames and cleanup.

The supplied logo, derived favicon and procedural sample are bundled in public. Regenerate them from the root with `python scripts/prepare_assets.py`.

Netlify and Vercel publish dist with the checked-in SPA redirects/security headers. Exact CORS and browser-cookie hosting arrangements are documented in [Deployment](../../docs/DEPLOYMENT.md).

Playwright builds the production frontend with a direct API prefix, starts a real isolated API and checks 1440/1366/768/390 px. `TRACEMARK_WEB_URL` may target an already-running deployment instead.
