import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useEffect, useRef, useState } from "react";
const h = React.createElement;
export default function Library({ api, post, onDirtyChange }) {
  const [sessions, setSessions] = useState([]),
    [conversation, setConversation] = useState("default"),
    [learning, setLearning] = useState(false);
  const [brains, setBrains] = useState([]),
    [brain, setBrain] = useState("default"),
    [notes, setNotes] = useState([]),
    [proposals, setProposals] = useState([]),
    [revisions, setRevisions] = useState([]);
  const [title, setTitle] = useState(""),
    [path, setPath] = useState("memory/FACTS.md"),
    [content, setContent] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const currentBrain = useRef(brain),
    currentPath = useRef(path),
    generation = useRef(0),
    mounted = useRef(true);
  currentBrain.current = brain;
  currentPath.current = path;
  const [baseline, setBaseline] = useState({
    path: "memory/FACTS.md",
    content: "",
  });
  const dirty = path !== baseline.path || content !== baseline.content;
  const dirtyRef = useRef(dirty),
    editor = useRef({ brain, path, content });
  dirtyRef.current = dirty;
  editor.current = { brain, path, content };
  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      onDirtyChange?.(false);
    };
  }, [onDirtyChange]);
  useEffect(() => {
    const warn = (e) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function mayDiscard() {
    return (
      !dirtyRef.current ||
      window.confirm(uiText("Bản đề xuất chưa lưu. Bỏ thay đổi đang sửa?"))
    );
  }
  function changeBrain(next) {
    if (!mayDiscard()) return;
    currentBrain.current = next;
    generation.current++;
    setBrain(next);
    setNotes([]);
    setProposals([]);
    setSessions([]);
    setRevisions([]);
    setPath("memory/FACTS.md");
    setContent("");
    setBaseline({ path: "memory/FACTS.md", content: "" });
  }
  async function reload() {
    if (brain !== currentBrain.current) return;
    const request = ++generation.current;
    const [bs, ns, ps, ss] = await Promise.all([
      api("/library"),
      api(`/library/${brain}/notes`),
      api(`/library/${brain}/proposals`),
      api("/workspace/sessions"),
    ]);
    if (
      !mounted.current ||
      request !== generation.current ||
      brain !== currentBrain.current
    )
      return;
    setBrains(bs);
    const eligible = ss.filter((s) => (s.brain_id || "default") === brain);
    setSessions(eligible);
    setConversation((current) =>
      eligible.some((s) => s.id === current) ? current : eligible[0]?.id || "",
    );
    setNotes(ns);
    setProposals(ps);
  }
  useEffect(() => {
    reload().catch((e) => setError(e.message));
  }, [brain]);
  async function run(fn) {
    setError("");
    setNotice("");
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e.message);
    }
  }
  function select(note) {
    if (!mayDiscard()) return;
    setBaseline({ path: note.path, content: note.content });
    setPath(note.path);
    setContent(note.content);
    setRevisions([]);
  }
  return h(
    "section",
    { className: "panel workspace-panel", style: { padding: 24 } },
    h("h2", null, uiText("Thư viện bộ nhớ")),
    h(
      "p",
      null,
      uiText("Mỗi bộ nhớ có tài liệu và kết nối MCP riêng. Chọn bộ nhớ khi tạo cuộc trò chuyện. Mọi đề xuất dưới đây cần bạn duyệt; nếu tài liệu đã đổi, đề xuất cũ bị từ chối."),
    ),
    error && h("p", { role: "alert" }, error),
    notice && h("p", { role: "status" }, notice),
    h(
      "label",
      null,
      uiText("Bộ nhớ"),
      h(
        "select",
        { value: brain, onChange: (e) => changeBrain(e.target.value) },
        ...brains.map((b) => h("option", { key: b.id, value: b.id }, b.title)),
      ),
    ),
    h(
      "a",
      { href: `/api/library/${brain}/export`, download: true },
      uiText("Xuất tài liệu Markdown (.zip)"),
    ),
    h(
      "label",
      null,
      uiText("Tên bộ nhớ mới"),
      h("input", { value: title, onChange: (e) => setTitle(e.target.value) }),
    ),
    h(
      "button",
      {
        disabled: !title.trim(),
        onClick: () =>
          run(async () => {
            const b = await post("/library", { title });
            changeBrain(b.id);
            setTitle("");
          }),
      },
      uiText("Tạo bộ nhớ"),
    ),
    h("h3", null, uiText("Tài liệu")),
    ...notes.map((n) =>
      h("button", { key: n.path, onClick: () => select(n) }, n.path),
    ),
    h(
      "label",
      null,
      uiText("Đường dẫn Markdown"),
      h("input", {
        value: path,
        onChange: (e) => {
          setPath(e.target.value);
          setRevisions([]);
        },
      }),
    ),
    h(
      "label",
      null,
      uiText("Nội dung đề xuất"),
      h("textarea", {
        value: content,
        rows: 10,
        onChange: (e) => setContent(e.target.value),
      }),
    ),
    h("input", {
      type: "file",
      accept: ".md,.txt,text/plain,text/markdown",
      "aria-label": uiText("Nhập tài liệu văn bản"),
      onChange: async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        if (file.size > 100000) {
          setError(uiText("Tài liệu tối đa 100 KB."));
          return;
        }
        if (!mayDiscard()) return;
        const beforeImport = editor.current;
        const imported = await file.text();
        if (!mounted.current || editor.current !== beforeImport) return;
        setContent(imported);
        setPath(
          "wiki/" +
            file.name
              .replace(/[^a-zA-Z0-9._-]/g, "-")
              .replace(/\.(txt|md)$/i, "") +
            ".md",
        );
      },
    }),
    h(
      "button",
      {
        onClick: () =>
          run(async () => {
            await post(`/library/${brain}/proposals`, { path, content });
            if (currentBrain.current === brain && currentPath.current === path)
              setBaseline({ path, content });
            setNotice(uiText("Đã tạo đề xuất. Xem và duyệt bên dưới."));
          }),
      },
      uiText("Đề xuất lưu tài liệu"),
    ),
    h(
      "button",
      {
        onClick: () =>
          run(async () => {
            const rows = await api(
              `/library/${brain}/revisions?path=${encodeURIComponent(path)}`,
            );
            if (
              mounted.current &&
              currentBrain.current === brain &&
              currentPath.current === path
            )
              setRevisions(rows);
          }),
      },
      uiText("Lịch sử tài liệu"),
    ),
    ...revisions.map((r) =>
      h(
        "details",
        { key: r.id },
        h("summary", null, new Date(r.created * 1000).toLocaleString()),
        h("pre", null, r.content),
        h(
          "button",
          {
            onClick: () => {
              if (!mayDiscard()) return;
              setContent(r.content);
              setNotice(
                uiText("Đã đưa nội dung cũ vào ô đề xuất; chưa thay tài liệu đang lưu."),
              );
            },
          },
          uiText("Dùng bản này để đề xuất khôi phục"),
        ),
      ),
    ),
    h("h3", null, uiText("Học từ cuộc trò chuyện")),
    h(
      "select",
      {
        "aria-label": uiText("Cuộc trò chuyện để học"),
        value: conversation,
        onChange: (e) => setConversation(e.target.value),
      },
      ...sessions.map((s) => h("option", { key: s.id, value: s.id }, s.title)),
    ),
    h(
      "button",
      {
        disabled: learning || !conversation,
        onClick: () =>
          run(async () => {
            setLearning(true);
            try {
              await post(`/library/${brain}/learn`, { conversation, path });
              setNotice(uiText("AI đã tạo đề xuất; hãy đọc và duyệt bên dưới."));
            } finally {
              setLearning(false);
            }
          }),
      },
      learning ? uiText("Đang rút ra đề xuất…") : uiText("AI đề xuất ký ức"),
    ),
    h("h3", null, uiText("Chờ duyệt")),
    ...proposals.map((p) =>
      h(
        "details",
        { key: p.id },
        h("summary", null, p.path),
        h(
          "pre",
          { style: { whiteSpace: "pre-wrap", overflowWrap: "anywhere" } },
          p.content,
        ),
        h(
          "button",
          {
            onClick: () =>
              run(() =>
                post(`/library/proposals/${p.id}/decision`, { approved: true }),
              ),
          },
          uiText("Duyệt và ghi vào bộ nhớ"),
        ),
        h(
          "button",
          {
            onClick: () =>
              run(() =>
                post(`/library/proposals/${p.id}/decision`, {
                  approved: false,
                }),
              ),
          },
          uiText("Từ chối"),
        ),
      ),
    ),
  );
}
