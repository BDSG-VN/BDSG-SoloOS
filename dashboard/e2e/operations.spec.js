import { test, expect } from "./fixtures.js";
import { readFileSync } from "node:fs";
const token = readFileSync(new URL("../../.env", import.meta.url), "utf8")
  .split("\n")
  .find((l) => l.startsWith("BDSG_OWNER_TOKEN="))
  .slice(17);
test("calendar preview, reviewed pack, workboard and mobile navigation", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("dialog", (d) => d.accept());
  await page.goto("/admin");
  await page.getByLabel("Dùng khóa máy chủ").check();
  await page.getByLabel("Khóa chủ doanh nghiệp").fill(token);
  await page.getByRole("button", { name: "Mở không gian làm việc" }).click();
  const nav = page.getByRole("navigation", { name: "Điều hướng chính" });
  await expect(
    nav.getByRole("heading", { name: "Làm việc", exact: true }),
  ).toBeVisible();
  await nav.getByLabel("Tìm chức năng").fill("vận hành");
  await expect(nav.getByRole("button")).toHaveCount(1);
  await nav.getByRole("button", { name: "Trung tâm vận hành" }).click();
  await expect(
    page.getByRole("heading", { name: "Hộp thông báo" }),
  ).toBeVisible();
  await nav.getByRole("button", { name: "Tự động hóa", exact: true }).click();
  const flow = `Calendar QA ${Date.now()}`;
  await page.getByLabel("Tên", { exact: true }).fill(flow);
  await page.getByLabel("Loại bước 1").selectOption("note");
  await page.getByLabel("Yêu cầu bước 1").fill("Local reminder");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await page.getByLabel("Quy trình của lịch").selectOption({ label: flow });
  await page.getByLabel("Kiểu lịch").selectOption("cron");
  await page.getByLabel("Múi giờ", { exact: true }).fill("Asia/Ho_Chi_Minh");
  await page.getByRole("button", { name: "Xem trước lần chạy" }).click();
  await expect(
    page
      .getByRole("list", { name: "Các lần chạy dự kiến" })
      .getByRole("listitem"),
  ).toHaveCount(5);
  await page.getByRole("button", { name: "Lưu lịch", exact: true }).click();
  const schedule = page.locator(".schedule-row").filter({ hasText: flow });
  await expect(schedule).toContainText("Tạm dừng");
  await page.locator(".packs summary").click();
  await page.getByLabel("Chọn gói JSON").setInputFiles({
    name: "qa-pack.json",
    mimeType: "application/json",
    buffer: Buffer.from(
      JSON.stringify({
        format: "soloos-pack-v1",
        title: "QA Pack",
        skills: {
          draft: { title: "Pack QA skill", instruction: "Draft only" },
        },
      }),
    ),
  });
  await expect(page.getByRole("heading", { name: "QA Pack" })).toBeVisible();
  await page.getByRole("button", { name: "Nhập gói đã xem" }).click();
  await expect(page.locator(".packs").getByRole("status")).toContainText(
    "trạng thái tắt",
  );
  await nav.getByRole("button", { name: "Công việc", exact: true }).click();
  const title = `Work QA ${Date.now()}`;
  await page.getByLabel("Tên công việc", { exact: true }).fill(title);
  await page
    .getByText("Chi tiết, ưu tiên & phân công", { exact: true })
    .click();
  await page.getByLabel("Mức ưu tiên").selectOption("urgent");
  await page.getByLabel("Hạn hoàn thành").fill("2026-12-15");
  await page.getByLabel("Mô tả công việc").fill("Detailed owner task");
  await page.getByRole("button", { name: "Thêm việc", exact: true }).click();
  const card = page.locator(".task-card").filter({ hasText: title });
  await expect(card).toContainText("Khẩn cấp");
  await expect(card).toContainText("2026-12-15");
  await card.getByRole("combobox").selectOption("doing");
  await expect(
    page
      .locator(".kanban-col")
      .filter({ has: page.getByRole("heading", { name: /Đang làm/ }) }),
  ).toContainText(title);
  await page.screenshot({
    path: "../artifacts/operations-workboard.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Mở menu" }).click();
  await expect(
    nav.getByRole("button", { name: "Trung tâm vận hành" }),
  ).toBeVisible();
  await page.screenshot({ path: "../artifacts/operations-mobile-menu.png" });
  await nav.getByRole("button", { name: "Trung tâm vận hành" }).click();
  await expect(page.getByRole("button", { name: "Mở menu" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await expect(
    page.getByRole("heading", { name: "Hộp thông báo" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../artifacts/operations-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
