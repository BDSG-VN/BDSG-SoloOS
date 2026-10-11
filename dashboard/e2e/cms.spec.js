import { test, expect } from "./fixtures.js";
import { readFileSync, mkdirSync } from "node:fs";
const token = readFileSync(new URL("../../.env", import.meta.url), "utf8")
  .split("\n")
  .find((l) => l.startsWith("BDSG_OWNER_TOKEN="))
  .slice("BDSG_OWNER_TOKEN=".length);
test("CMS preserves public snapshot, restores drafts and creates an AI proposal", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto("/admin");
  await page.getByLabel("Dùng khóa máy chủ").check();
  await page.getByLabel("Khóa chủ doanh nghiệp").fill(token);
  await page.getByRole("button", { name: "Mở không gian làm việc" }).click();
  await page
    .getByRole("button", { name: "Nội dung & website", exact: true })
    .click();
  await page.getByRole("button", { name: "Trang", exact: true }).click();
  await page.getByRole("button", { name: "+ Trang mới", exact: true }).click();
  const title = `Trang kiểm thử ${Date.now()}`;
  await page.getByLabel("Tiêu đề", { exact: true }).fill(title);
  await page
    .getByRole("textbox", { name: "Nội dung khối 1", exact: true })
    .fill("Nội dung công khai ban đầu.");
  await page.getByRole("button", { name: "Lưu bản nháp", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Đã lưu bản nháp");
  await page
    .getByRole("button", { name: "Xuất bản phiên bản đã lưu", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("Đã xuất bản.");
  const publicURL = await page
    .getByRole("link", { name: "Mở trang công khai ↗" })
    .getAttribute("href");
  expect((await page.request.get(publicURL)).status()).toBe(200);
  await page
    .getByRole("textbox", { name: "Nội dung khối 1", exact: true })
    .fill("Bản nháp riêng tư mới.");
  await page.getByRole("button", { name: "Lưu bản nháp", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Đã lưu bản nháp");
  expect(await (await page.request.get(publicURL)).text()).not.toContain(
    "Bản nháp riêng tư mới.",
  );
  await page
    .getByRole("button", { name: "Lịch sử phiên bản", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Khôi phục chỉ thay bản nháp" }),
  ).toBeVisible();
  mkdirSync(new URL("../../artifacts/", import.meta.url), { recursive: true });
  await page.screenshot({
    path: "../artifacts/cms-editor.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../artifacts/cms-mobile.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Chuyển vào thùng rác", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("Đã cập nhật trạng thái.");
  expect((await page.request.get(publicURL)).status()).toBe(404);
  // Mock only external AI settings and generation; persistence above uses the real server.
  await page.route("**/api/cms/settings", (route) =>
    route.fulfill({
      json: {
        homepage_id: null,
        gateway: {
          configured: true,
          model: "test",
          base_url: "https://example.invalid/v1",
        },
      },
    }),
  );
  await page.reload();
  await page.getByRole("button", { name: "Mở menu" }).click();
  await page
    .getByRole("button", { name: "Nội dung & website", exact: true })
    .click();
  await page
    .getByRole("button", { name: "+ Bài viết mới", exact: true })
    .click();
  const proposal = {
    kind: "post",
    title: "Đề xuất từ AI kiểm thử",
    slug: "ai-test",
    excerpt: "Đề xuất",
    blocks: [
      { type: "paragraph", text: "Thông tin cần người biên tập xác minh." },
    ],
    categories: [],
    tags: [],
    sources: [],
    seo_title: "",
    seo_description: "",
    ai_generated: true,
  };
  await page.route("**/api/cms/generate", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: [
        { type: "token", text: "text" },
        { type: "proposal", content: proposal },
        { type: "done" },
      ]
        .map((x) => "data: " + JSON.stringify(x) + "\n\n")
        .join(""),
    }),
  );
  await page.getByLabel("Lệnh cho AI").fill("Viết tin thử nghiệm");
  await page.getByLabel("Tiêu đề", { exact: true }).fill("Bản đang viết");
  await page
    .getByRole("button", { name: "Tạo đề xuất bằng AI", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Lưu nội dung");
  await expect(page.getByLabel("Tiêu đề", { exact: true })).toHaveValue(
    "Bản đang viết",
  );
  await page.getByLabel("Tiêu đề", { exact: true }).fill("");
  await page
    .getByRole("button", { name: "Tạo đề xuất bằng AI", exact: true })
    .click();
  await expect(page.getByRole("status").first()).toContainText(
    "AI đã tạo đề xuất",
  );
  await expect(page.getByLabel("Tiêu đề", { exact: true })).toHaveValue(
    proposal.title,
  );
  expect((await page.request.get("/news/ai-test")).status()).toBe(404);
  await page.getByRole("button", { name: "Mở menu" }).click();
  page.removeAllListeners("dialog");
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Tổng quan", exact: true }).click();
  await expect(page.getByLabel("Tiêu đề", { exact: true })).toHaveValue(
    proposal.title,
  );
  expect(errors).toEqual([]);
});
