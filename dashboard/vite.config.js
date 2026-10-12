import { defineConfig } from "vite";

export default defineConfig({
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  test: { setupFiles: ["./i18n/test_setup.js"], environment: "jsdom", exclude: ["**/node_modules/**", "e2e/**"] },
});
