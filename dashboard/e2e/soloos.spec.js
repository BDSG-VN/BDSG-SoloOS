import { test, expect } from "@playwright/test";
import { readFileSync, mkdirSync } from "node:fs";

const config = readFileSync(new URL("../../.env", import.meta.url), "utf8");
const token = config
  .split("\n")
  .find((line) => line.startsWith("BDSG_OWNER_TOKEN="))
  .slice("BDSG_OWNER_TOKEN=".length);
test("owner signs in, sees streaming UI, submits a form and approves a real MCP write", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("Khóa chủ doanh nghiệp").fill(token);
  await page.getByRole("button", { name: "Mở không gian làm việc" }).click();
  await expect(
    page.getByRole("heading", { name: "Tổng quan", exact: true }),
  ).toBeVisible();
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(
    token,
  );
  mkdirSync(new URL("../../artifacts/", import.meta.url), { recursive: true });
  await page.screenshot({ path: "../artifacts/overview.png", fullPage: true });
  await page.getByRole("button", { name: "Thử luồng giao diện mẫu" }).click();
  await expect(
    page.getByRole("img", { name: "Doanh thu minh họa (triệu đồng)" }),
  ).toBeVisible();
  const submit = page.getByRole("button", { name: "Ghi nhận mục tiêu" });
  await expect(submit).toBeEnabled();
  const goal = `Mục tiêu kiểm tra ${Date.now()}`;
  await page.getByLabel("Mục tiêu của bạn").fill(goal);
  await submit.click();
  await expect(page.getByRole("status")).toContainText("Đã thêm mục tiêu");
  await page.screenshot({
    path: "../artifacts/streaming-ui.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Công việc", exact: true }).click();
  await expect(page.getByText(goal, { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Công việc", exact: true }).click();
  await expect(page.getByText(goal, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Bộ nhớ", exact: true }).click();
  await page.getByLabel("Đường dẫn Markdown").fill("wiki/e2e.md");
  await page
    .getByLabel("Nội dung", { exact: true })
    .fill("# Kiểm tra\nGhi chú được lưu qua MCP sau phê duyệt.");
  await page.getByRole("button", { name: "Lưu qua MCP Hub" }).click();
  await expect(page.getByRole("status")).toContainText("phê duyệt");
  await page.getByRole("button", { name: /Phê duyệt/ }).click();
  await expect(
    page.getByText("second-brain / write_note", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Duyệt và thực thi" }).click();
  await expect(page.getByRole("status")).toContainText("Đã duyệt và thực thi");
  await page.getByRole("button", { name: "Bộ nhớ", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /wiki\/e2e.md/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Kết nối MCP", exact: true }).click();
  await page.getByRole("button", { name: "Chỉnh sửa quyền →" }).click();
  await expect(page.getByLabel("Cấu hình MCP JSON")).toHaveValue(
    /"id": "second-brain"/,
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Tổng quan", exact: true }).click();
  await page.screenshot({ path: "../artifacts/mobile.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
