import React, { useEffect, useRef, useState } from "react";
import { useUnsaved } from "./use_unsaved.js";
const h = React.createElement;
export default function SiteSettings({
  api,
  post,
  onDraft,
  disabled,
  onDirtyChange,
}) {
  const [site, setSite] = useState(null),
    [themes, setThemes] = useState([]),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState("");
  const [previews, setPreviews] = useState({});
  const dialogRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all(themes.map(async t => [t.id, (await api(`/cms/themes/${t.id}/preview`)).html]))
      .then(entries => { if (active) setPreviews(Object.fromEntries(entries)); })
      .catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [themes]);
  useEffect(() => {
    if (!preview) return;
    dialogRef.current?.showModal();
    const close = e => { if (e.key === "Escape") setPreview(null); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [preview]);
  useEffect(() => {
    Promise.all([api("/cms/site"), api("/cms/themes")])
      .then(([s, t]) => {
        setSite(s);
        setSaved(JSON.stringify(s));
        setThemes(t);
      })
      .catch((e) => setError(e.message));
  }, []);
  async function run(fn) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  useUnsaved(Boolean(site && JSON.stringify(site) !== saved), onDirtyChange);
  if (!site) return null;
  return h(
    "details",
    { className: "card" },
    h("summary", null, "Giao diện & thông tin website"),
    h(
      "p",
      null,
      "Trang chủ dành cho khách. Quản trị tại /admin. Mẫu được tạo thành bản nháp để bạn chỉnh sửa và xuất bản.",
    ),
    error && h("p", { role: "alert" }, error),
    notice && h("p", { role: "status" }, notice),
    preview && h("dialog", {ref: dialogRef, onCancel: () => setPreview(null), className: "theme-preview-dialog", "aria-label": `Xem trước ${preview.title}`},
      h("div", {className: "theme-preview-toolbar"},
        h("strong", null, preview.title),
        h("button", {type: "button", onClick: () => setMobile(false), "aria-pressed": !mobile}, "Máy tính"),
        h("button", {type: "button", onClick: () => setMobile(true), "aria-pressed": mobile}, "Điện thoại"),
        h("button", {type: "button", onClick: () => setPreview(null)}, "Đóng xem trước")),
      h("p", null, "Bản mẫu dùng nội dung minh họa. Xem trước không thay đổi website."),
      h("div", {className: "theme-preview-stage"}, h("iframe", {title: `Bản xem trước ${preview.title}`, srcDoc: previews[preview.id], sandbox: "", style: {width: mobile ? "390px" : "100%"}}))),
    h(
      "fieldset",
      { disabled: disabled || busy },
      h(
        "label",
        null,
        "Tên website",
        h("input", {
          value: site.title,
          onChange: (e) => setSite({ ...site, title: e.target.value }),
          maxLength: 120,
        }),
      ),
      h(
        "label",
        null,
        "Lời giới thiệu",
        h("input", {
          value: site.tagline,
          onChange: (e) => setSite({ ...site, tagline: e.target.value }),
          maxLength: 300,
        }),
      ),
      h(
        "label",
        null,
        h("input", {
          type: "checkbox",
          checked: site.registration,
          onChange: (e) => setSite({ ...site, registration: e.target.checked }),
        }),
        " Cho phép khách đăng ký",
      ),
      h(
        "div",
        { className: "site-themes" },
        ...themes.map((t) =>
          h(
            "article",
            {
              key: t.id,
              className: "card",
              style: { borderTop: `8px solid ${t.accent}` },
            },
            h("button", {type: "button", className: "theme-thumbnail", onClick: () => setPreview(t), "aria-label": `Xem trước ${t.title}`},
              previews[t.id] ? h("iframe", {title: `Hình thu nhỏ ${t.title}`, srcDoc: previews[t.id], sandbox: "", tabIndex: -1, loading: "lazy"}) : "Đang tải hình xem trước…"),
            h("h3", null, t.title),
            h("button", {type: "button", onClick: () => setPreview(t)}, "Xem trước"),
            h("p", null, t.headline),
            h(
              "label",
              null,
              h("input", {
                type: "radio",
                name: "site-theme",
                checked: site.theme === t.id,
                onChange: () => setSite({ ...site, theme: t.id }),
              }),
              " Chọn màu giao diện",
            ),
            h(
              "button",
              {
                type: "button",
                onClick: () =>
                  run(async () => {
                    if (await onDraft(t.id))
                      setNotice(
                        "Đã tạo trang nháp. Hãy chỉnh nội dung rồi xuất bản và chọn làm trang chủ.",
                      );
                  }),
              },
              "Tạo trang từ mẫu",
            ),
          ),
        ),
      ),
      h(
        "button",
        {
          type: "button",
          onClick: () =>
            run(async () => {
              const result = await post("/cms/site", site, "PUT");
              setSite(result);
              setSaved(JSON.stringify(result));
              setNotice("Đã lưu thông tin website.");
            }),
        },
        "Lưu thông tin website",
      ),
    ),
  );
}
