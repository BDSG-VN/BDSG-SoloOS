import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useState } from "react";
const h = React.createElement;
export default function Packs({ post, onSaved }) {
  const [body, setBody] = useState(null),
    [preview, setPreview] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  return h(
    "details",
    { className: "packs" },
    h("summary", null, uiText("Gói kỹ năng & quy trình")),
    h(
      "p",
      null,
      uiText("Chia sẻ cấu hình có thể đọc được. Gói nhập luôn tắt, không chạy mã và không tự cấp quyền công cụ."),
    ),
    h(
      "a",
      { href: "/api/automation/pack", download: true },
      uiText("Xuất gói hiện tại"),
    ),
    h(
      "label",
      null,
      uiText("Chọn gói JSON"),
      h("input", {
        type: "file",
        accept: ".json,application/json",
        disabled: busy,
        onChange: async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          setBusy(true);
          setPreview(null);
          setBody(null);
          setError("");
          setNotice("");
          try {
            if (file.size > 500000) throw Error(uiText("Gói tối đa 500 KB."));
            const value = JSON.parse(await file.text());
            const result = await post("/automation/pack/preview", value);
            setBody(value);
            setPreview(result);
          } catch (e) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        },
      }),
    ),
    error && h("p", { role: "alert" }, error),
    notice && h("p", { role: "status" }, notice),
    preview &&
      h(
        "section",
        null,
        h("h4", null, preview.title),
        ...Object.entries(preview.items).map(([kind, titles]) =>
          h(
            "p",
            { key: kind },
            `${{ skills: uiText("Kỹ năng"), agents: uiText("Trợ lý"), workflows: uiText("Quy trình") }[kind]}: ${titles.join(", ") || uiText("Không có")}`,
          ),
        ),
        h("p", null, preview.notice),
        h(
          "button",
          {
            disabled: busy,
            onClick: async () => {
              setBusy(true);
              try {
                await post("/automation/pack/import", body);
                setPreview(null);
                setBody(null);
                setNotice(
                  uiText("Đã nhập gói ở trạng thái tắt. Xem nội dung trước khi bật."),
                );
                await onSaved();
              } catch (e) {
                setError(e.message);
              } finally {
                setBusy(false);
              }
            },
          },
          uiText("Nhập gói đã xem"),
        ),
      ),
  );
}
