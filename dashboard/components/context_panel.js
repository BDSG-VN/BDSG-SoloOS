import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useState, useCallback } from "react";
import { useUnsaved } from "./use_unsaved.js";
const h = React.createElement;
export default function ContextPanel({
  session,
  api,
  post,
  onSave,
  onDirtyChange,
}) {
  const [summary, setSummary] = useState(session.context_summary || ""),
    [limit, setLimit] = useState(session.context_characters || 48000),
    [stats, setStats] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [baseline, setBaseline] = useState(
    JSON.stringify([
      session.context_summary || "",
      session.context_characters || 48000,
    ]),
  );
  const reportDirty = useCallback(
    (dirty) => onDirtyChange?.(session.id, dirty),
    [onDirtyChange, session.id],
  );
  useUnsaved(JSON.stringify([summary, limit]) !== baseline, reportDirty);
  async function run(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return h(
    "details",
    { className: "context-panel" },
    h("summary", null, uiText("Bối cảnh & tóm tắt")),
    h(
      "p",
      { className: "muted" },
      uiText("Giới hạn phần lịch sử gửi vào mỗi lượt AI; toàn bộ cuộc trò chuyện gốc vẫn được giữ. Tóm tắt AI cần bạn kiểm tra trước khi lưu."),
    ),
    error && h("p", { role: "alert" }, error),
    notice && h("p", { role: "status" }, notice),
    h(
      "fieldset",
      { disabled: busy },
      h(
        "label",
        null,
        uiText("Giới hạn lịch sử (ký tự, không phải token)"),
        h("input", {
          type: "number",
          min: 4000,
          max: 120000,
          value: limit,
          onChange: (e) => setLimit(Number(e.target.value)),
        }),
      ),
      h(
        "label",
        null,
        uiText("Tóm tắt đã kiểm tra"),
        h("textarea", {
          rows: 5,
          maxLength: 12000,
          value: summary,
          onChange: (e) => setSummary(e.target.value),
        }),
      ),
      h(
        "div",
        { className: "button-row" },
        h(
          "button",
          {
            onClick: () =>
              run(async () =>
                setStats(
                  await api(`/workspace/sessions/${session.id}/context`),
                ),
              ),
          },
          uiText("Kiểm tra bối cảnh"),
        ),
        h(
          "button",
          {
            onClick: () => {
              if (
                summary &&
                !window.confirm(
                  uiText("Thay nội dung tóm tắt đang sửa bằng đề xuất AI mới?"),
                )
              )
                return;
              run(async () => {
                const result = await post(
                  `/workspace/sessions/${session.id}/summary-proposal`,
                  {},
                );
                setSummary(result.proposal);
                setNotice(
                  uiText("Đề xuất chưa lưu. Đọc lại và bấm Lưu bối cảnh nếu đồng ý."),
                );
              });
            },
          },
          uiText("AI đề xuất tóm tắt"),
        ),
        h(
          "button",
          {
            onClick: () =>
              run(async () => {
                await onSave({
                  context_summary: summary,
                  context_characters: limit,
                });
                setBaseline(JSON.stringify([summary, limit]));
                setNotice(uiText("Đã lưu bối cảnh. Lịch sử gốc được giữ nguyên."));
              }),
          },
          uiText("Lưu bối cảnh"),
        ),
      ),
    ),
    stats &&
      h(
        "p",
        { role: "status" },
        uiText("{0} ký tự từ {1}/{2} tin gần đây; {3} tin trong mẫu nằm ngoài giới hạn.", [stats.characters, stats.messages.length, stats.sampled, stats.omitted]),
      ),
  );
}
