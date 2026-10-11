import { defineConfig } from "vite";

export default defineConfig({
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  test: { environment: "jsdom", exclude: ["**/node_modules/**", "e2e/**"] },
});
