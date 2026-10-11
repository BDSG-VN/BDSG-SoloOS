import React, { useEffect, useRef, useState } from "react";
const h = React.createElement;
const groups = [
  ["Làm việc", "Work", ["overview", "chat", "sessions", "tasks"]],
  ["Doanh nghiệp", "Business", ["business", "cms"]],
  ["Tự động hóa", "Automation", ["automation", "operations", "approvals"]],
  ["Kiến thức", "Knowledge", ["library", "brain"]],
  ["Hệ thống", "System", ["accounts", "mcp", "devices"]],
];
export default function Navigation({
  labels,
  icons,
  page,
  onNavigate,
  disabled,
  approvals,
  lang,
  onReveal,
}) {
  const [query, setQuery] = useState("");
  const input = useRef(null);
  useEffect(() => {
    const key = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onReveal();
        setTimeout(() => input.current?.focus(), 0);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onReveal]);
  return h(
    "nav",
    { "aria-label": "Điều hướng chính" },
    h(
      "label",
      { className: "nav-search" },
      h("span", null, "Tìm chức năng"),
      h("input", {
        ref: input,
        type: "search",
        value: query,
        placeholder: "Tìm nhanh · ⌘ K",
        onChange: (e) => setQuery(e.target.value),
      }),
    ),
    ...groups.map(([vi, en, ids]) => {
      const matches = ids.filter((id) =>
        labels[id].toLocaleLowerCase().includes(query.toLocaleLowerCase()),
      );
      return matches.length
        ? h(
            "section",
            { key: vi, className: "nav-group" },
            h("h2", null, lang === "vi" ? vi : en),
            ...matches.map((id) =>
              h(
                "button",
                {
                  key: id,
                  "aria-label": labels[id],
                  "aria-current": page === id ? "page" : undefined,
                  title: labels[id],
                  className: page === id ? "active" : "",
                  disabled,
                  onClick: () => {
                    onNavigate(id);
                    setQuery("");
                  },
                },
                h(icons[id], { size: 18 }),
                h("span", null, labels[id]),
                id === "approvals" && approvals > 0 && h("b", null, approvals),
              ),
            ),
          )
        : null;
    }),
    query &&
      !Object.values(labels).some((v) =>
        v.toLowerCase().includes(query.toLowerCase()),
      ) &&
      h("p", { role: "status" }, "Không tìm thấy chức năng."),
  );
}
