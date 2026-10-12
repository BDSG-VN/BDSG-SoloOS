import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useEffect, useRef, useState } from "react";
import {
  Renderer,
  createLibrary,
  defineComponent,
  FormNameContext,
  useStateField,
  useTriggerAction,
  useIsStreaming,
} from "@openuidev/react-lang";
import { z } from "zod/v4";
import { readSSE } from "./stream.js";

const h = React.createElement;

const Text = defineComponent({
  name: "Text",
  description: "Text paragraph. Plain text, no HTML.",
  props: z.object({ text: z.string().max(20000) }),
  component: ({ props }) => h("p", { className: "ui-text" }, props.text),
});

const BarChart = defineComponent({
  name: "BarChart",
  description: "Bar chart of finite numbers aligned with labels.",
  props: z.object({
    title: z.string(),
    labels: z.array(z.string()).max(50),
    values: z.array(z.number().finite()).max(50),
  }),
  component: ({ props }) => {
    const labels = props.labels ?? [],
      values = props.values ?? [];
    const max = Math.max(1, ...values.map((v) => Math.abs(Number(v) || 0)));
    return h(
      "figure",
      { className: "ui-chart" },
      h("figcaption", null, props.title),
      h(
        "div",
        { className: "bars", role: "img", "aria-label": props.title },
        ...labels.map((label, i) =>
          h(
            "div",
            { className: "bar-col", key: i },
            h("span", { className: "bar-value" }, values[i] ?? "…"),
            h("div", {
              className: "bar",
              style: {
                height: `${Math.max(2, (Math.abs(Number(values[i]) || 0) / max) * 100)}%`,
              },
            }),
            h("span", { className: "bar-label" }, label),
          ),
        ),
      ),
      h(
        "details",
        null,
        h("summary", null, uiText("Xem dữ liệu")),
        h(
          "table",
          null,
          h(
            "tbody",
            null,
            ...labels.map((label, i) =>
              h(
                "tr",
                { key: i },
                h("th", { scope: "row" }, label),
                h("td", null, values[i] ?? "…"),
              ),
            ),
          ),
        ),
      ),
    );
  },
});

const Progress = defineComponent({
  name: "Progress",
  description: "Labeled progress percentage from 0 to 100.",
  props: z.object({ label: z.string(), value: z.number().min(0).max(100) }),
  component: ({ props }) =>
    h(
      "label",
      { className: "ui-progress" },
      props.label,
      h("progress", { max: 100, value: props.value ?? 0 }),
    ),
});

const Input = defineComponent({
  name: "Input",
  description: "Named text field within a Form.",
  props: z.object({
    name: z.string(),
    label: z.string(),
    placeholder: z.string().optional(),
  }),
  component: ({ props }) => {
    const field = useStateField(props.name);
    const streaming = useIsStreaming();
    return h(
      "label",
      { className: "ui-field" },
      props.label,
      h("input", {
        name: props.name,
        value: field.value ?? "",
        placeholder: props.placeholder,
        disabled: streaming,
        onChange: (e) => field.setValue(e.target.value),
        required: true,
      }),
    );
  },
});

const Form = defineComponent({
  name: "Form",
  description:
    "A named form. Submission sends user intent; never grants tool permissions.",
  props: z.object({
    name: z.string(),
    title: z.string(),
    fields: z.array(Input.ref).max(20),
    submitLabel: z.string(),
  }),
  component: ({ props, renderNode }) => {
    const triggerAction = useTriggerAction();
    const streaming = useIsStreaming();
    return h(
      FormNameContext.Provider,
      { value: props.name },
      h(
        "form",
        {
          className: "ui-form",
          onSubmit: (e) => {
            e.preventDefault();
            if (!streaming) triggerAction(props.submitLabel, props.name);
          },
        },
        h("h3", null, props.title),
        renderNode(props.fields),
        h("button", { type: "submit", disabled: streaming }, props.submitLabel),
      ),
    );
  },
});

const Stack = defineComponent({
  name: "Stack",
  description: "Root layout with text, charts, progress and forms.",
  props: z.object({
    children: z
      .array(z.union([Text.ref, BarChart.ref, Progress.ref, Form.ref]))
      .max(50),
  }),
  component: ({ props, renderNode }) =>
    h("div", { className: "ui-stack" }, renderNode(props.children)),
});

export const soloLibrary = createLibrary({
  root: "Stack",
  components: [Stack, Text, BarChart, Progress, Form, Input],
});
export const soloUIPrompt = soloLibrary.prompt({
  preamble:
    "Output only OpenUI Lang. Respond in Vietnamese. Never output HTML or JavaScript.",
  additionalRules: [
    "Define root first, using references to separate child statements.",
    "Use only registered components. Do not generate Query, Mutation, fetch or external URLs.",
    "Form submission is user intent and cannot approve an MCP action.",
  ],
  examples: [
    'root = Stack([title, chart])\ntitle = Text("Tổng quan")\nchart = BarChart("Doanh thu", ["T1", "T2"], [10, 20])',
  ],
});

class RenderBoundary extends React.Component {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error
      ? h("p", { role: "alert" }, uiText("Không thể kết xuất giao diện này."))
      : this.props.children;
  }
}

/** Controlled response OR authenticated API SSE stream. The official runtime parses partial Lang.
 * request must have stable identity; changing it cancels the previous response.
 * Server event contract: token{text}, confirmation{id}, done, error{message}.
 */
export default function OpenUIRender({
  response = null,
  isStreaming = false,
  url = null,
  request,
  onAction,
  onStateUpdate,
  initialState,
  onConfirmation,
  onComplete,
  onError,
}) {
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const callbacks = useRef({});
  callbacks.current = { onConfirmation, onComplete, onError };
  useEffect(() => {
    if (!url) return;
    const controller = new AbortController();
    let active = true,
      content = "",
      frame = null;
    setText("");
    setError("");
    setStreaming(true);
    const flush = () => {
      frame = null;
      if (active) setText(content);
    };
    (async () => {
      try {
        const result = await fetch(url, {
          ...request,
          credentials: "include",
          signal: controller.signal,
        });
        if (!result.ok) throw new Error(uiText("API trả về lỗi {0}.", [result.status]));
        if (!result.headers.get("content-type")?.includes("text/event-stream"))
          throw new Error(uiText("API phải trả về SSE."));
        let complete = false;
        for await (const event of readSSE(result.body)) {
          if (!active) break;
          if (event.type === "token" && typeof event.text === "string") {
            content += event.text;
            if (content.length > 200000)
              throw new Error(uiText("Giao diện vượt giới hạn kích thước."));
            if (frame === null) frame = requestAnimationFrame(flush);
          } else if (event.type === "confirmation") {
            callbacks.current.onConfirmation?.(event.confirmation_id);
          } else if (event.type === "error") {
            throw new Error(event.message || uiText("Luồng AI gặp lỗi."));
          } else if (event.type === "done") {
            complete = true;
            break;
          }
        }
        if (active && !complete)
          throw new Error(uiText("Luồng kết thúc trước tín hiệu hoàn tất."));
        if (active) callbacks.current.onComplete?.(content);
      } catch (err) {
        if (active && err.name !== "AbortError") {
          setError(err.message);
          callbacks.current.onError?.(err);
        }
      } finally {
        if (frame !== null) cancelAnimationFrame(frame);
        if (active) {
          setText(content);
          setStreaming(false);
        }
      }
    })();
    return () => {
      active = false;
      controller.abort();
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [url, request]);
  const busy = url ? streaming : isStreaming;
  return h(
    "section",
    { className: "openui", "aria-busy": busy },
    error && h("p", { className: "error", role: "alert" }, error),
    h(
      RenderBoundary,
      { key: url ? `${url}-${request?.body ?? ""}` : "controlled" },
      h(Renderer, {
        library: soloLibrary,
        response: url ? text : response,
        isStreaming: busy,
        toolProvider: null,
        onAction,
        onStateUpdate,
        initialState,
        onError: (errors) => {
          if (errors.length && !busy) callbacks.current.onError?.(errors);
        },
      }),
    ),
    busy &&
      h(
        "div",
        { className: "stream-status", role: "status" },
        uiText("Đang kết xuất giao diện…"),
      ),
  );
}
