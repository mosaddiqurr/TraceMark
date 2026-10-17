import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: { entries: ["index.html"] },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target:
          process.env.TRACEMARK_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
  },
});
