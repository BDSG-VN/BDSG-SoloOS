import React, { useEffect, useRef, useState, useCallback } from "react";
import { readSSE } from "./stream.js";
import "./cms.css";
import SiteSettings from "./site_settings.js";
const h = React.createElement;
const TYPES = {
  hero: "Mở đầu",
  heading: "Tiêu đề",
  paragraph: "Đoạn văn",
  list: "Danh sách",
  quote: "Trích dẫn",
  button: "Nút liên kết",
  image: "Hình ảnh",
  divider: "Đường phân cách",
};
const STATUS = {
  draft: "Bản nháp",
  published: "Đã xuất bản",
  trash: "Thùng rác",
};
const blank = (kind) => ({
  kind,
  title: "",
  slug: "",
  excerpt: "",
  blocks: [{ type: "paragraph", text: "" }],
  categories: [],
  tags: [],
  sources: [],
  seo_title: "",
  seo_description: "",
  ai_generated: false,
});
const payload = (doc) =>
  Object.fromEntries(
    Object.keys(blank(doc.kind)).map((key) => [
      key,
      ["categories", "tags", "sources"].includes(key)
        ? doc[key].map((s) => s.trim()).filter(Boolean)
        : doc[key],
    ]),
  );

export function DraftPreview({ doc }) {
  return h(
    "article",
    { className: "cms-preview" },
    h("h1", null, doc.title || "Tiêu đề"),
    ...doc.blocks.map((b, i) => {
      const props = { key: i };
      if (b.type === "hero")
        return h(
          "section",
          { ...props, className: "cms-hero" },
          h("h2", null, b.text),
          h("p", null, b.detail),
        );
      if (b.type === "heading") return h("h2", props, b.text);
      if (b.type === "list")
        return h(
          "ul",
          props,
          ...(b.items || []).map((item, j) => h("li", { key: j }, item)),
        );
      if (b.type === "image")
        return /^\/media\/[a-f0-9]{32}\.webp$/.test(b.src || "")
          ? h(
              "figure",
              props,
              h("img", {
                src: b.src.replace("/media/", "/api/cms/media/"),
                alt: b.alt || "",
              }),
              h("figcaption", null, b.text),
            )
          : null;
      if (b.type === "button")
        return h(
          "span",
          { ...props, className: "cms-link-preview" },
          b.text,
          " ↗",
        );
      if (b.type === "divider") return h("hr", props);
      return h(b.type === "quote" ? "blockquote" : "p", props, b.text);
    }),
  );
}

export default function CMSWorkspace({
  api,
  post,
  streamRequest,
  onDirtyChange,
}) {
  const [kind, setKind] = useState("post"),
    [records, setRecords] = useState([]),
    [settings, setSettings] = useState(null),
    [media, setMedia] = useState([]);
  const [doc, setDoc] = useState(null),
    [saved, setSaved] = useState(""),
    [search, setSearch] = useState(""),
    [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [preview, setPreview] = useState(false),
    [revisions, setRevisions] = useState([]);
  const [instruction, setInstruction] = useState(""),
    [references, setReferences] = useState(""),
    [tokens, setTokens] = useState(0),
    [gateway, setGateway] = useState(null);
  const controller = useRef(null);
  const [siteDirty, setSiteDirty] = useState(false);
  const siteDirtyChange = useCallback((value) => setSiteDirty(value), []);
  const dirty = doc && JSON.stringify(payload(doc)) !== saved;
  useEffect(() => {
    onDirtyChange?.(Boolean(dirty || siteDirty || busy));
    const protect = (e) => {
      if (dirty || siteDirty || busy) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", protect);
    return () => {
      window.removeEventListener("beforeunload", protect);
      onDirtyChange?.(false);
    };
  }, [dirty, siteDirty, busy, onDirtyChange]);
  const load = async () => {
    const [r, s, m] = await Promise.all([
      api("/cms/content"),
      api("/cms/settings"),
      api("/cms/media"),
    ]);
    setRecords(r);
    setSettings(s);
    setMedia(m);
  };
  useEffect(() => {
    load().catch((e) => setError(e.message));
    return () => controller.current?.abort();
  }, []);
  const run = async (fn) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      return await fn();
    } catch (e) {
      if (e.name !== "AbortError") setError(e.message);
    } finally {
      controller.current = null;
      setBusy(false);
    }
  };
  const select = (value) => {
    setDoc(value);
    setSaved(value?.id ? JSON.stringify(payload(value)) : "");
    setRevisions([]);
    setPreview(false);
  };
  const mayLeave = () =>
    !dirty || window.confirm("Bản đang sửa chưa lưu. Bỏ các thay đổi này?");
  const update = (key, value) => setDoc((d) => ({ ...d, [key]: value }));
  const updateBlock = (i, changes) =>
    update(
      "blocks",
      doc.blocks.map((b, n) => (n === i ? { ...b, ...changes } : b)),
    );
  const btn = (label, fn, props = {}) =>
    h(
      "button",
      { type: "button", disabled: busy, onClick: () => run(fn), ...props },
      label,
    );
  const field = (label, value, change, multiline = false, props = {}) =>
    h(
      "label",
      { className: "cms-field" },
      label,
      h(multiline ? "textarea" : "input", {
        value: value || "",
        onChange: (e) => change(e.target.value),
        disabled: busy,
        ...props,
      }),
    );
  const save = async () => {
    const result = doc.id
      ? await post(
          `/cms/content/${doc.id}`,
          { content: payload(doc), expected_version: doc.version },
          "PUT",
        )
      : await post("/cms/content", payload(doc));
    select(result);
    await load();
    setNotice("Đã lưu bản nháp. Nội dung công khai chỉ cập nhật khi xuất bản.");
    return result;
  };
  const transition = async (action) => {
    if (dirty) throw new Error("Lưu bản nháp trước khi thay đổi trạng thái.");
    if (
      (action === "publish" || action === "trash") &&
      !window.confirm(
        action === "publish"
          ? "Xuất bản phiên bản đã lưu để mọi người có thể xem?"
          : "Chuyển vào thùng rác và gỡ khỏi trang công khai?",
      )
    )
      return;
    select(
      await post(`/cms/content/${doc.id}/transition`, {
        action,
        expected_version: doc.version,
      }),
    );
    await load();
    setNotice(
      action === "publish" ? "Đã xuất bản." : "Đã cập nhật trạng thái.",
    );
  };
  const generate = async () => {
    if (!instruction.trim()) throw new Error("Nhập yêu cầu cho AI.");
    if (
      (doc.id && dirty) ||
      (!doc.id &&
        JSON.stringify(payload(doc)) !== JSON.stringify(blank(doc.kind)))
    )
      throw new Error("Lưu nội dung đang sửa trước khi yêu cầu AI chỉnh tiếp.");
    controller.current = new AbortController();
    setTokens(0);
    const response = await streamRequest(
      {
        instruction,
        kind: doc.kind,
        content_id: doc.id || null,
        reference_text: references,
        sources: payload(doc).sources,
      },
      controller.current.signal,
    );
    if (!response.ok)
      throw new Error(
        "Không thể bắt đầu tạo bản thảo. Kiểm tra phiên đăng nhập và yêu cầu.",
      );
    let proposal = null,
      done = false;
    for await (const event of readSSE(response.body)) {
      if (event.type === "error") throw new Error(event.message);
      if (event.type === "token") setTokens((n) => n + event.text.length);
      if (event.type === "proposal") proposal = event.content;
      if (event.type === "done") done = true;
    }
    if (!proposal || !done)
      throw new Error("Luồng AI chưa hoàn tất. Bản đang sửa được giữ nguyên.");
    setDoc((d) => ({ ...d, ...proposal }));
    setPreview(true);
    setNotice(
      "AI đã tạo đề xuất. Kiểm tra thông tin và nguồn, chỉnh sửa rồi lưu bản nháp.",
    );
  };
  const upload = async (file) => {
    if (!file) return;
    const result = await api("/cms/media", {
      method: "POST",
      headers: { "Content-Type": file.type },
      body: file,
    });
    update("blocks", [
      ...doc.blocks,
      { type: "image", src: result.src, alt: "", text: "" },
    ]);
    await load();
  };
  const filtered = records.filter(
    (r) =>
      r.kind === kind &&
      (!status ? r.status !== "trash" : r.status === status) &&
      (r.title + " " + r.excerpt).toLowerCase().includes(search.toLowerCase()),
  );
  return h(
    "section",
    { className: "cms-workspace" },
    h(SiteSettings, {
      api,
      post,
      onDirtyChange: siteDirtyChange,
      disabled: busy,
      onDraft: async (theme) => {
        if (!mayLeave()) return false;
        const draft = await post(`/cms/themes/${theme}/draft`, {});
        setKind("page");
        select(draft);
        await load();
        return true;
      },
    }),
    h(
      "div",
      { className: "cms-heading" },
      h(
        "div",
        null,
        h("span", { className: "eyebrow" }, "NỘI DUNG & WEBSITE"),
        h("h2", null, "Từ ý tưởng đến trang công khai"),
        h(
          "p",
          null,
          "Viết tin, tạo trang bằng AI và duyệt từng phiên bản trước khi xuất bản.",
        ),
      ),
      btn("Cấu hình AI", () =>
        setGateway({ ...settings?.gateway, api_key: "" }),
      ),
    ),
    error && h("p", { role: "alert", className: "cms-error" }, String(error)),
    notice && h("p", { role: "status", className: "cms-notice" }, notice),
    gateway &&
      h(
        "form",
        {
          className: "panel cms-settings",
          onSubmit: (e) => {
            e.preventDefault();
            run(async () => {
              await post(
                "/cms/gateway",
                {
                  base_url: gateway.base_url,
                  model: gateway.model,
                  api_key: gateway.api_key || null,
                },
                "PUT",
              );
              setGateway(null);
              await load();
              setNotice("Đã lưu cổng AI cho CMS và AI Studio.");
            });
          },
        },
        h("h3", null, "Cổng AI tương thích OpenAI"),
        field(
          "Base URL (gồm /v1 nếu cổng yêu cầu)",
          gateway.base_url,
          (v) => setGateway((g) => ({ ...g, base_url: v })),
          false,
          { required: true, placeholder: "https://gateway.example/v1" },
        ),
        field(
          "Model",
          gateway.model,
          (v) => setGateway((g) => ({ ...g, model: v })),
          false,
          { required: true },
        ),
        field(
          gateway.has_api_key
            ? "API key mới (để trống giữ khóa cùng máy chủ)"
            : "API key",
          gateway.api_key,
          (v) => setGateway((g) => ({ ...g, api_key: v })),
          false,
          { type: "password", autoComplete: "new-password" },
        ),
        h(
          "p",
          null,
          "Khóa được mã hóa trên máy chủ. Khi đổi máy chủ, hãy nhập lại khóa. Yêu cầu AI gửi nội dung và tài liệu tham khảo tới cổng này.",
        ),
        h("button", { disabled: busy }, "Lưu cổng AI"),
        btn("Đóng", () => setGateway(null)),
      ),
    h(
      "div",
      { className: "cms-layout" },
      h(
        "aside",
        { className: "panel cms-sidebar" },
        h(
          "div",
          { className: "cms-toolbar" },
          ...["post", "page"].map((k) =>
            btn(
              k === "post" ? "Bài viết" : "Trang",
              () => {
                if (mayLeave()) {
                  setKind(k);
                  select(null);
                }
              },
              { key: k, "aria-pressed": kind === k },
            ),
          ),
        ),
        btn(
          kind === "post" ? "+ Bài viết mới" : "+ Trang mới",
          () => {
            if (mayLeave()) select(blank(kind));
          },
          { className: "primary" },
        ),
        field("Tìm nội dung", search, setSearch),
        h(
          "select",
          {
            "aria-label": "Lọc trạng thái",
            value: status,
            onChange: (e) => setStatus(e.target.value),
          },
          h("option", { value: "" }, "Đang sử dụng"),
          ...Object.entries(STATUS).map(([key, title]) =>
            h("option", { key, value: key }, title),
          ),
        ),
        h(
          "div",
          { className: "cms-records" },
          ...filtered.map((r) =>
            h(
              "button",
              {
                key: r.id,
                type: "button",
                disabled: busy,
                className: doc?.id === r.id ? "selected" : "",
                onClick: () => {
                  if (mayLeave()) select(r);
                },
              },
              h("strong", null, r.title),
              h(
                "small",
                null,
                STATUS[r.status],
                r.has_unpublished_changes ? " · Có bản sửa" : "",
                settings?.homepage_id === r.id ? " · Trang chủ" : "",
              ),
            ),
          ),
          !filtered.length &&
            h("p", null, "Chưa có nội dung. Tạo bản nháp đầu tiên ở trên."),
        ),
        h(
          "a",
          { href: "/news", target: "_blank", rel: "noreferrer" },
          "Xem trang tin tức ↗",
        ),
      ),
      doc
        ? h(
            "div",
            { className: "cms-editor panel" },
            h(
              "div",
              { className: "cms-toolbar" },
              h(
                "strong",
                null,
                doc.kind === "post" ? "Biên tập bài viết" : "Thiết kế trang",
              ),
              h(
                "small",
                null,
                dirty
                  ? "Chưa lưu"
                  : `${STATUS[doc.status] || "Bản nháp"} · v${doc.version || 1}`,
              ),
            ),
            h(
              "fieldset",
              { disabled: busy || doc.status === "trash" },
              field("Tiêu đề", doc.title, (v) => update("title", v), false, {
                maxLength: 250,
              }),
              field(
                "Đường dẫn (để trống để tạo từ tiêu đề)",
                doc.slug,
                (v) => update("slug", v),
                false,
                {
                  disabled: busy || doc.status === "published",
                  placeholder: "gioi-thieu",
                },
              ),
              field("Tóm tắt", doc.excerpt, (v) => update("excerpt", v), true, {
                rows: 2,
              }),
              h(
                "details",
                { className: "cms-ai", open: true },
                h("summary", null, "✦ Trợ lý viết & tạo trang AI"),
                h(
                  "p",
                  null,
                  settings?.gateway.configured
                    ? `Model: ${settings.gateway.model}`
                    : "Chưa kết nối AI. Mở Cấu hình AI để nhập cổng và khóa API.",
                ),
                field("Lệnh cho AI", instruction, setInstruction, true, {
                  placeholder:
                    doc.kind === "page"
                      ? "Tạo trang chủ gồm lời giới thiệu, dịch vụ, quy trình 4 bước và nút xem tin tức…"
                      : "Viết bài tin tức từ tài liệu bên dưới, giọng rõ ràng, có tiêu đề và tóm tắt…",
                  rows: 3,
                }),
                field(
                  "Tài liệu và dữ kiện tham khảo",
                  references,
                  setReferences,
                  true,
                  {
                    rows: 4,
                    placeholder:
                      "Dán thông tin đã xác minh. AI không tự đọc các URL nguồn.",
                  },
                ),
                btn("Tạo đề xuất bằng AI", generate, {
                  disabled: busy || !settings?.gateway.configured,
                }),
                tokens > 0 &&
                  h(
                    "small",
                    { role: "status" },
                    busy
                      ? ` Đang nhận bản thảo… ${tokens.toLocaleString()} ký tự`
                      : ` Đã nhận ${tokens.toLocaleString()} ký tự`,
                  ),
              ),
              h(
                "div",
                { className: "cms-toolbar" },
                h("h3", null, "Các khối nội dung"),
                btn(preview ? "Sửa khối" : "Xem bố cục", () =>
                  setPreview(!preview),
                ),
              ),
              preview
                ? h(DraftPreview, { doc })
                : h(
                    "div",
                    { className: "cms-blocks" },
                    ...doc.blocks.map((b, i) =>
                      h(
                        "section",
                        { key: i, className: "cms-block" },
                        h(
                          "div",
                          { className: "cms-toolbar" },
                          h("strong", null, `${i + 1}. ${TYPES[b.type]}`),
                          btn(
                            "↑",
                            () => {
                              const blocks = [...doc.blocks];
                              [blocks[i - 1], blocks[i]] = [
                                blocks[i],
                                blocks[i - 1],
                              ];
                              update("blocks", blocks);
                            },
                            {
                              disabled: busy || i === 0,
                              "aria-label": `Di chuyển khối ${i + 1} lên`,
                            },
                          ),
                          btn(
                            "↓",
                            () => {
                              const blocks = [...doc.blocks];
                              [blocks[i + 1], blocks[i]] = [
                                blocks[i],
                                blocks[i + 1],
                              ];
                              update("blocks", blocks);
                            },
                            {
                              disabled: busy || i === doc.blocks.length - 1,
                              "aria-label": `Di chuyển khối ${i + 1} xuống`,
                            },
                          ),
                          btn(
                            "Xóa",
                            () =>
                              update(
                                "blocks",
                                doc.blocks.filter((_, n) => n !== i),
                              ),
                            { "aria-label": `Xóa khối ${i + 1}` },
                          ),
                        ),
                        !["divider", "list"].includes(b.type) &&
                          field(
                            `Nội dung khối ${i + 1}`,
                            b.text,
                            (v) => updateBlock(i, { text: v }),
                            true,
                            { rows: b.type === "paragraph" ? 5 : 2 },
                          ),
                        b.type === "hero" &&
                          field(
                            "Mô tả mở đầu",
                            b.detail,
                            (v) => updateBlock(i, { detail: v }),
                            true,
                          ),
                        b.type === "list" &&
                          field(
                            "Mỗi mục một dòng",
                            (b.items || []).join("\n"),
                            (v) => updateBlock(i, { items: v.split("\n") }),
                            true,
                          ),
                        b.type === "button" &&
                          field(
                            "Liên kết HTTPS hoặc đường dẫn /",
                            b.href,
                            (v) => updateBlock(i, { href: v }),
                          ),
                        b.type === "image" &&
                          h(
                            React.Fragment,
                            null,
                            h(
                              "select",
                              {
                                "aria-label": "Chọn ảnh",
                                value: b.src,
                                onChange: (e) =>
                                  updateBlock(i, { src: e.target.value }),
                              },
                              h("option", { value: "" }, "Chọn từ thư viện"),
                              ...media.map((m) =>
                                h(
                                  "option",
                                  {
                                    key: m.filename,
                                    value: `/media/${m.filename}`,
                                  },
                                  `${m.width}×${m.height} · ${m.filename.slice(0, 8)}`,
                                ),
                              ),
                            ),
                            field("Mô tả ảnh cho người đọc", b.alt, (v) =>
                              updateBlock(i, { alt: v }),
                            ),
                          ),
                      ),
                    ),
                  ),
              h(
                "div",
                { className: "cms-toolbar" },
                h(
                  "select",
                  {
                    "aria-label": "Thêm khối",
                    value: "",
                    onChange: (e) => {
                      if (e.target.value) {
                        update("blocks", [
                          ...doc.blocks,
                          {
                            type: e.target.value,
                            text: "",
                            ...(e.target.value === "button"
                              ? { href: "/news" }
                              : {}),
                          },
                        ]);
                        setPreview(false);
                      }
                    },
                  },
                  h("option", { value: "" }, "+ Thêm khối"),
                  ...Object.entries(TYPES).map(([key, name]) =>
                    h("option", { key, value: key }, name),
                  ),
                ),
                h(
                  "label",
                  { className: "cms-upload" },
                  "Tải ảnh (tối đa 5 MB)",
                  h("input", {
                    type: "file",
                    accept: "image/jpeg,image/png,image/webp",
                    onChange: (e) => {
                      const file = e.target.files[0];
                      e.target.value = "";
                      run(() => upload(file));
                    },
                  }),
                ),
              ),
              h(
                "details",
                null,
                h("summary", null, "Phân loại, nguồn & SEO"),
                field(
                  "Chuyên mục (mỗi dòng một mục)",
                  doc.categories.join("\n"),
                  (v) => update("categories", v.split("\n")),
                  true,
                ),
                field(
                  "Thẻ (mỗi dòng một thẻ)",
                  doc.tags.join("\n"),
                  (v) => update("tags", v.split("\n")),
                  true,
                ),
                field(
                  "Nguồn HTTPS (mỗi dòng một URL)",
                  doc.sources.join("\n"),
                  (v) => update("sources", v.split("\n")),
                  true,
                ),
                field("Tiêu đề SEO", doc.seo_title, (v) =>
                  update("seo_title", v),
                ),
                field(
                  "Mô tả SEO",
                  doc.seo_description,
                  (v) => update("seo_description", v),
                  true,
                ),
              ),
              h(
                "div",
                { className: "cms-toolbar cms-actions" },
                btn("Lưu bản nháp", save, { className: "primary" }),
                doc.id &&
                  btn(
                    "Xuất bản phiên bản đã lưu",
                    () => transition("publish"),
                    { disabled: busy || dirty },
                  ),
                doc.id &&
                  h(
                    "a",
                    {
                      href: `/api/cms/content/${doc.id}/preview`,
                      target: "_blank",
                      rel: "noreferrer",
                    },
                    "Xem bản đã lưu ↗",
                  ),
              ),
            ),
            doc.id &&
              h(
                "div",
                { className: "cms-toolbar" },
                doc.status === "published" &&
                  h(
                    "a",
                    {
                      href: `/${doc.kind === "post" ? "news" : "pages"}/${doc.slug}`,
                      target: "_blank",
                      rel: "noreferrer",
                    },
                    "Mở trang công khai ↗",
                  ),
                doc.status === "published" &&
                  btn("Gỡ xuất bản", () => transition("unpublish")),
                doc.status === "published" &&
                  doc.kind === "page" &&
                  btn(
                    settings?.homepage_id === doc.id
                      ? "Bỏ làm trang chủ"
                      : "Đặt làm trang chủ",
                    async () => {
                      await post(
                        "/cms/homepage",
                        {
                          content_id:
                            settings?.homepage_id === doc.id ? null : doc.id,
                        },
                        "PUT",
                      );
                      await load();
                      setNotice("Đã cập nhật trang chủ công khai.");
                    },
                  ),
                btn(
                  doc.status === "trash"
                    ? "Khôi phục bản nháp"
                    : "Chuyển vào thùng rác",
                  () =>
                    transition(doc.status === "trash" ? "restore" : "trash"),
                ),
                btn("Lịch sử phiên bản", async () =>
                  setRevisions(await api(`/cms/content/${doc.id}/revisions`)),
                ),
                btn("Tải lại bản đã lưu", async () => {
                  if (mayLeave()) select(await api(`/cms/content/${doc.id}`));
                }),
              ),
            revisions.length > 0 &&
              h(
                "div",
                { className: "cms-revisions" },
                h("h3", null, "Khôi phục chỉ thay bản nháp"),
                ...revisions.map((r) =>
                  h(
                    "div",
                    { key: r.version, className: "cms-toolbar" },
                    h(
                      "span",
                      null,
                      `v${r.version} · ${new Date(r.created * 1000).toLocaleString("vi-VN")} · ${r.action}`,
                    ),
                    btn(
                      "Khôi phục",
                      async () => {
                        if (dirty)
                          throw new Error(
                            "Lưu hoặc tải lại bản đang sửa trước khi khôi phục.",
                          );
                        select(
                          await post(
                            `/cms/content/${doc.id}/restore-revision`,
                            {
                              revision: r.version,
                              expected_version: doc.version,
                            },
                          ),
                        );
                        await load();
                      },
                      { disabled: busy || doc.status === "trash" },
                    ),
                  ),
                ),
              ),
          )
        : h(
            "div",
            { className: "panel cms-empty" },
            h("h3", null, "Không gian biên tập của anh"),
            h(
              "p",
              null,
              "Chọn một bài viết hoặc tạo trang mới. AI giúp soạn nội dung và bố cục; anh kiểm soát thời điểm xuất bản.",
            ),
            h(
              "p",
              null,
              "Trang chủ: ",
              settings?.homepage_id
                ? "Đã chọn trang công khai"
                : "Chưa chọn · đang mở khu quản trị",
            ),
          ),
    ),
    busy &&
      controller.current &&
      btn("Dừng tạo AI", () => controller.current.abort(), { disabled: false }),
  );
}
