import { test, expect } from "./fixtures.js";
import { readFileSync } from "node:fs";
const token = readFileSync(new URL("../../.env", import.meta.url), "utf8")
  .split("\n")
  .find((l) => l.startsWith("BDSG_OWNER_TOKEN="))
  .slice("BDSG_OWNER_TOKEN=".length);
test("isolated brain proposal requires review, revisions remain available, shares revoke", async ({
  page,
  context,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("dialog", (d) => d.accept());
  await page.goto("/admin");
  await page.getByLabel("Dùng khóa máy chủ").check();
  await page.getByLabel("Khóa chủ doanh nghiệp").fill(token);
  await page.getByRole("button", { name: "Mở không gian làm việc" }).click();
  await page
    .getByRole("button", { name: "Thư viện bộ nhớ", exact: true })
    .click();
  const title = `Brain QA ${Date.now()}`;
  await page.getByLabel("Tên bộ nhớ mới").fill(title);
  await page.getByRole("button", { name: "Tạo bộ nhớ", exact: true }).click();
  await expect(
    page
      .getByRole("combobox", { name: "Bộ nhớ", exact: true })
      .locator("option:checked"),
  ).toHaveText(title);
  await page
    .getByLabel("Nội dung đề xuất")
    .fill("Thông tin được xác nhận cho bộ nhớ riêng.");
  await page.getByRole("button", { name: "Đề xuất lưu tài liệu" }).click();
  const proposal = page
    .locator("details")
    .filter({ hasText: "memory/FACTS.md" });
  await proposal.locator("summary").click();
  await proposal
    .getByRole("button", { name: "Duyệt và ghi vào bộ nhớ" })
    .click();
  await page
    .getByRole("button", { name: "memory/FACTS.md", exact: true })
    .click();
  await expect(page.getByLabel("Nội dung đề xuất")).toHaveValue(
    "Thông tin được xác nhận cho bộ nhớ riêng.",
  );
  await page.getByRole("button", { name: "Lịch sử tài liệu" }).click();
  await expect(
    page.getByRole("button", {
      name: "Dùng bản này để đề xuất khôi phục",
      includeHidden: true,
    }),
  ).toHaveCount(1);
  await page
    .getByRole("button", { name: "Trò chuyện & dự án", exact: true })
    .click();
  await page
    .getByLabel("Bộ nhớ cho cuộc trò chuyện mới")
    .selectOption({ label: title });
  await page
    .getByRole("button", { name: "Cuộc trò chuyện mới", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Nhập bằng giọng nói" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Trò chuyện & dự án", exact: true })
    .click();
  const row = page
    .locator("article")
    .filter({ hasText: "Cuộc trò chuyện mới" })
    .first();
  await row.getByRole("button", { name: "Tạo liên kết chia sẻ" }).click();
  const link = page.locator('a[href^="/share/"]');
  await expect(link).toBeVisible();
  const url = await link.getAttribute("href");
  const anon = await context.browser().newContext();
  const shared = await anon.newPage();
  await shared.goto(new URL(url, page.url()).href);
  await expect(
    shared.getByText("Bản chụp chỉ đọc.", { exact: false }),
  ).toBeVisible();
  await anon.close();
  await page
    .getByRole("button", { name: "Thu hồi", exact: true })
    .first()
    .click();
  expect((await page.request.get(url)).status()).toBe(404);
  await page
    .getByRole("button", { name: "Thư viện bộ nhớ", exact: true })
    .click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../artifacts/library-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
