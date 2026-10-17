import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const python =
  process.platform === "win32" ? ".venv\\Scripts\\python.exe" : "python";
const external = process.env.TRACEMARK_WEB_URL;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: external ?? "http://127.0.0.1:5184",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop-1440",
      use: { browserName: "chromium", viewport: { width: 1440, height: 960 } },
    },
    {
      name: "desktop-1366",
      use: { browserName: "chromium", viewport: { width: 1366, height: 900 } },
    },
    {
      name: "tablet-768",
      use: { browserName: "chromium", viewport: { width: 768, height: 1024 } },
    },
    {
      name: "mobile-390",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: external
    ? undefined
    : [
        {
          command: `${python} -m uvicorn scripts.e2e_api:create_app --factory --host 127.0.0.1 --port 8844 --no-access-log`,
          cwd: root,
          url: "http://127.0.0.1:8844/api/v1/ready",
          reuseExistingServer: false,
          timeout: 60_000,
        },
        {
          command:
            "pnpm build && pnpm preview --host 127.0.0.1 --port 5184 --strictPort",
          url: "http://127.0.0.1:5184",
          reuseExistingServer: false,
          timeout: 60_000,
          env: { VITE_API_URL: "http://127.0.0.1:8844/api/v1" },
        },
      ],
});
