import React, { useEffect, useState } from "react";
const h = React.createElement;
const templates = {
  skills: { title: "", instruction: "", enabled: true },
  agents: { title: "", instruction: "", skills: [], enabled: true },
  workflows: {
    title: "",
    agent_id: null,
    steps: [{ kind: "ai", prompt: "" }],
    enabled: true,
  },
};
const labels = { skills: "Kỹ năng", agents: "Trợ lý", workflows: "Quy trình" };
export default function Automation({ api, post }) {
  const [data, setData] = useState(null),
    [kind, setKind] = useState("workflows"),
    [draft, setDraft] = useState(templates.workflows),
    [id, setId] = useState(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  async function reload() {
    setData(await api("/automation"));
  }
  useEffect(() => {
    reload().catch((e) => setError(e.message));
    const timer = setInterval(() => reload().catch(() => {}), 5000);
    return () => clearInterval(timer);
  }, []);
  async function run(fn) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function edit(next, value = null) {
    setKind(next);
    setId(value?.id || null);
    const { id: _, ...body } = value || templates[next];
    setDraft(body);
  }
  function update(values) {
    setDraft({ ...draft, ...values });
  }
  function step(index, values) {
    update({
      steps: draft.steps.map((s, i) => (i === index ? { ...s, ...values } : s)),
    });
  }
  return h(
    "section",
    { className: "panel workspace-panel", style: { padding: 24 } },
    h("h2", null, "Tự động hóa"),
    h(
      "p",
      null,
      "Kỹ năng và trợ lý định hướng nội dung. Quy trình chạy từng bước, lưu kết quả và dừng chờ phê duyệt công cụ theo quyền MCP. Hủy dừng các bước tiếp theo; thao tác đã gửi ra ngoài có thể đã thực hiện.",
    ),
    error && h("p", { role: "alert" }, error),
    notice && h("p", { role: "status" }, notice),
    h(
      "nav",
      null,
      ...Object.entries(labels).map(([k, label]) =>
        h("button", { key: k, onClick: () => edit(k) }, label),
      ),
    ),
    h("h3", null, `${id ? "Sửa" : "Tạo"} ${labels[kind].toLowerCase()}`),
    h(
      "label",
      null,
      "Tên",
      h("input", {
        value: draft.title,
        onChange: (e) => update({ title: e.target.value }),
      }),
    ),
    kind !== "workflows" &&
      h(
        "label",
        null,
        "Hướng dẫn",
        h("textarea", {
          value: draft.instruction,
          rows: 5,
          onChange: (e) => update({ instruction: e.target.value }),
        }),
      ),
    kind === "agents" &&
      h(
        "fieldset",
        null,
        h("legend", null, "Kỹ năng của trợ lý"),
        ...(data?.skills || []).map((s) =>
          h(
            "label",
            { key: s.id },
            h("input", {
              type: "checkbox",
              checked: draft.skills.includes(s.id),
              onChange: (e) =>
                update({
                  skills: e.target.checked
                    ? [...draft.skills, s.id]
                    : draft.skills.filter((v) => v !== s.id),
                }),
            }),
            s.title,
          ),
        ),
      ),
    kind === "workflows" &&
      h(
        "div",
        null,
        h(
          "label",
          null,
          "Trợ lý",
          h(
            "select",
            {
              value: draft.agent_id || "",
              onChange: (e) => update({ agent_id: e.target.value || null }),
            },
            h("option", { value: "" }, "Không dùng trợ lý"),
            ...(data?.agents || []).map((a) =>
              h("option", { key: a.id, value: a.id }, a.title),
            ),
          ),
        ),
        ...draft.steps.map((s, i) =>
          h(
            "fieldset",
            { key: i },
            h("legend", null, `Bước ${i + 1}`),
            h(
              "select",
              {
                "aria-label": `Loại bước ${i + 1}`,
                value: s.kind,
                onChange: (e) => step(i, { kind: e.target.value }),
              },
              h("option", { value: "ai" }, "AI soạn nội dung"),
              h("option", { value: "note" }, "Ghi chú / nhắc việc"),
              h("option", { value: "mcp" }, "Gọi công cụ MCP"),
            ),
            s.kind !== "mcp"
              ? h("textarea", {
                  "aria-label": `Yêu cầu bước ${i + 1}`,
                  value: s.prompt || "",
                  onChange: (e) => step(i, { prompt: e.target.value }),
                })
              : h(
                  "div",
                  null,
                  h(
                    "label",
                    null,
                    "Mã kết nối",
                    h("input", {
                      value: s.connector || "",
                      onChange: (e) => step(i, { connector: e.target.value }),
                    }),
                  ),
                  h(
                    "label",
                    null,
                    "Tên công cụ",
                    h("input", {
                      value: s.tool || "",
                      onChange: (e) => step(i, { tool: e.target.value }),
                    }),
                  ),
                  h(
                    "label",
                    null,
                    "Tham số JSON",
                    h("textarea", {
                      value:
                        s.argumentsText ??
                        JSON.stringify(s.arguments || {}, null, 2),
                      onChange: (e) =>
                        step(i, { argumentsText: e.target.value }),
                    }),
                  ),
                ),
            h(
              "button",
              {
                disabled: draft.steps.length === 1,
                onClick: () =>
                  update({ steps: draft.steps.filter((_, n) => n !== i) }),
              },
              "Bỏ bước",
            ),
          ),
        ),
        h(
          "button",
          {
            disabled: draft.steps.length >= 12,
            onClick: () =>
              update({ steps: [...draft.steps, { kind: "ai", prompt: "" }] }),
          },
          "Thêm bước",
        ),
      ),
    h(
      "label",
      null,
      h("input", {
        type: "checkbox",
        checked: draft.enabled,
        onChange: (e) => update({ enabled: e.target.checked }),
      }),
      " Bật",
    ),
    h(
      "button",
      {
        disabled: busy || !draft.title.trim(),
        onClick: () =>
          run(async () => {
            const body =
              kind === "workflows"
                ? {
                    ...draft,
                    steps: draft.steps.map(({ argumentsText, ...s }) => ({
                      ...s,
                      arguments:
                        argumentsText === undefined
                          ? s.arguments || {}
                          : JSON.parse(argumentsText),
                    })),
                  }
                : draft;
            await post(
              `/automation/${kind}${id ? `/${id}` : ""}`,
              body,
              id ? "PUT" : "POST",
            );
            edit(kind);
            setNotice("Đã lưu.");
          }),
      },
      "Lưu",
    ),
    h("h3", null, labels[kind]),
    ...(data?.[kind] || []).map((item) =>
      h(
        "article",
        { key: item.id, style: { padding: 12 } },
        h("strong", null, item.title),
        h("button", { onClick: () => edit(kind, item) }, "Sửa"),
        kind === "workflows" &&
          h(
            "button",
            {
              disabled: busy || !item.enabled,
              onClick: () =>
                run(async () => {
                  await post(`/automation/workflows/${item.id}/run`, {});
                  setNotice("Đã đưa vào hàng đợi.");
                }),
            },
            "Chạy",
          ),
        kind === "workflows" &&
          h(
            "button",
            {
              disabled: busy || !item.enabled,
              onClick: () => {
                const n = window.prompt(
                  "Chạy lặp mỗi bao nhiêu phút? Tối thiểu 15 phút. Mỗi lượt có thể dùng hạn mức AI hoặc thực hiện công cụ đã cấp quyền.",
                  "60",
                );
                if (n !== null)
                  run(() =>
                    post("/automation/schedules", {
                      workflow_id: item.id,
                      interval_minutes: Number(n),
                      enabled: true,
                    }),
                  );
              },
            },
            "Đặt lịch",
          ),
      ),
    ),
    h("h3", null, "Lịch lặp"),
    ...(data?.schedules || []).map((s) =>
      h(
        "p",
        { key: s.id },
        `${data.workflows.find((w) => w.id === s.workflow_id)?.title || s.workflow_id} · ${s.interval_minutes} phút · ${s.enabled ? "Bật" : "Tạm dừng"}`,
        h(
          "button",
          {
            onClick: () =>
              run(() =>
                post(
                  `/automation/schedules/${s.id}`,
                  {
                    workflow_id: s.workflow_id,
                    interval_minutes: s.interval_minutes,
                    enabled: !s.enabled,
                  },
                  "PUT",
                ),
              ),
          },
          s.enabled ? "Tạm dừng" : "Bật lại",
        ),
      ),
    ),
    h("h3", null, "Hộp kết quả"),
    ...(data?.runs || []).map((r) =>
      h(
        "details",
        { key: r.id },
        h(
          "summary",
          null,
          `${r.definition.title} · ${r.status} · bước ${r.step}/${r.definition.steps.length}`,
        ),
        r.error && h("p", null, r.error),
        h(
          "pre",
          { style: { whiteSpace: "pre-wrap", overflowWrap: "anywhere" } },
          JSON.stringify(r.results, null, 2),
        ),
        r.status === "waiting" &&
          h(
            "p",
            null,
            "Mở mục Phê duyệt để xem và quyết định thao tác cụ thể.",
          ),
        ["queued", "running", "waiting"].includes(r.status) &&
          h(
            "button",
            {
              onClick: () =>
                run(() => post(`/automation/runs/${r.id}/cancel`, {})),
            },
            "Hủy các bước tiếp theo",
          ),
      ),
    ),
  );
}
