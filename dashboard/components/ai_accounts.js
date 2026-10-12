import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useEffect, useState } from "react";
const h = React.createElement;
// Keep authorization codes in memory only; remove them before any subsequent navigation.
const fragment = new URLSearchParams(window.location.hash.slice(1));
let callback = fragment.get("chatgpt-callback");
export const accountLanding = Boolean(
  callback || fragment.has("connect-chatgpt"),
);
if (accountLanding)
  history.replaceState(
    null,
    "",
    window.location.pathname + window.location.search,
  );
export default function AIAccounts({ api, post, onChange }) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false),
    [models, setModels] = useState([]),
    [model, setModel] = useState("");
  async function reload() {
    const next = await api("/ai/accounts");
    setData(next);
    setModel(next.selected_model || "");
  }
  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
      await reload();
      await onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    if (callback) {
      const value = callback;
      callback = null;
      run(async () => {
        await post("/ai/chatgpt/finish", { callback_url: value });
        setNotice(uiText("Đã kết nối ChatGPT. Chọn model để bắt đầu."));
      });
    } else reload().catch((err) => setError(err.message));
  }, []);
  useEffect(() => {
    let cancelled = false;
    setModels([]);
    if (
      data?.active_account &&
      !["gateway", "claude-native"].includes(data.active_account)
    )
      api(`/ai/accounts/${data.active_account}/models`)
        .then((value) => {
          if (!cancelled) setModels(value);
        })
        .catch((err) => {
          if (!cancelled) setError(err.message);
        });
    return () => {
      cancelled = true;
    };
  }, [data?.active_account]);
  async function login(account_id = null) {
    await run(async () => {
      const result = await post("/ai/chatgpt/start", { account_id });
      window.location.assign(result.authorization_url);
    });
  }
  return h(
    "section",
    { className: "panel workspace-panel", style: { padding: "24px" } },
    h("h2", null, uiText("Tài khoản AI")),
    h(
      "p",
      null,
      uiText("Kết nối tài khoản ChatGPT bằng quyền do chính bạn cấp. Khả năng sử dụng phụ thuộc gói thuê bao và hạn mức được nhà cung cấp cho phép."),
    ),
    error && h("p", { role: "alert", className: "error" }, error),
    notice && h("p", { role: "status" }, notice),
    h("h3", null, uiText("Đăng nhập ChatGPT trên máy của bạn")),
    h(
      "p",
      null,
      uiText("Tải trình hỗ trợ, mở Terminal tại thư mục tải xuống và chạy lệnh dưới đây. Trình hỗ trợ mở trang quản trị; sau đó bấm Continue with ChatGPT. Giữ Terminal mở cho đến khi hoàn tất đăng nhập."),
    ),
    h(
      "a",
      { href: "/api/ai/chatgpt/helper", download: true },
      uiText("Tải soloos-chatgpt-login.py"),
    ),
    h(
      "pre",
      { style: { overflowX: "auto" } },
      `python3 soloos-chatgpt-login.py --site ${window.location.origin}`,
    ),
    h(
      "button",
      { disabled: busy, onClick: () => login() },
      "Continue with ChatGPT",
    ),
    h("h3", null, uiText("Nguồn AI đang sử dụng")),
    data &&
      h(
        "select",
        {
          "aria-label": uiText("Nguồn AI"),
          disabled: busy,
          value: data.active_account,
          onChange: (e) =>
            run(() => post("/ai/select", { account_id: e.target.value })),
        },
        h(
          "option",
          { value: "gateway" },
          `LLM Gateway${data.gateway_configured ? "" : uiText(" — chưa cấu hình")}`,
        ),
        h(
          "option",
          { value: "claude-native" },
          uiText("Claude Code — đăng nhập qua CLI chính thức"),
        ),
        ...data.accounts
          .filter((a) => a.connected)
          .map((a) =>
            h(
              "option",
              { key: a.id, value: a.id },
              `${a.label} · ${a.id.slice(0, 6)}`,
            ),
          ),
      ),
    models.length > 0 &&
      h(
        "div",
        null,
        h(
          "select",
          {
            "aria-label": "Model ChatGPT",
            value: model,
            onChange: (e) => setModel(e.target.value),
          },
          h("option", { value: "" }, uiText("Tự chọn model khả dụng")),
          ...models.map((m) => h("option", { key: m.id, value: m.id }, m.name)),
        ),
        h(
          "button",
          {
            disabled: busy,
            onClick: () =>
              run(() =>
                post("/ai/select", { account_id: data.active_account, model }),
              ),
          },
          uiText("Lưu model"),
        ),
      ),
    ...(data?.accounts || []).map((a) =>
      h(
        "div",
        { key: a.id, style: { marginTop: 16 } },
        h(
          "strong",
          null,
          `${a.label} · ${a.connected ? uiText("Đã kết nối") : uiText("Đã ngắt")}`,
        ),
        h(
          "button",
          { disabled: busy, onClick: () => login(a.id) },
          uiText("Đăng nhập lại"),
        ),
        a.connected &&
          h(
            "button",
            {
              disabled: busy,
              onClick: () =>
                run(async () => {
                  const result = await post(
                    `/ai/accounts/${a.id}/disconnect`,
                    {},
                  );
                  setNotice(
                    result.remote_revocation_confirmed
                      ? uiText("Đã thu hồi kết nối.")
                      : uiText("Đã xóa thông tin đăng nhập trên SoloOS. Chưa xác nhận thu hồi phía ChatGPT; hãy kiểm tra các ứng dụng được cấp quyền trong cài đặt ChatGPT."),
                  );
                }),
            },
            uiText("Ngắt kết nối"),
          ),
      ),
    ),
    h(
      "button",
      {
        disabled: busy,
        onClick: () =>
          run(async () => {
            const s = await api("/ai/claude/status");
            setNotice(
              s.connected
                ? uiText("Claude Code đã đăng nhập.")
                : s.message || uiText("Claude Code chưa đăng nhập."),
            );
          }),
      },
      uiText("Kiểm tra Claude Code"),
    ),
    h("h3", null, uiText("Sử dụng ChatGPT trong 30 ngày")),
    ...(data?.usage || []).map((u, i) =>
      h(
        "p",
        { key: i },
        uiText("{0} · {1} · {2} lượt · {3} · token vào/ra: {4}/{5}", [u.model, u.source, u.requests, u.status, u.input_tokens ?? "—", u.output_tokens ?? "—"]),
      ),
    ),
    h(
      "p",
      null,
      uiText("Claude: dùng bản CLI chính thức do bạn cài và đăng nhập trên máy chủ; SoloOS không thu thập token Claude. Chế độ này chỉ soạn nội dung, chưa có thao tác công cụ. Các nền tảng khác dùng Gateway hoặc model tự lưu trữ."),
    ),
  );
}
