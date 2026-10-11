import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  LayoutDashboard,
  Bot,
  BookOpen,
  CheckSquare,
  Plug,
  ShieldCheck,
  ArrowUpRight,
  LogOut,
  Plus,
  ArrowUp,
  Terminal,
  Menu,
  X,
  Activity,
} from "lucide-react";
import Devices from "./components/devices.js";
import Workboard from "./components/workboard.js";
import Navigation from "./components/navigation.js";
import Operations from "./components/operations.js";
import OpenUIRender, { soloUIPrompt } from "./components/openui_render.js";
import SharedChat from "./components/shared_chat.js";
import Voice from "./components/voice.js";
import Library from "./components/library.js";
import Automation from "./components/automation.js";
import Sessions from "./components/sessions.js";
import Profile from "./components/profile.js";
import AIAccounts, { accountLanding } from "./components/ai_accounts.js";
import CMSWorkspace from "./components/cms_workspace.js";
import BusinessWorkspace from "./components/business_workspace.js";
import KnowledgeGraph from "./components/knowledge_graph.js";
import { messages } from "./i18n/index.js";
import "./style.css";

const h = React.createElement;
let csrf = "";
async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
      ...options.headers,
    },
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.detail || `API error ${response.status}`);
  return data;
}
const post = (path, data, method = "POST") =>
  api(path, { method, body: JSON.stringify(data) });
const ICONS = {
  overview: LayoutDashboard,
  operations: Activity,
  devices: Plug,
  business: LayoutDashboard,
  cms: BookOpen,
  chat: Bot,
  accounts: Plug,
  sessions: BookOpen,
  automation: CheckSquare,
  library: BookOpen,
  brain: BookOpen,
  tasks: CheckSquare,
  mcp: Plug,
  approvals: ShieldCheck,
};
const PERMISSIONS = {
  read_only: "Chỉ đọc",
  requires_confirmation: "Cần phê duyệt",
  full_access: "Toàn quyền",
};

function Login({ onLogin }) {
  const [installed, setInstalled] = useState(null),
    [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [recovery, setRecovery] = useState(false);
  useEffect(() => {
    api("/setup")
      .then((s) => setInstalled(s.installed))
      .catch((e) => setError(e.message));
  }, []);
  const [token, setToken] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return h(
    "main",
    { className: "login-shell" },
    h(
      "div",
      { className: "login-story" },
      h("span", { className: "eyebrow" }, "BDSG FOUNDATION / OPEN SOURCE"),
      h(
        "h1",
        null,
        "Một người.",
        h("br"),
        "Cả một",
        h("br"),
        h("em", null, "doanh nghiệp."),
      ),
      h(
        "p",
        null,
        "Không gian làm việc dành cho người tự xây dựng con đường của mình. Thuê trí tuệ, sở hữu bộ não.",
      ),
      h(
        "div",
        { className: "login-foot" },
        "BDSG SoloOS",
        h("span", null, "MIT LICENSE · v0.5"),
      ),
    ),
    h(
      "form",
      {
        className: "login-card",
        onSubmit: async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            if (installed === false && !recovery)
              await post("/setup", { token, username, password });
            await post(
              "/session",
              recovery ? { token } : { username, password },
            );
            setPassword("");
            setToken("");
            await onLogin();
          } catch (err) {
            setError(err.message);
          } finally {
            setBusy(false);
          }
        },
      },
      h("span", { className: "brand-mark" }, "S"),
      h(
        "h2",
        null,
        installed === false ? "Cài đặt quản trị viên" : "Đăng nhập quản trị",
      ),
      h(
        "p",
        { className: "muted" },
        "Đăng nhập vào hệ điều hành riêng của bạn.",
      ),
      !recovery &&
        h(
          "label",
          null,
          "Tên quản trị viên",
          h("input", {
            value: username,
            onChange: (e) => setUsername(e.target.value),
            required: true,
            autoComplete: "username",
            minLength: 3,
            maxLength: 100,
          }),
        ),
      !recovery &&
        h(
          "label",
          null,
          "Mật khẩu quản trị",
          h("input", {
            type: "password",
            value: password,
            onChange: (e) => setPassword(e.target.value),
            required: true,
            minLength: 12,
            maxLength: 128,
            autoComplete: installed ? "current-password" : "new-password",
          }),
        ),
      (installed === false || recovery) &&
        h(
          "label",
          null,
          "Khóa chủ doanh nghiệp",
          h("input", {
            type: "password",
            autoComplete: "current-password",
            value: token,
            onChange: (e) => setToken(e.target.value),
            required: true,
            placeholder: "Nhập BDSG_OWNER_TOKEN",
          }),
        ),
      h(
        "label",
        null,
        h("input", {
          type: "checkbox",
          checked: recovery,
          onChange: (e) => setRecovery(e.target.checked),
        }),
        " Dùng khóa máy chủ",
      ),
      error && h("p", { className: "error", role: "alert" }, error),
      h(
        "button",
        { className: "primary", disabled: busy || installed === null },
        busy ? "Đang kết nối…" : "Mở không gian làm việc",
        h(ArrowUpRight, { size: 18 }),
      ),
      h(
        "small",
        { className: "muted" },
        "Dữ liệu được lưu trên máy chủ của bạn. Khóa được đổi thành phiên đăng nhập bảo mật.",
      ),
    ),
  );
}

function App() {
  const [authenticated, setAuthenticated] = useState(false),
    [loading, setLoading] = useState(true);
  const [page, setPageValue] = useState(
      accountLanding ? "accounts" : "overview",
    ),
    [lang, setLang] = useState("vi");
  const [navOpen, setNavOpen] = useState(false);
  const revealNav = useCallback(() => setNavOpen(true), []);
  useEffect(() => {
    const close = (e) => {
      if (e.key === "Escape") setNavOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  const [cmsDirty, setCMSDirty] = useState(false);
  const setPage = (next) => {
    if (
      next === page ||
      !cmsDirty ||
      window.confirm("Bản nội dung chưa lưu. Rời khu biên tập?")
    ) {
      setPageValue(next);
      setNavOpen(false);
      return true;
    }
    return false;
  };
  const [notes, setNotes] = useState([]),
    [tasks, setTasks] = useState([]),
    [connectors, setConnectors] = useState([]),
    [approvals, setApprovals] = useState([]);
  const [conversation, setConversation] = useState("default");
  const [history, setHistory] = useState([]),
    [engine, setEngine] = useState({}),
    [model, setModel] = useState("solo-default");
  const [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [message, setMessage] = useState(""),
    [stream, setStream] = useState(null),
    [chatBusy, setChatBusy] = useState(false);
  const [notePath, setNotePath] = useState("memory/FACTS.md"),
    [noteContent, setNoteContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [connectorDraft, setConnectorDraft] = useState(
    JSON.stringify(
      {
        id: "my-service",
        transport: "streamable_http",
        url: "https://your-mcp-server.example/mcp",
        permission: "read_only",
        tools: {},
        enabled: true,
      },
      null,
      2,
    ),
  );
  const labels = {...messages[lang], profile: "Tài khoản của tôi"};
  const [ownerProfile, setOwnerProfile] = useState(null);
  useEffect(() => { if(authenticated) api("/profile").then(setOwnerProfile).catch(() => {}); }, [authenticated]);

  const refresh = useCallback(async () => {
    const [ns, ts, cs, aps, hs, es] = await Promise.all([
      api("/brain"),
      api("/tasks"),
      api("/mcp/connectors"),
      api("/confirmations"),
      api(`/conversations/${conversation}`),
      api("/engines"),
    ]);
    setNotes(ns);
    setTasks(ts);
    setConnectors(cs);
    setApprovals(aps);
    setHistory(hs);
    setEngine(es);
    setModel((current) => (current === "solo-default" ? es.model : current));
  }, [conversation]);
  const initialize = useCallback(async () => {
    const session = await api("/session");
    csrf = session.csrf;
    setAuthenticated(true);
    await refresh();
  }, [refresh]);
  useEffect(() => {
    initialize()
      .catch((err) => {
        if (!err.message.includes("Authentication")) setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [initialize]);
  async function act(action) {
    setError("");
    setNotice("");
    setSaving(true);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }
  function launchChat(demo = false) {
    if (chatBusy || (!demo && !message.trim())) return;
    setPage("chat");
    setChatBusy(true);
    setError("");
    setStream({
      key: Date.now(),
      url: demo ? "/api/demo/stream" : "/api/chat",
      request: demo
        ? {}
        : {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRF-Token": csrf,
            },
            body: JSON.stringify({
              message,
              model,
              conversation,
              ui_prompt: soloUIPrompt,
            }),
          },
      demo,
    });
    if (!demo) {
      setHistory((items) => [
        ...items,
        { id: Date.now(), role: "user", content: message },
      ]);
      setMessage("");
    }
  }
  if (loading) return h("main", { className: "loading" }, "Đang mở Solo-OS…");
  if (!authenticated) return h(Login, { onLogin: initialize });

  const completion = tasks.length
    ? Math.round(
        (tasks.filter((t) => t.state === "done").length / tasks.length) * 100,
      )
    : 0;
  let content;
  if (page === "overview")
    content = h(
      "div",
      { className: "overview" },
      h(
        "section",
        { className: "welcome-panel" },
        h(
          "div",
          null,
          h("span", { className: "eyebrow" }, "YOUR BUSINESS, YOUR BRAIN"),
          h("h2", null, "Bớt phân tán.", h("br"), "Thêm tập trung."),
          h(
            "p",
            null,
            "Một nơi để suy nghĩ, ghi nhớ và hoàn thành công việc. Bạn luôn quyết định quyền của AI.",
          ),
          h(
            "button",
            { onClick: () => setPage("chat"), className: "primary" },
            "Làm việc cùng AI",
            h(ArrowUpRight, { size: 18 }),
          ),
        ),
        h(
          "div",
          { className: "orb", "aria-hidden": true },
          h("span", null, "S"),
        ),
      ),
      h(
        "div",
        { className: "metrics" },
        ...[
          [
            "Kiến thức đã lưu",
            notes.length,
            "Markdown · thuộc sở hữu của bạn",
            BookOpen,
          ],
          [
            "Công việc đang mở",
            tasks.filter((t) => t.state !== "done").length,
            `${completion}% công việc hoàn thành`,
            CheckSquare,
          ],
          [
            "Kết nối công cụ",
            connectors.filter((c) => c.enabled).length,
            "Một Hub cho mọi mô hình",
            Plug,
          ],
          [
            "Đang chờ bạn duyệt",
            approvals.length,
            "Quyền kiểm soát tại tầng hệ thống",
            ShieldCheck,
          ],
        ].map(([label, value, caption, Icon]) =>
          h(
            "article",
            { className: "metric", key: label },
            h("div", null, h("span", null, label), h(Icon, { size: 18 })),
            h("strong", null, value),
            h("small", null, caption),
          ),
        ),
      ),
      h(
        "div",
        { className: "two-col" },
        h(
          "section",
          { className: "panel" },
          h(
            "div",
            { className: "section-title" },
            h("h3", null, "Tiếp tục công việc"),
            h(
              "button",
              { className: "text-button", onClick: () => setPage("tasks") },
              "Xem bảng việc →",
            ),
          ),
          tasks.length
            ? tasks
                .slice(0, 4)
                .map((task) =>
                  h(
                    "div",
                    { className: "task-row", key: task.id },
                    h(CheckSquare, { size: 16 }),
                    h("span", null, task.title),
                    h(
                      "span",
                      { className: "badge" },
                      { todo: "Cần làm", doing: "Đang làm", done: "Hoàn tất" }[
                        task.state
                      ],
                    ),
                  ),
                )
            : h(
                "div",
                { className: "empty" },
                h(CheckSquare, { size: 26 }),
                h("p", null, "Khoảng trống cho ý tưởng tiếp theo."),
                h(
                  "button",
                  { onClick: () => setPage("tasks") },
                  "Tạo công việc đầu tiên",
                ),
              ),
        ),
        h(
          "section",
          { className: "panel accent-panel" },
          h("span", { className: "eyebrow" }, "GENERATIVE UI"),
          h("h3", null, "Không chỉ là câu trả lời."),
          h(
            "p",
            null,
            "Biểu đồ và biểu mẫu xuất hiện ngay khi AI đang trả lời, qua OpenUI Lang.",
          ),
          h(
            "button",
            { onClick: () => launchChat(true), disabled: chatBusy },
            "Thử luồng giao diện mẫu",
            h(ArrowUpRight, { size: 16 }),
          ),
          h("small", null, "Dữ liệu minh họa · không cần khóa LLM"),
        ),
      ),
    );

  if (page === "library")
    content = h(Library, { api, post, onDirtyChange: setCMSDirty });
  if (page === "devices") content = h(Devices, { api, post });
  if (page === "operations")
    content = h(Operations, { api, post, onNavigate: setPage });
  if (page === "automation")
    content = h(Automation, { api, post, onDirtyChange: setCMSDirty });
  if (page === "sessions")
    content = h(Sessions, {
      api,
      post,
      onDirtyChange: setCMSDirty,
      onOpen: (s) => {
        if (chatBusy || !setPage("chat")) return;
        setConversation(s.id);
        setModel(s.model);
        setStream(null);
      },
    });
  if (page === "profile") content = h(Profile, {api, post, onUpdate: setOwnerProfile, onDirtyChange: setCMSDirty, onLogout: () => {csrf = ""; setCMSDirty(false); setAuthenticated(false);}});
  if (page === "accounts")
    content = h(AIAccounts, {
      api,
      post,
      onChange: async () => {
        setModel("solo-default");
        await refresh();
      },
    });
  if (page === "cms")
    content = h(CMSWorkspace, {
      api,
      post,
      onDirtyChange: setCMSDirty,
      streamRequest: (body, signal) =>
        fetch("/api/cms/generate", {
          method: "POST",
          credentials: "include",
          signal,
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
          body: JSON.stringify(body),
        }),
    });
  if (page === "business")
    content = h(BusinessWorkspace, {
      api,
      post,
      onPending: refresh,
      onConfigure: (template) => {
        setConnectorDraft(JSON.stringify(template, null, 2));
        setPage("mcp");
      },
      onAskAI: (prompt) => {
        setMessage(prompt);
        setPage("chat");
      },
    });
  if (page === "chat")
    content = h(
      "div",
      { className: "chat-layout panel" },
      h(
        "button",
        { onClick: () => setPage("accounts"), disabled: chatBusy },
        "Quản lý tài khoản AI",
      ),
      h(
        "div",
        { className: "chat-toolbar" },
        h(
          "span",
          { className: "badge" },
          engine.configured ? "Đã kết nối nguồn AI" : "Chưa kết nối nguồn AI",
        ),
        h(
          "label",
          null,
          "Model",
          h("input", {
            value: model,
            onChange: (e) => setModel(e.target.value),
            "aria-label": "Model alias",
            disabled: chatBusy,
          }),
        ),
        h(
          "button",
          {
            className: "text-button",
            onClick: () => launchChat(true),
            disabled: chatBusy,
          },
          "Thử bản mẫu",
        ),
        chatBusy &&
          h(
            "button",
            {
              onClick: () => {
                setStream(null);
                setChatBusy(false);
              },
            },
            "Dừng luồng",
          ),
      ),
      h(
        "div",
        { className: "chat-messages" },
        !history.length &&
          !stream &&
          h(
            "div",
            { className: "empty chat-empty" },
            h(Bot, { size: 32 }),
            h("h2", null, "Hôm nay bạn muốn xây dựng điều gì?"),
            h(
              "p",
              null,
              "Lập kế hoạch, đọc bộ nhớ hoặc yêu cầu AI kết xuất biểu đồ. Mọi công cụ đều đi qua MCP Hub.",
            ),
          ),
        ...history.map((entry) =>
          h(
            "article",
            { key: entry.id, className: `chat-message ${entry.role}` },
            h("small", null, entry.role === "user" ? "BẠN" : "SOLO-OS"),
            entry.role === "user"
              ? h("p", null, entry.content)
              : h(OpenUIRender, { response: entry.content }),
          ),
        ),
        stream &&
          h(
            "article",
            { className: "chat-message assistant" },
            h(
              "small",
              null,
              stream.demo ? "LUỒNG MẪU · DỮ LIỆU MINH HỌA" : "SOLO-OS",
            ),
            h(OpenUIRender, {
              key: stream.key,
              url: stream.url,
              request: stream.request,
              onConfirmation: () => {
                setNotice(
                  "AI đang chờ phê duyệt. Mở mục Phê duyệt để xem tham số.",
                );
                refresh().catch((err) => setError(err.message));
              },
              onComplete: () => {
                setChatBusy(false);
                if (!stream.demo) {
                  setStream(null);
                  refresh().catch((err) => setError(err.message));
                }
              },
              onError: (err) => {
                setChatBusy(false);
                if (err instanceof Error) setError(err.message);
              },
              onAction: (event) => {
                // This registered demo form has one explicit, owner-initiated action.
                const fields = event.formState?.business || event.formState;
                const goal = fields?.goal?.value ?? fields?.goal;
                if (
                  event.formName === "business" &&
                  typeof goal === "string" &&
                  goal.trim()
                ) {
                  act(async () => {
                    await post("/tasks", { title: goal });
                    setNotice("Đã thêm mục tiêu vào bảng công việc.");
                  });
                } else
                  setNotice(
                    "Đã nhận nội dung biểu mẫu. Chưa gắn hành động cho biểu mẫu này.",
                  );
              },
            }),
          ),
      ),
      h(Voice, {
        disabled: chatBusy,
        onTranscript: (text) =>
          setMessage((current) =>
            (current + " " + text).trim().slice(0, 12000),
          ),
      }),
      h(
        "form",
        {
          className: "composer",
          onSubmit: (e) => {
            e.preventDefault();
            launchChat();
          },
        },
        h("textarea", {
          value: message,
          onChange: (e) => setMessage(e.target.value),
          placeholder: "Nhờ AI lập kế hoạch cho doanh nghiệp của bạn…",
          rows: 2,
          disabled: chatBusy,
          "aria-label": "Tin nhắn cho AI",
        }),
        h(
          "div",
          null,
          h("small", null, "Công cụ thực thi qua MCP Hub · quyền do bạn cấp"),
          h(
            "button",
            {
              className: "primary icon-button",
              disabled: chatBusy || !message.trim(),
              "aria-label": "Gửi tin nhắn",
            },
            h(ArrowUp, { size: 20 }),
          ),
        ),
      ),
    );

  if (page === "brain")
    content = h(
      "div",
      { className: "two-col brain-layout" },
      h(
        "section",
        { className: "panel" },
        h(
          "div",
          { className: "section-title" },
          h("h3", null, "Second Brain"),
          h("span", { className: "badge" }, `${notes.length} ghi chú`),
        ),
        ...notes.map((note) =>
          h(
            "button",
            {
              key: note.path,
              className: `note-item ${note.path === notePath ? "selected" : ""}`,
              onClick: () => {
                setNotePath(note.path);
                setNoteContent(note.content);
              },
            },
            h(BookOpen, { size: 18 }),
            h(
              "span",
              null,
              note.path,
              h("small", null, note.content.slice(0, 70)),
            ),
          ),
        ),
        h(KnowledgeGraph, { notes }),
      ),
      h(
        "form",
        {
          className: "panel note-editor",
          onSubmit: (e) => {
            e.preventDefault();
            act(async () => {
              const result = await post("/brain", {
                path: notePath,
                content: noteContent,
              });
              setNotice(
                result.status === "requires_confirmation"
                  ? "Đã gửi ghi chú để phê duyệt. Mở mục Phê duyệt để lưu."
                  : "Đã lưu ghi chú.",
              );
            });
          },
        },
        h("h3", null, "Ghi chú thuộc về bạn"),
        h(
          "label",
          null,
          "Đường dẫn Markdown",
          h("input", {
            value: notePath,
            onChange: (e) => setNotePath(e.target.value),
            required: true,
          }),
        ),
        h(
          "label",
          null,
          "Nội dung",
          h("textarea", {
            rows: 16,
            value: noteContent,
            onChange: (e) => setNoteContent(e.target.value),
            placeholder:
              "# Kiến thức doanh nghiệp\n\nLiên kết bằng [[tên ghi chú]].",
          }),
        ),
        h(
          "button",
          { className: "primary", disabled: saving },
          "Lưu qua MCP Hub",
          h(ShieldCheck, { size: 16 }),
        ),
      ),
    );

  if (page === "tasks")
    content = h(Workboard, {
      api,
      post,
      onDirtyChange: setCMSDirty,
      onSaved: refresh,
    });

  if (page === "mcp")
    content = h(
      "div",
      { className: "two-col" },
      h(
        "section",
        { className: "panel" },
        h("h3", null, "Công cụ của doanh nghiệp"),
        ...connectors.map((connector) =>
          h(
            "article",
            { className: "connector-card", key: connector.id },
            h(
              "div",
              { className: "section-title" },
              h("h4", null, connector.id),
              h("span", { className: "badge" }, connector.transport),
            ),
            h(
              "p",
              null,
              h(ShieldCheck, { size: 14 }),
              " ",
              PERMISSIONS[connector.permission],
            ),
            h(
              "small",
              { className: "muted" },
              Object.keys(connector.tools).join(" · ") || "Chưa cấp công cụ",
            ),
            h(
              "button",
              {
                className: "text-button",
                onClick: () => {
                  const { revision, ...editable } = connector;
                  setConnectorDraft(JSON.stringify(editable, null, 2));
                },
              },
              "Chỉnh sửa quyền →",
            ),
          ),
        ),
      ),
      h(
        "form",
        {
          className: "panel",
          onSubmit: (e) => {
            e.preventDefault();
            act(async () => {
              await post("/mcp/connectors", JSON.parse(connectorDraft), "PUT");
              setNotice(
                "Đã cập nhật cấu hình MCP. Các phê duyệt cũ sẽ không còn hiệu lực.",
              );
            });
          },
        },
        h("h3", null, "Cấu hình kết nối"),
        h(
          "p",
          { className: "muted" },
          "Cấp quyền từng công cụ. tools: { tên: true } xác nhận công cụ chỉ đọc; false dành cho công cụ có thể ghi.",
        ),
        h("textarea", {
          className: "code",
          rows: 17,
          value: connectorDraft,
          "aria-label": "Cấu hình MCP JSON",
          onChange: (e) => setConnectorDraft(e.target.value),
        }),
        h("button", { className: "primary", disabled: saving }, "Lưu cấu hình"),
      ),
    );

  if (page === "approvals")
    content = h(
      "section",
      { className: "panel" },
      h(
        "div",
        { className: "section-title" },
        h("h3", null, "Bạn giữ quyền quyết định"),
        h(
          "button",
          {
            className: "text-button",
            onClick: () => act(refresh),
            disabled: saving,
          },
          "Làm mới",
        ),
      ),
      h(
        "p",
        { className: "muted" },
        "Mỗi phê duyệt chỉ dùng một lần, gắn với đúng công cụ và tham số. Hết hạn sau 5 phút.",
      ),
      ...approvals.map((approval) =>
        h(
          "article",
          { className: "approval-card", key: approval.id },
          h(
            "div",
            { className: "section-title" },
            h(
              "h4",
              null,
              `${approval.payload.connector} / ${approval.payload.tool}`,
            ),
            h(
              "span",
              { className: "badge" },
              approval.payload.actor === "agent" ? "AI yêu cầu" : "Bạn yêu cầu",
            ),
          ),
          h("pre", null, JSON.stringify(approval.payload.arguments, null, 2)),
          h(
            "small",
            { className: "muted" },
            `Hết hạn: ${new Date(approval.expires * 1000).toLocaleTimeString("vi-VN")}`,
          ),
          h(
            "div",
            { className: "button-row" },
            h(
              "button",
              {
                className: "primary",
                disabled: saving,
                onClick: () =>
                  act(async () => {
                    const result = await post(
                      `/confirmations/${approval.id}/decision`,
                      { approved: true },
                    );
                    setNotice(
                      result.status === "completed"
                        ? "Đã duyệt và thực thi."
                        : "Công cụ báo lỗi; xem kết quả trước khi thử lại.",
                    );
                  }),
              },
              "Duyệt và thực thi",
            ),
            h(
              "button",
              {
                disabled: saving,
                onClick: () =>
                  act(() =>
                    post(`/confirmations/${approval.id}/decision`, {
                      approved: false,
                    }),
                  ),
              },
              "Từ chối",
            ),
          ),
        ),
      ),
      !approvals.length &&
        h(
          "div",
          { className: "empty" },
          h(ShieldCheck, { size: 32 }),
          h("p", null, "Không có hành động nào đang chờ duyệt."),
        ),
    );

  return h(
    "div",
    { className: "app-shell" },
    h(
      "aside",
      {
        className: `sidebar ${navOpen ? "is-open" : ""}`,
        id: "workspace-navigation",
      },
      h(
        "a",
        {
          className: "brand",
          href: "/",
          onClick: (e) => {
            e.preventDefault();
            if (!chatBusy) setPage("overview");
          },
        },
        h("span", { className: "brand-mark" }, "S"),
        h("div", null, "SoloOS", h("small", null, "BDSG FOUNDATION")),
      ),
      h(
        "button",
        {
          className: "nav-close",
          onClick: () => setNavOpen(false),
          "aria-label": "Đóng menu",
        },
        h(X, { size: 20 }),
      ),
      h(Navigation, {
        labels,
        icons: ICONS,
        page,
        onNavigate: setPage,
        disabled: chatBusy,
        approvals: approvals.length,
        lang,
        onReveal: revealNav,
      }),
      h(
        "div",
        { className: "sidebar-bottom" },
        h(
          "div",
          { className: "ownership" },
          h(ShieldCheck, { size: 20 }),
          h(
            "div",
            null,
            "Bạn sở hữu bộ não.",
            h("small", null, "Markdown + SQLite trên máy chủ riêng"),
          ),
        ),
        h("button", {className: "profile", disabled: chatBusy, onClick: () => setPage("profile"), "aria-label": "Tài khoản của tôi"},
          h("span", {className: "avatar"}, (ownerProfile?.display_name || "TK").slice(0,2).toUpperCase()),
          h("span", null, ownerProfile?.display_name || "Tài khoản của tôi", h("small", null, "Thông tin & mật khẩu"))),
        h(
          "button",
          {
            className: "profile",
            "aria-label": "Đăng xuất",
            disabled: chatBusy,
            onClick: async () => {
              try {
                if (
                  cmsDirty &&
                  !window.confirm("Bản nội dung chưa lưu. Đăng xuất?")
                )
                  return;
                await api("/session", { method: "DELETE" });
                csrf = "";
                setAuthenticated(false);
              } catch (err) {
                setError(err.message);
              }
            },
          },
          h("span", null, "Đăng xuất"),
          h(LogOut, { size: 16 }),
        ),
      ),
    ),
    navOpen &&
      h("button", {
        className: "nav-backdrop",
        "aria-label": "Đóng điều hướng",
        onClick: () => setNavOpen(false),
      }),
    h(
      "main",
      { className: "main" },
      h(
        "header",
        { className: "topbar" },
        h(
          "button",
          {
            className: "nav-toggle",
            "aria-label": "Mở menu",
            "aria-expanded": navOpen,
            "aria-controls": "workspace-navigation",
            onClick: () => setNavOpen(!navOpen),
          },
          h(Menu, { size: 20 }),
        ),
        h(
          "div",
          null,
          h("span", { className: "muted" }, "Không gian làm việc / "),
          labels[page],
        ),
        h(
          "div",
          { className: "topbar-right" },
          h("a", {href: "/", target: "_blank", rel: "noopener noreferrer", className: "text-button"}, "Mở website ↗"),
          h("span", { className: "status-dot" }),
          "Local-first",
          h(
            "button",
            {
              className: "text-button",
              onClick: () => setLang(lang === "vi" ? "en" : "vi"),
            },
            lang.toUpperCase(),
          ),
        ),
      ),
      h(
        "div",
        { className: "page-content" },
        h(
          "div",
          { className: "page-heading" },
          h(
            "div",
            null,
            h("span", { className: "eyebrow" }, "BDSG SOLO-OS / 01"),
            h("h1", null, labels[page]),
          ),
          h(
            "span",
            { className: "date" },
            new Date().toLocaleDateString("vi-VN", {
              weekday: "long",
              day: "numeric",
              month: "long",
            }),
          ),
        ),
        error && h("p", { className: "error", role: "alert" }, error),
        notice && h("p", { className: "notice", role: "status" }, notice),
        content,
      ),
      h(
        "footer",
        null,
        "BDSG Foundation · MIT · v0.5",
        h("span", null, "RENT THE MODEL. OWN THE BRAIN."),
      ),
    ),
  );
}

createRoot(document.getElementById("root")).render(
  h(location.pathname.startsWith("/share/") ? SharedChat : App),
);

if ("serviceWorker" in navigator && location.protocol === "https:") {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
