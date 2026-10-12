import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useEffect, useState } from "react";
import { useUnsaved } from "./use_unsaved.js";
import Packs from "./packs.js";
import Schedules from "./schedules.js";
const h = React.createElement;
const templates = {
  skills: { title: "", instruction: "", enabled: true },
  agents: {
    title: "",
    instruction: "",
    skills: [],
    connectors: null,
    enabled: true,
  },
  workflows: {
    title: "",
    agent_id: null,
    steps: [{ kind: "ai", prompt: "" }],
    enabled: true,
  },
};
const labels = { get skills() { return uiText("Kỹ năng"); }, get agents() { return uiText("Trợ lý"); }, get workflows() { return uiText("Quy trình"); } };
export default function Automation({ api, post, onDirtyChange }) {
  const [data, setData] = useState(null),
    [kind, setKind] = useState("workflows"),
    [draft, setDraft] = useState(templates.workflows),
    [id, setId] = useState(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [baseline, setBaseline] = useState(JSON.stringify(templates.workflows));
  const mayDiscard = useUnsaved(
    JSON.stringify(draft) !== baseline,
    onDirtyChange,
  );
  const [connectors, setConnectors] = useState([]);
  const [busy, setBusy] = useState(false);
  async function reload() {
    const [automation, connections] = await Promise.all([
      api("/automation"),
      api("/mcp/connectors"),
    ]);
    setData(automation);
    setConnectors(connections);
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
  function edit(next, value = null, saved = false) {
    if (!saved && !mayDiscard()) return;
    setKind(next);
    setId(value?.id || null);
    const { id: _, ...body } = value || templates[next];
    setDraft(body);
    setBaseline(JSON.stringify(body));
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
    "fieldset",
    {
      disabled: busy,
      className: "panel workspace-panel",
      style: { padding: 24, minWidth: 0 },
    },
    h("h2", null, uiText("Tự động hóa")),
    h(
      "p",
      null,
      uiText("Kỹ năng và trợ lý định hướng nội dung. Quy trình chạy từng bước, lưu kết quả và dừng chờ phê duyệt công cụ theo quyền MCP. Hủy dừng các bước tiếp theo; thao tác đã gửi ra ngoài có thể đã thực hiện."),
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
    h("h3", null, `${id ? uiText("Sửa") : uiText("Tạo")} ${labels[kind].toLowerCase()}`),
    h(
      "label",
      null,
      uiText("Tên"),
      h("input", {
        value: draft.title,
        onChange: (e) => update({ title: e.target.value }),
      }),
    ),
    kind !== "workflows" &&
      h(
        "label",
        null,
        uiText("Hướng dẫn"),
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
        h("legend", null, uiText("Kỹ năng của trợ lý")),
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
    kind === "agents" &&
      h(
        "fieldset",
        null,
        h("legend", null, uiText("Phạm vi công cụ của trợ lý")),
        h(
          "label",
          null,
          h("input", {
            type: "checkbox",
            checked: draft.connectors == null,
            onChange: (e) =>
              update({ connectors: e.target.checked ? null : [] }),
          }),
          uiText(" Dùng các kết nối được chủ cấp quyền"),
        ),
        draft.connectors != null &&
          connectors.map((c) =>
            h(
              "label",
              { key: c.id },
              h("input", {
                type: "checkbox",
                checked: draft.connectors.includes(c.id),
                onChange: (e) =>
                  update({
                    connectors: e.target.checked
                      ? [...draft.connectors, c.id]
                      : draft.connectors.filter((v) => v !== c.id),
                  }),
              }),
              c.id,
            ),
          ),
        h(
          "small",
          null,
          uiText("Không chọn kết nối nào: chỉ soạn nội dung. Quyền tại MCP Hub vẫn áp dụng."),
        ),
      ),
    kind === "workflows" &&
      h(
        "div",
        null,
        h(
          "label",
          null,
          uiText("Trợ lý"),
          h(
            "select",
            {
              value: draft.agent_id || "",
              onChange: (e) => update({ agent_id: e.target.value || null }),
            },
            h("option", { value: "" }, uiText("Không dùng trợ lý")),
            ...(data?.agents || []).map((a) =>
              h("option", { key: a.id, value: a.id }, a.title),
            ),
          ),
        ),
        ...draft.steps.map((s, i) =>
          h(
            "fieldset",
            { key: i },
            h("legend", null, uiText("Bước {0}", [i + 1])),
            h(
              "select",
              {
                "aria-label": uiText("Loại bước {0}", [i + 1]),
                value: s.kind,
                onChange: (e) => step(i, { kind: e.target.value }),
              },
              h("option", { value: "ai" }, uiText("AI soạn nội dung")),
              h("option", { value: "note" }, uiText("Ghi chú / nhắc việc")),
              h("option", { value: "mcp" }, uiText("Gọi công cụ MCP")),
            ),
            s.kind !== "mcp"
              ? h("textarea", {
                  "aria-label": uiText("Yêu cầu bước {0}", [i + 1]),
                  value: s.prompt || "",
                  onChange: (e) => step(i, { prompt: e.target.value }),
                })
              : h(
                  "div",
                  null,
                  h(
                    "label",
                    null,
                    uiText("Mã kết nối"),
                    h("input", {
                      value: s.connector || "",
                      onChange: (e) => step(i, { connector: e.target.value }),
                    }),
                  ),
                  h(
                    "label",
                    null,
                    uiText("Tên công cụ"),
                    h("input", {
                      value: s.tool || "",
                      onChange: (e) => step(i, { tool: e.target.value }),
                    }),
                  ),
                  h(
                    "label",
                    null,
                    uiText("Tham số JSON"),
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
              uiText("Bỏ bước"),
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
          uiText("Thêm bước"),
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
      uiText(" Bật"),
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
            edit(kind, null, true);
            setNotice(uiText("Đã lưu."));
          }),
      },
      uiText("Lưu"),
    ),
    h("h3", null, labels[kind]),
    ...(data?.[kind] || []).map((item) =>
      h(
        "article",
        { key: item.id, style: { padding: 12 } },
        h("strong", null, item.title),
        h("button", { onClick: () => edit(kind, item) }, uiText("Sửa")),
        kind === "workflows" &&
          h(
            "button",
            {
              disabled: busy || !item.enabled,
              onClick: () =>
                run(async () => {
                  await post(`/automation/workflows/${item.id}/run`, {});
                  setNotice(uiText("Đã đưa vào hàng đợi."));
                }),
            },
            uiText("Chạy"),
          ),
      ),
    ),
    h(Packs, { post, onSaved: reload }),
    h(Schedules, { data, api, post, onSaved: reload }),
    h("h3", null, uiText("Hộp kết quả")),
    ...(data?.runs || []).map((r) =>
      h(
        "details",
        { key: r.id },
        h(
          "summary",
          null,
          uiText("{0} · {1} · bước {2}/{3}", [r.definition.title, r.status, r.step, r.definition.steps.length]),
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
            uiText("Mở mục Phê duyệt để xem và quyết định thao tác cụ thể."),
          ),
        ["queued", "running", "waiting"].includes(r.status) &&
          h(
            "button",
            {
              onClick: () =>
                run(() => post(`/automation/runs/${r.id}/cancel`, {})),
            },
            uiText("Hủy các bước tiếp theo"),
          ),
      ),
    ),
  );
}
