import React, { useEffect, useState } from "react";
const h = React.createElement;
export default function Sessions({ api, post, onOpen }) {
  const [sessions, setSessions] = useState([]),
    [projects, setProjects] = useState([]),
    [search, setSearch] = useState(""),
    [archived, setArchived] = useState(false);
  const [title, setTitle] = useState(""),
    [context, setContext] = useState(""),
    [project, setProject] = useState(""),
    [error, setError] = useState("");
  async function reload() {
    const [s, p] = await Promise.all([
      api(
        `/workspace/sessions?archived=${archived}&search=${encodeURIComponent(search)}`,
      ),
      api("/workspace/projects"),
    ]);
    setSessions(s);
    setProjects(p);
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
    h("h2", null, "Cuộc trò chuyện & dự án"),
    error && h("p", { role: "alert" }, error),
    h(
      "label",
      null,
      "Tìm theo tên hoặc nội dung",
      h("input", { value: search, onChange: (e) => setSearch(e.target.value) }),
    ),
    h(
      "label",
      null,
      h("input", {
        type: "checkbox",
        checked: archived,
        onChange: (e) => setArchived(e.target.checked),
      }),
      " Đã lưu trữ",
    ),
    h(
      "div",
      null,
      h(
        "label",
        null,
        "Dự án",
        h(
          "select",
          { value: project, onChange: (e) => setProject(e.target.value) },
          h("option", { value: "" }, "Không gắn dự án"),
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
              });
              onOpen(s);
            }),
        },
        "Cuộc trò chuyện mới",
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
        h("button", { onClick: () => onOpen(s), disabled: s.archived }, "Mở"),
        h(
          "button",
          { onClick: () => run(() => update(s, { pinned: !s.pinned })) },
          s.pinned ? "Bỏ ghim" : "Ghim",
        ),
        h(
          "button",
          {
            onClick: () => {
              const name = window.prompt("Tên cuộc trò chuyện", s.title);
              if (name?.trim()) run(() => update(s, { title: name.trim() }));
            },
          },
          "Đổi tên",
        ),
        h(
          "button",
          { onClick: () => run(() => update(s, { archived: !s.archived })) },
          s.archived ? "Khôi phục" : "Lưu trữ",
        ),
        h(
          "a",
          { href: `/api/workspace/sessions/${s.id}/export`, download: true },
          "Xuất JSON",
        ),
      ),
    ),
    h("h3", null, "Tạo dự án"),
    h(
      "p",
      null,
      "Bối cảnh dự án được dùng cho các cuộc trò chuyện thuộc dự án. Các liên kết và nội dung là tài liệu tham khảo.",
    ),
    h(
      "label",
      null,
      "Tên dự án",
      h("input", { value: title, onChange: (e) => setTitle(e.target.value) }),
    ),
    h(
      "label",
      null,
      "Bối cảnh",
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
      "Lưu dự án",
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
              const value = window.prompt("Bối cảnh dự án", p.context);
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
          "Sửa bối cảnh",
        ),
      ),
    ),
  );
}
