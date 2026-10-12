import { t as uiText, localeTag } from "../i18n/runtime.js";
/** Decode SSE independently of UTF-8 / TCP chunk boundaries, including multi-line data. */
export async function* readSSE(body, { maxBytes = 2_000_000 } = {}) {
  if (!body) throw new Error(uiText("API không trả về luồng dữ liệu."));
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "",
    bytes = 0;
  const parse = (block) => {
    const payload = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).replace(/^ /, ""))
      .join("\n");
    if (!payload) return null;
    if (payload === "[DONE]") return { type: "done" };
    return JSON.parse(payload);
  };
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (value) {
        bytes += value.byteLength;
        if (bytes > maxBytes) throw new Error(uiText("Luồng dữ liệu vượt giới hạn."));
      }
      buffer += done
        ? decoder.decode()
        : decoder.decode(value, { stream: true });
      let match;
      while ((match = /\r?\n\r?\n/.exec(buffer))) {
        const block = buffer.slice(0, match.index);
        buffer = buffer.slice(match.index + match[0].length);
        const event = parse(block);
        if (event) yield event;
      }
      if (done) {
        if (buffer.trim())
          throw new Error(uiText("Luồng SSE kết thúc giữa một sự kiện."));
        return;
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
