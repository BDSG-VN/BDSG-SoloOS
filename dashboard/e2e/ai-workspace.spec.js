import { test, expect } from "./fixtures.js";
import { readFileSync, mkdirSync } from "node:fs";
const token = readFileSync(new URL("../../.env", import.meta.url), "utf8")
  .split("\n")
  .find((l) => l.startsWith("BDSG_OWNER_TOKEN="))
  .slice("BDSG_OWNER_TOKEN=".length);
test("AI accounts, project sessions and durable workflow results", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/admin");
  await page.getByLabel("Dùng khóa máy chủ").check();
  await page.getByLabel("Khóa chủ doanh nghiệp").fill(token);
  await page.getByRole("button", { name: "Mở không gian làm việc" }).click();
  await page.getByRole("button", { name: "Tài khoản AI", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Continue with ChatGPT" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Kiểm tra Claude Code" }).click();
  await expect(page.getByRole("status")).toContainText("Chưa cài");
  await page
    .getByRole("button", { name: "Trò chuyện & dự án", exact: true })
    .click();
  const title = `Project QA ${Date.now()}`;
  await page.getByLabel("Tên dự án", { exact: true }).fill(title);
  await page
    .getByLabel("Bối cảnh", { exact: true })
    .fill("Bối cảnh riêng kiểm thử.");
  await page.getByRole("button", { name: "Lưu dự án", exact: true }).click();
  await expect(page.getByText(title, { exact: true }).last()).toBeVisible();
  await page
    .getByRole("button", { name: "Cuộc trò chuyện mới", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Quản lý tài khoản AI" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Tự động hóa", exact: true }).click();
  const workflow = `Reminder QA ${Date.now()}`;
  await page.getByLabel("Tên", { exact: true }).fill(workflow);
  await page.getByLabel("Loại bước 1").selectOption("note");
  await page
    .getByLabel("Yêu cầu bước 1")
    .fill("Một ghi chú thử nghiệm cục bộ.");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  const row = page.locator("article").filter({ hasText: workflow });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Chạy", exact: true }).click();
  await expect(
    page.locator("summary").filter({ hasText: workflow }),
  ).toContainText("completed", { timeout: 15000 });
  mkdirSync(new URL("../../artifacts/", import.meta.url), { recursive: true });
  await page.screenshot({
    path: "../artifacts/ai-workspace-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../artifacts/ai-workspace-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
