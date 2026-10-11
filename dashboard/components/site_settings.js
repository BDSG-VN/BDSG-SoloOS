import React, { useEffect, useState } from "react";
import { useUnsaved } from "./use_unsaved.js";
const h = React.createElement;
export default function SiteSettings({
  api,
  post,
  onDraft,
  disabled,
  onDirtyChange,
}) {
  const [saved, setSaved] = useState("");
  const [site, setSite] = useState(null),
    [themes, setThemes] = useState([]),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
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
            h("h3", null, t.title),
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
