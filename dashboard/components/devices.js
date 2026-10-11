import React, { useEffect, useState } from "react";
const h = React.createElement;
export default function Devices({ api, post }) {
  const [rows, setRows] = useState([]),
    [name, setName] = useState(""),
    [scopes, setScopes] = useState(["read", "chat"]),
    [code, setCode] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const labels = {
    read: "Xem dữ liệu & vận hành",
    chat: "Trò chuyện AI",
    tasks: "Tạo/sửa công việc",
    approvals: "Duyệt thực thi công cụ",
  };
  async function reload() {
    setRows(await api("/devices"));
  }
  useEffect(() => {
    reload().catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!code) return;
    const timer = setTimeout(() => setCode(null), 300000);
    return () => clearTimeout(timer);
  }, [code]);
  async function run(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return h(
    "section",
    { className: "panel workspace-panel", style: { padding: 24 } },
    h("h2", null, "Thiết bị của bạn"),
    h(
      "p",
      null,
      "Ghép ứng dụng native bằng mã dùng một lần, hết hạn sau 5 phút. Quyền thiết bị có hạn 30 ngày và có thể thu hồi. Không cần đưa khóa chủ doanh nghiệp vào ứng dụng.",
    ),
    error && h("p", { role: "alert" }, error),
    h(
      "fieldset",
      { disabled: busy },
      h("legend", null, "Ghép thiết bị mới"),
      h(
        "label",
        null,
        "Tên thiết bị",
        h("input", {
          value: name,
          maxLength: 100,
          onChange: (e) => setName(e.target.value),
          placeholder: "Ví dụ: iPhone của tôi",
        }),
      ),
      ...Object.entries(labels).map(([key, label]) =>
        h(
          "label",
          { key },
          h("input", {
            type: "checkbox",
            checked: scopes.includes(key),
            onChange: (e) =>
              setScopes(
                e.target.checked
                  ? [...scopes, key]
                  : scopes.filter((s) => s !== key),
              ),
          }),
          " " + label,
        ),
      ),
      h(
        "button",
        {
          disabled: !name.trim() || !scopes.length,
          onClick: () =>
            run(async () => {
              const result = await post("/devices/pair", {
                name,
                scopes,
                days: 30,
              });
              setCode(result.code);
            }),
        },
        "Tạo mã ghép",
      ),
    ),
    code &&
      h(
        "div",
        { className: "pairing-code" },
        h(
          "label",
          null,
          "Mã ghép — chỉ nhập vào ứng dụng của bạn",
          h("input", {
            readOnly: true,
            value: code,
            autoComplete: "off",
            spellCheck: false,
          }),
        ),
        h("button", { onClick: () => setCode(null) }, "Ẩn mã"),
      ),
    h(
      "button",
      { disabled: busy, onClick: () => run(reload) },
      "Làm mới thiết bị",
    ),
    ...rows.map((d) =>
      h(
        "article",
        { key: d.id, className: "notification-row" },
        h(
          "div",
          null,
          h("strong", null, d.name),
          h("p", null, d.scopes.map((s) => labels[s]).join(" · ")),
          h(
            "small",
            null,
            d.revoked
              ? "Đã thu hồi"
              : "Hết hạn: " + new Date(d.expires * 1000).toLocaleString(),
          ),
        ),
        !d.revoked &&
          h(
            "button",
            {
              disabled: busy,
              onClick: () => {
                if (
                  window.confirm(
                    "Thu hồi quyền thiết bị này? Yêu cầu tiếp theo sẽ bị chặn; thao tác đã gửi có thể đã thực hiện.",
                  )
                )
                  run(() => api("/devices/" + d.id, { method: "DELETE" }));
              },
            },
            "Thu hồi thiết bị",
          ),
      ),
    ),
    !rows.length &&
      h("p", { className: "empty" }, "Chưa có thiết bị ghép nối."),
  );
}
