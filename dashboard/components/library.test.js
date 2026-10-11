import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import Library from "./library.js";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("ignores an old brain response and preserves edits when switching is declined", async () => {
  let resolveOld;
  let reads = 0;
  const api = vi.fn(async (path) => {
    if (path === "/library")
      return [
        { id: "default", title: "Default" },
        { id: "b", title: "Brain B" },
      ];
    if (path === "/library/default/notes") {
      if (reads++ === 0) return [];
      return new Promise((resolve) => {
        resolveOld = resolve;
      });
    }
    if (path === "/library/b/notes")
      return [{ path: "wiki/B.md", content: "B only" }];
    return [];
  });
  render(React.createElement(Library, { api, post: vi.fn(async () => ({})) }));
  await screen.findByRole("option", { name: "Brain B" });
  fireEvent.click(screen.getByRole("button", { name: "Đề xuất lưu tài liệu" }));
  await act(async () => {});
  fireEvent.change(screen.getByLabelText("Bộ nhớ", { exact: true }), {
    target: { value: "b" },
  });
  await screen.findByRole("button", { name: "wiki/B.md" });
  await act(async () => resolveOld([{ path: "wiki/A.md", content: "A only" }]));
  expect(screen.queryByRole("button", { name: "wiki/A.md" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "wiki/B.md" }));
  fireEvent.change(screen.getByLabelText("Nội dung đề xuất"), {
    target: { value: "unsaved B" },
  });
  vi.spyOn(window, "confirm").mockReturnValue(false);
  fireEvent.change(screen.getByLabelText("Bộ nhớ", { exact: true }), {
    target: { value: "default" },
  });
  expect(screen.getByLabelText("Bộ nhớ", { exact: true }).value).toBe("b");
  expect(screen.getByLabelText("Nội dung đề xuất").value).toBe("unsaved B");
});
it("does not overwrite edits made while an imported file is being read", async () => {
  const api = async (path) =>
    path === "/library" ? [{ id: "default", title: "Default" }] : [];
  render(React.createElement(Library, { api, post: vi.fn() }));
  await screen.findByRole("option", { name: "Default" });
  let finish;
  const file = {
    name: "import.md",
    size: 10,
    text: () => new Promise((r) => (finish = r)),
  };
  fireEvent.change(screen.getByLabelText("Nhập tài liệu văn bản"), {
    target: { files: [file] },
  });
  fireEvent.change(screen.getByLabelText("Nội dung đề xuất"), {
    target: { value: "new human edit" },
  });
  await act(async () => finish("old imported text"));
  expect(screen.getByLabelText("Nội dung đề xuất").value).toBe(
    "new human edit",
  );
});
it("checks current unsaved edits when create-brain finishes", async () => {
  const api = async (path) =>
    path === "/library" ? [{ id: "default", title: "Default" }] : [];
  let finish;
  const post = () => new Promise((r) => (finish = r));
  render(React.createElement(Library, { api, post }));
  await screen.findByRole("option", { name: "Default" });
  fireEvent.change(screen.getByLabelText("Tên bộ nhớ mới"), {
    target: { value: "New" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Tạo bộ nhớ" }));
  fireEvent.change(screen.getByLabelText("Nội dung đề xuất"), {
    target: { value: "pending edit" },
  });
  vi.spyOn(window, "confirm").mockReturnValue(false);
  await act(async () => finish({ id: "new" }));
  expect(window.confirm).toHaveBeenCalled();
  expect(screen.getByLabelText("Bộ nhớ", { exact: true }).value).toBe(
    "default",
  );
  expect(screen.getByLabelText("Nội dung đề xuất").value).toBe("pending edit");
});
