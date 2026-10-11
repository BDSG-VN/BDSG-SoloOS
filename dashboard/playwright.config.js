import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 60000,
  reporter: "list",
  use: {
    baseURL: process.env.BDSG_TEST_URL || "http://127.0.0.1:8000",
    headless: true,
    launchOptions: process.env.CHROME_BIN
      ? { executablePath: process.env.CHROME_BIN }
      : {},
  },
});
