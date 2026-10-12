import { t as uiText, localeTag } from "../i18n/runtime.js";
import React from "react";
const h = React.createElement;

/** Links are derived from actual Markdown [[wikilinks]], without external fetching. */
export default function KnowledgeGraph({ notes = [] }) {
  const edges = notes.flatMap((note) =>
    [...note.content.matchAll(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g)].map(
      (match) => ({ from: note.path, to: match[1] }),
    ),
  );
  return h(
    "div",
    { className: "knowledge-links" },
    h("h3", null, uiText("Liên kết kiến thức")),
    edges.length
      ? h(
          "ul",
          null,
          ...edges.map((edge, i) =>
            h("li", { key: i }, `${edge.from} → ${edge.to}`),
          ),
        )
      : h(
          "p",
          { className: "muted" },
          uiText("Dùng [[tên ghi chú]] để nối các ý tưởng."),
        ),
  );
}
