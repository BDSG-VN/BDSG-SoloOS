import React, { useEffect, useState } from "react";
import { useUnsaved } from "./use_unsaved.js";
const h = React.createElement;
const initial = {
  title: "",
  description: "",
  priority: "normal",
  due: null,
  project_id: null,
  agent_id: null,
};
const states = { todo: "Cần làm", doing: "Đang làm", done: "Hoàn tất" },
  priorities = {
    urgent: "Khẩn cấp",
    high: "Cao",
    normal: "Bình thường",
    low: "Thấp",
  };
export default function Workboard({ api, post, onDirtyChange, onSaved }) {
  const [tasks, setTasks] = useState([]),
    [projects, setProjects] = useState([]),
    [agents, setAgents] = useState([]),
    [draft, setDraft] = useState(initial),
    [id, setId] = useState(null),
    [filter, setFilter] = useState(""),
    [query, setQuery] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const [baseline, setBaseline] = useState(JSON.stringify(initial));
  const mayDiscard = useUnsaved(
    JSON.stringify(draft) !== baseline,
    onDirtyChange,
  );
  const patch = (v) => setDraft({ ...draft, ...v });
  async function reload() {
    const [t, p, a] = await Promise.all([
      api("/tasks"),
      api("/workspace/projects"),
      api("/automation"),
    ]);
    setTasks(t);
    setProjects(p);
    setAgents(a.agents);
  }
  useEffect(() => {
    reload().catch((e) => setError(e.message));
  }, []);
  async function run(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await reload();
      await onSaved?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const visible = tasks
    .filter(
      (t) =>
        (!filter || t.project_id === filter) &&
        `${t.title} ${t.description}`
          .toLowerCase()
          .includes(query.toLowerCase()),
    )
    .sort(
      (a, b) =>
        Object.keys(priorities).indexOf(a.priority) -
        Object.keys(priorities).indexOf(b.priority),
    );
  return h(
    "section",
    { className: "workboard" },
    error && h("p", { role: "alert" }, error),
    h(
      "form",
      {
        className: "panel",
        onSubmit: (e) => {
          e.preventDefault();
          run(async () => {
            await post(
              "/tasks" + (id ? "/" + id : ""),
              draft,
              id ? "PUT" : "POST",
            );
            setDraft(initial);
            setBaseline(JSON.stringify(initial));
            setId(null);
          });
        },
      },
      h("h2", null, id ? "Sửa công việc" : "Lập công việc"),
      h(
        "fieldset",
        { disabled: busy },
        h(
          "label",
          null,
          "Tên công việc",
          h("input", {
            value: draft.title,
            required: true,
            maxLength: 500,
            onChange: (e) => patch({ title: e.target.value }),
          }),
        ),
        h(
          "details",
          null,
          h("summary", null, "Chi tiết, ưu tiên & phân công"),
          h(
            "label",
            null,
            "Mô tả công việc",
            h("textarea", {
              value: draft.description,
              rows: 4,
              onChange: (e) => patch({ description: e.target.value }),
            }),
          ),
          h(
            "div",
            { className: "form-grid" },
            h(
              "label",
              null,
              "Mức ưu tiên",
              h(
                "select",
                {
                  value: draft.priority,
                  onChange: (e) => patch({ priority: e.target.value }),
                },
                ...Object.entries(priorities).map(([v, n]) =>
                  h("option", { key: v, value: v }, n),
                ),
              ),
            ),
            h(
              "label",
              null,
              "Hạn hoàn thành",
              h("input", {
                type: "date",
                value: draft.due || "",
                onChange: (e) => patch({ due: e.target.value || null }),
              }),
            ),
            h(
              "label",
              null,
              "Dự án công việc",
              h(
                "select",
                {
                  value: draft.project_id || "",
                  onChange: (e) =>
                    patch({ project_id: e.target.value || null }),
                },
                h("option", { value: "" }, "Không gắn dự án"),
                ...projects.map((p) =>
                  h("option", { key: p.id, value: p.id }, p.title),
                ),
              ),
            ),
            h(
              "label",
              null,
              "Trợ lý phụ trách",
              h(
                "select",
                {
                  value: draft.agent_id || "",
                  onChange: (e) => patch({ agent_id: e.target.value || null }),
                },
                h("option", { value: "" }, "Chủ doanh nghiệp"),
                ...agents
                  .filter((a) => a.enabled)
                  .map((a) => h("option", { key: a.id, value: a.id }, a.title)),
              ),
            ),
          ),
          h(
            "small",
            { className: "muted" },
            "Phân công để theo dõi; không tự khởi chạy AI hay công cụ.",
          ),
        ),
        h(
          "div",
          { className: "button-row" },
          h(
            "button",
            { type: "submit", className: "primary" },
            id ? "Lưu công việc" : "Thêm việc",
          ),
          id &&
            h(
              "button",
              {
                type: "button",
                onClick: () => {
                  if (!mayDiscard()) return;
                  setDraft(initial);
                  setBaseline(JSON.stringify(initial));
                  setId(null);
                },
              },
              "Hủy sửa",
            ),
        ),
      ),
    ),
    h(
      "div",
      { className: "board-filters" },
      h(
        "label",
        null,
        "Tìm công việc",
        h("input", {
          type: "search",
          value: query,
          onChange: (e) => setQuery(e.target.value),
        }),
      ),
      h(
        "label",
        null,
        "Lọc dự án",
        h(
          "select",
          { value: filter, onChange: (e) => setFilter(e.target.value) },
          h("option", { value: "" }, "Tất cả dự án"),
          ...projects.map((p) =>
            h("option", { key: p.id, value: p.id }, p.title),
          ),
        ),
      ),
    ),
    h(
      "div",
      { className: "kanban" },
      ...Object.entries(states).map(([state, title]) =>
        h(
          "section",
          { className: "kanban-col", key: state },
          h(
            "h3",
            null,
            title,
            h("span", null, visible.filter((t) => t.state === state).length),
          ),
          ...visible
            .filter((t) => t.state === state)
            .map((t) =>
              h(
                "article",
                { key: t.id, className: "task-card" },
                h("strong", null, t.title),
                h(
                  "p",
                  {
                    className: t.priority === "urgent" ? "attention" : "muted",
                  },
                  priorities[t.priority],
                ),
                t.description && h("p", null, t.description),
                t.due && h("small", null, "Hạn: " + t.due),
                t.agent_id &&
                  h(
                    "small",
                    null,
                    "Trợ lý: " +
                      (agents.find((a) => a.id === t.agent_id)?.title ||
                        "Không còn hoạt động"),
                  ),
                h(
                  "select",
                  {
                    "aria-label": "Trạng thái " + t.title,
                    value: t.state,
                    disabled: busy,
                    onChange: (e) =>
                      run(() =>
                        post(
                          "/tasks/" + t.id,
                          { state: e.target.value },
                          "PATCH",
                        ),
                      ),
                  },
                  ...Object.entries(states).map(([value, label]) =>
                    h("option", { key: value, value }, label),
                  ),
                ),
                h(
                  "button",
                  {
                    disabled: busy,
                    onClick: () => {
                      if (!mayDiscard()) return;
                      setId(t.id);
                      const value = Object.fromEntries(
                        Object.keys(initial).map((key) => [
                          key,
                          t[key] ?? initial[key],
                        ]),
                      );
                      setDraft(value);
                      setBaseline(JSON.stringify(value));
                    },
                  },
                  "Sửa công việc",
                ),
              ),
            ),
        ),
      ),
    ),
  );
}
