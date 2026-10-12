import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useEffect, useState, useRef, useCallback } from "react";
import { useUnsaved } from "./use_unsaved.js";
import ContextPanel from "./context_panel.js";
const h = React.createElement;
export default function Sessions({ api, post, onOpen, onDirtyChange }) {
  const [dirtyPanels, setDirtyPanels] = useState({});
  const dirtyPanel = useCallback(
    (id, dirty) => setDirtyPanels((previous) => ({ ...previous, [id]: dirty })),
    [],
  );
  const mayDiscard = useUnsaved(
    Object.values(dirtyPanels).some(Boolean),
    onDirtyChange,
  );
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  const [agents, setAgents] = useState([]),
    [agent, setAgent] = useState("");
  const [shares, setShares] = useState([]),
    [shareURL, setShareURL] = useState("");
  const [brains, setBrains] = useState([]),
    [brain, setBrain] = useState("default");
  const [sessions, setSessions] = useState([]),
    [projects, setProjects] = useState([]),
    [search, setSearch] = useState(""),
    [archived, setArchived] = useState(false);
  const [title, setTitle] = useState(""),
    [context, setContext] = useState(""),
    [project, setProject] = useState(""),
    [error, setError] = useState("");
  async function reload() {
    const request = ++generation.current;
    const [s, p, b, shared, automation] = await Promise.all([
      api(
        `/workspace/sessions?archived=${archived}&search=${encodeURIComponent(search)}`,
      ),
      api("/workspace/projects"),
      api("/library"),
      api("/shares"),
      api("/automation"),
    ]);
    if (request !== generation.current) return;
    setSessions(s);
    setProjects(p);
    setBrains(b);
    setShares(shared);
    setAgents(automation.agents);
  }
  useEffect(() => {
    reload().catch((e) => setError(e.message));
  }, [search, archived]);
  async function run(fn) {
    setError("");
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e.message);
    }
  }
  function update(s, patch) {
    const { id, updated, ...body } = s;
    return post(`/workspace/sessions/${id}`, { ...body, ...patch }, "PUT");
  }
  return h(
    "section",
    { className: "panel workspace-panel", style: { padding: 24 } },
    h("h2", null, uiText("Cuộc trò chuyện & dự án")),
    error && h("p", { role: "alert" }, error),
    h(
      "label",
      null,
      uiText("Tìm theo tên hoặc nội dung"),
      h("input", {
        value: search,
        onChange: (e) => {
          if (mayDiscard()) setSearch(e.target.value);
        },
      }),
    ),
    h(
      "label",
      null,
      h("input", {
        type: "checkbox",
        checked: archived,
        onChange: (e) => {
          if (mayDiscard()) setArchived(e.target.checked);
        },
      }),
      uiText(" Đã lưu trữ"),
    ),
    h(
      "div",
      null,
      h(
        "label",
        null,
        uiText("Dự án"),
        h(
          "select",
          { value: project, onChange: (e) => setProject(e.target.value) },
          h("option", { value: "" }, uiText("Không gắn dự án")),
          ...projects.map((p) =>
            h("option", { key: p.id, value: p.id }, p.title),
          ),
        ),
      ),
      h(
        "button",
        {
          onClick: () =>
            run(async () => {
              const s = await post("/workspace/sessions", {
                project_id: project || null,
                brain_id: brain,
                agent_id: agent || null,
              });
              onOpen(s);
            }),
        },
        uiText("Cuộc trò chuyện mới"),
      ),
    ),
    h(
      "label",
      null,
      uiText("Bộ nhớ cho cuộc trò chuyện mới"),
      h(
        "select",
        { value: brain, onChange: (e) => setBrain(e.target.value) },
        ...brains.map((b) => h("option", { key: b.id, value: b.id }, b.title)),
      ),
    ),
    h(
      "label",
      null,
      uiText("Trợ lý cho cuộc trò chuyện mới"),
      h(
        "select",
        { value: agent, onChange: (e) => setAgent(e.target.value) },
        h("option", { value: "" }, uiText("Trợ lý mặc định")),
        ...agents
          .filter((a) => a.enabled)
          .map((a) => h("option", { key: a.id, value: a.id }, a.title)),
      ),
    ),
    ...sessions.map((s) =>
      h(
        "article",
        {
          key: s.id,
          style: { padding: "16px 0", borderBottom: "1px solid #555" },
        },
        h("strong", null, s.title),
        h("button", { onClick: () => onOpen(s), disabled: s.archived }, uiText("Mở")),
        h(
          "button",
          { onClick: () => run(() => update(s, { pinned: !s.pinned })) },
          s.pinned ? uiText("Bỏ ghim") : uiText("Ghim"),
        ),
        h(
          "button",
          {
            onClick: () => {
              const name = window.prompt(uiText("Tên cuộc trò chuyện"), s.title);
              if (name?.trim()) run(() => update(s, { title: name.trim() }));
            },
          },
          uiText("Đổi tên"),
        ),
        h(
          "button",
          {
            onClick: () => {
              if (mayDiscard()) run(() => update(s, { archived: !s.archived }));
            },
          },
          s.archived ? uiText("Khôi phục") : uiText("Lưu trữ"),
        ),
        h(ContextPanel, {
          session: s,
          onDirtyChange: dirtyPanel,
          api,
          post,
          onSave: async (patch) => {
            await update(s, patch);
            await reload();
          },
        }),
        h(
          "a",
          { href: `/api/workspace/sessions/${s.id}/export`, download: true },
          uiText("Xuất JSON"),
        ),
        h(
          "button",
          {
            onClick: () => {
              if (
                window.confirm(
                  uiText("Tạo liên kết đọc toàn bộ nội dung cuộc trò chuyện trong 7 ngày? Bất kỳ ai có liên kết đều đọc được bản chụp này. Hãy kiểm tra thông tin riêng tư trước khi chia sẻ."),
                )
              )
                run(async () => {
                  const shared = await post("/shares", {
                    conversation: s.id,
                    days: 7,
                  });
                  setShareURL(shared.url);
                });
            },
          },
          uiText("Tạo liên kết chia sẻ"),
        ),
      ),
    ),
    shareURL &&
      h(
        "p",
        null,
        uiText("Liên kết mới: "),
        h(
          "a",
          { href: shareURL, target: "_blank", rel: "noreferrer" },
          location.origin + shareURL,
        ),
      ),
    h("h3", null, uiText("Liên kết đã tạo")),
    ...shares.map((s) =>
      h(
        "p",
        { key: s.id },
        `${s.title} · ${s.revoked ? uiText("Đã thu hồi") : new Date(s.expires * 1000).toLocaleString()}`,
        !s.revoked &&
          h(
            "button",
            { onClick: () => run(() => post(`/shares/${s.id}`, {}, "DELETE")) },
            uiText("Thu hồi"),
          ),
      ),
    ),
    h("h3", null, uiText("Tạo dự án")),
    h(
      "p",
      null,
      uiText("Bối cảnh dự án được dùng cho các cuộc trò chuyện thuộc dự án. Các liên kết và nội dung là tài liệu tham khảo."),
    ),
    h(
      "label",
      null,
      uiText("Tên dự án"),
      h("input", { value: title, onChange: (e) => setTitle(e.target.value) }),
    ),
    h(
      "label",
      null,
      uiText("Bối cảnh"),
      h("textarea", {
        value: context,
        onChange: (e) => setContext(e.target.value),
        rows: 5,
      }),
    ),
    h(
      "button",
      {
        disabled: !title.trim(),
        onClick: () =>
          run(async () => {
            const p = await post("/workspace/projects", { title, context });
            setProject(p.id);
            setTitle("");
            setContext("");
          }),
      },
      uiText("Lưu dự án"),
    ),
    ...projects.map((p) =>
      h(
        "details",
        { key: p.id },
        h("summary", null, p.title),
        h("p", { style: { whiteSpace: "pre-wrap" } }, p.context),
        h(
          "button",
          {
            onClick: () => {
              const value = window.prompt(uiText("Bối cảnh dự án"), p.context);
              if (value !== null)
                run(() =>
                  post(
                    `/workspace/projects/${p.id}`,
                    { title: p.title, context: value, links: p.links },
                    "PUT",
                  ),
                );
            },
          },
          uiText("Sửa bối cảnh"),
        ),
      ),
    ),
  );
}
