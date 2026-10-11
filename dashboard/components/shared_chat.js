import React, { useEffect, useState } from "react";
import OpenUIRender from "./openui_render.js";
const h = React.createElement;
export default function SharedChat() {
  const [data, setData] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    const token = location.pathname.split("/").at(-1);
    fetch("/api/shared/" + encodeURIComponent(token), { credentials: "omit" })
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail);
        setData(d);
      })
      .catch((e) => setError(e.message));
  }, []);
  return h(
    "main",
    {
      className: "workspace-panel",
      style: { maxWidth: 900, margin: "40px auto", padding: 24 },
    },
    h("h1", null, data?.title || "Cuộc trò chuyện được chia sẻ"),
    h(
      "p",
      null,
      "Bản chụp chỉ đọc. Nội dung AI cần được kiểm chứng; các biểu mẫu ở đây không thực hiện thao tác.",
    ),
    error && h("p", { role: "alert" }, error),
    ...(data?.messages || []).map((m, i) =>
      h(
        "article",
        { key: i, className: "chat-message " + m.role },
        h("small", null, m.role === "user" ? "NGƯỜI DÙNG" : "AI"),
        m.role === "user"
          ? h("p", null, m.content)
          : h("div", { inert: true }, h(OpenUIRender, { response: m.content })),
      ),
    ),
  );
}
