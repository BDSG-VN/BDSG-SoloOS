import { test, expect } from "./fixtures.js";
import { readFileSync } from "node:fs";
const token = readFileSync(new URL("../../.env", import.meta.url), "utf8")
  .split("\n")
  .find((l) => l.startsWith("BDSG_OWNER_TOKEN="))
  .slice("BDSG_OWNER_TOKEN=".length);
test("public home and account remain separate from owner; templates are editable drafts", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByLabel("Khóa chủ doanh nghiệp")).toHaveCount(0);
  await page.goto("/account");
  await expect(
    page.getByRole("heading", { name: "Tài khoản khách hàng" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Đăng nhập", exact: true }),
  ).toBeVisible();
  await page.goto("/admin");
  await page.getByLabel("Dùng khóa máy chủ").check();
  await page.getByLabel("Khóa chủ doanh nghiệp").fill(token);
  await page.getByRole("button", { name: "Mở không gian làm việc" }).click();
  await page
    .getByRole("button", { name: "Nội dung & website", exact: true })
    .click();
  await page
    .getByText("Giao diện & thông tin website", { exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Tạo trang từ mẫu" }),
  ).toHaveCount(8);
  await expect(page.locator('.theme-thumbnail iframe')).toHaveCount(8);
  await page.getByRole('button', {name: 'Xem trước', exact: true}).first().click();
  const preview = page.getByRole('dialog');
  await expect(preview).toBeVisible();
  await expect(page.frameLocator('dialog iframe').getByRole('heading', {name: 'Chia sẻ kinh nghiệm. Kết nối cơ hội.'})).toBeVisible();
  await preview.getByRole('button', {name: 'Điện thoại', exact: true}).click();
  await expect(preview.locator('iframe')).toHaveCSS('width', '390px');
  await page.screenshot({path: '../artifacts/theme-preview-mobile.png'});
  await preview.getByRole('button', {name: 'Máy tính', exact: true}).click();
  await page.screenshot({path: '../artifacts/theme-preview-desktop.png'});
  await page.keyboard.press('Escape');
  await expect(preview).toHaveCount(0);
  await page
    .getByRole("article")
    .filter({
      has: page.getByRole("heading", { name: "Cá nhân & chuyên gia" }),
    })
    .getByRole("button", { name: "Tạo trang từ mẫu" })
    .click();
  await expect(page.getByLabel("Tiêu đề", { exact: true })).not.toBeEmpty();
  await page.screenshot({
    path: "../artifacts/site-themes.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("navigation", { name: "Điều hướng chính" }),
  ).not.toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../artifacts/site-themes-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
