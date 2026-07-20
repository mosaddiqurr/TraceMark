# TraceMark web client

The React client renders evidence returned by the versioned API; it does not calculate or invent forensic outcomes in the browser.

## Local commands

```text
pnpm install
pnpm dev
pnpm build
pnpm lint
pnpm test
pnpm e2e
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Set `VITE_API_URL` to override `/api/v1`. Authentication uses the API's opaque HTTP-only session cookie. The browser retains only the session response's CSRF token in memory and sends it on state-changing requests.

The end-to-end suite includes desktop and mobile Chromium projects. Set `TRACEMARK_WEB_URL` to test an already-running deployment.
