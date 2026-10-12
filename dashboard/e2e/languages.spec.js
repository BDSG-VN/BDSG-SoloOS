import { test, expect } from "./fixtures.js";
import { readFileSync } from "node:fs";
const token = readFileSync(new URL("../../.env", import.meta.url), "utf8")
  .split("\n").find((line) => line.startsWith("BDSG_OWNER_TOKEN="))
  .slice("BDSG_OWNER_TOKEN=".length);

test("language switching preserves an unsaved task and persists across reload", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/admin?lang=vi");
  const login = await page.request.post("/api/session", { headers: { Origin: new URL(page.url()).origin }, data: { token } });
  expect(login.ok()).toBeTruthy();
  await page.reload();
  await page.getByRole("button", { name: "Công việc", exact: true }).click();
  const draft = "Bản nháp tiếng Việt — keep my content";
  await page.getByLabel("Tên công việc", { exact: true }).fill(draft);
  await page.getByLabel("Language / Ngôn ngữ").selectOption("en");
  await expect(page.getByLabel("Task name", { exact: true })).toHaveValue(draft);
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.getByLabel("Language / Ngôn ngữ").selectOption("vi");
  await expect(page.getByLabel("Tên công việc", { exact: true })).toHaveValue(draft);
  await page.getByLabel("Tên công việc", { exact: true }).fill("");
  await page.getByLabel("Language / Ngôn ngữ").selectOption("en");
  await page.reload();
  await expect(page.getByLabel("Language / Ngôn ngữ")).toHaveValue("en");
  expect(errors).toEqual([]);
});
