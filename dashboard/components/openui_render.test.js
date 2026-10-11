import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { TextDecoder, TextEncoder } from "node:util";
import { ReadableStream } from "node:stream/web";
import OpenUIRender from "./openui_render.js";
import { readSSE } from "./stream.js";

globalThis.TextDecoder = TextDecoder;
globalThis.TextEncoder = TextEncoder;
globalThis.requestAnimationFrame = (fn) => setTimeout(fn, 0);
globalThis.cancelAnimationFrame = clearTimeout;
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const h = React.createElement;

function chunks(text, size = 1) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(controller) {
      for (let i = 0; i < bytes.length; i += size)
        controller.enqueue(bytes.slice(i, i + size));
      controller.close();
    },
  });
}

describe("Streaming transport", () => {
  it("preserves Vietnamese UTF-8, CRLF, multiline SSE and ignores comments", async () => {
    const body = chunks(
      ': keepalive\r\n\r\ndata: {"type":\r\ndata: "token", "text":"Doanh nghiệp Việt"}\r\n\r\ndata: [DONE]\n\n',
    );
    const events = [];
    for await (const event of readSSE(body)) events.push(event);
    expect(events).toEqual([
      { type: "token", text: "Doanh nghiệp Việt" },
      { type: "done" },
    ]);
  });
  it("rejects oversized and truncated events", async () => {
    await expect(async () => {
      for await (const event of readSSE(chunks('data: {"type":"done"}\n\n'), {
        maxBytes: 4,
      }))
        void event;
    }).rejects.toThrow("giới hạn");
    await expect(async () => {
      for await (const event of readSSE(chunks('data: {"type":"done"}')))
        void event;
    }).rejects.toThrow("giữa một sự kiện");
  });
});

describe("Official OpenUI runtime integration", () => {
  const code =
    'root = Stack([t, c, p, f])\nt = Text("Chào doanh nghiệp")\nc = BarChart("Doanh thu", ["T1", "T2"], [10, 20])\np = Progress("Triển khai", 50)\nf = Form("business", "Mục tiêu", [i], "Ghi nhận")\ni = Input("goal", "Mục tiêu tuần", "Nhập mục tiêu")\n';
  it("renders charts and submits state without granting MCP authority", async () => {
    const action = vi.fn();
    render(h(OpenUIRender, { response: code, onAction: action }));
    await screen.findByText("Chào doanh nghiệp");
    expect(screen.getByRole("img", { name: "Doanh thu" })).toBeTruthy();
    expect(screen.getByRole("progressbar").value).toBe(50);
    fireEvent.change(screen.getByLabelText("Mục tiêu tuần"), {
      target: { value: "Tìm 5 khách hàng" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ghi nhận" }));
    await waitFor(() => expect(action).toHaveBeenCalled());
    expect(action.mock.calls[0][0].formName).toBe("business");
    expect(action.mock.calls[0][0].formState.business.goal.value).toBe(
      "Tìm 5 khách hàng",
    );
  });
  it("renders partial output and disables form actions while streaming", async () => {
    render(
      h(OpenUIRender, { response: code.slice(0, -15), isStreaming: true }),
    );
    await screen.findByText("Chào doanh nghiệp");
    expect(screen.getByRole("button", { name: "Ghi nhận" }).disabled).toBe(
      true,
    );
  });
  it("accumulates actual SSE tokens through completion", async () => {
    const wire =
      [...code]
        .map(
          (character) =>
            `data: ${JSON.stringify({ type: "token", text: character })}\n\n`,
        )
        .join("") + 'data: {"type":"done"}\n\n';
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(chunks(wire, 3), {
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const complete = vi.fn();
    render(h(OpenUIRender, { url: "/api/stream", onComplete: complete }));
    await screen.findByText("Chào doanh nghiệp");
    await waitFor(() => expect(complete).toHaveBeenCalledWith(code));
    expect(screen.getByRole("button", { name: "Ghi nhận" }).disabled).toBe(
      false,
    );
  });
  it("requires a done event and reports disconnected streams", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        chunks('data: {"type":"token","text":"root = Stack([])"}\n\n'),
        { headers: { "Content-Type": "text/event-stream" } },
      ),
    );
    render(h(OpenUIRender, { url: "/api/stream" }));
    expect((await screen.findByRole("alert")).textContent).toContain(
      "trước tín hiệu",
    );
  });
  it("renders model text as text and never evaluates JavaScript", async () => {
    render(
      h(OpenUIRender, {
        response: 'root = Stack([t])\nt = Text("<script>alert(1)</script>")',
      }),
    );
    await screen.findByText("<script>alert(1)</script>");
    expect(document.querySelector("script")).toBeNull();
  });
});
