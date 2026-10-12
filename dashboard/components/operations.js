import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useEffect, useState } from "react";
const h = React.createElement;
const statuses = {
  get queued() { return uiText("Đang chờ"); },
  get running() { return uiText("Đang chạy"); },
  get waiting() { return uiText("Chờ duyệt"); },
  get completed() { return uiText("Hoàn tất"); },
  get failed() { return uiText("Thất bại"); },
  get uncertain() { return uiText("Cần đối chiếu"); },
  get cancelled() { return uiText("Đã hủy"); },
};
export default function Operations({ api, post, onNavigate }) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [onlyUnread, setOnlyUnread] = useState(true);
  async function reload() {
    try {
      setData(await api("/operations"));
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    reload();
    const id = setInterval(() => {
      if (!document.hidden) reload();
    }, 15000);
    return () => clearInterval(id);
  }, []);
  async function acknowledge(ids) {
    try {
      await post("/operations/read", { ids });
      await reload();
    } catch (e) {
      setError(e.message);
    }
  }
  return h(
    "section",
    { className: "operations" },
    h(
      "div",
      { className: "section-title" },
      h(
        "div",
        null,
        h("h2", null, uiText("Trung tâm vận hành")),
        h(
          "p",
          { className: "muted" },
          uiText("Kết quả, việc cần xử lý và tình trạng cấu hình trong một màn hình."),
        ),
      ),
      h("button", { onClick: reload }, uiText("Làm mới")),
    ),
    error && h("p", { role: "alert" }, error),
    !data
      ? h("p", { role: "status" }, uiText("Đang tải trạng thái…"))
      : h(
          React.Fragment,
          null,
          h(
            "div",
            { className: "ops-cards" },
            ...data.checks.map((c) =>
              h(
                "button",
                {
                  key: c.name,
                  className: "panel ops-card",
                  onClick: () => onNavigate(c.page),
                },
                h("small", null, c.name),
                h("strong", null, c.detail),
                h(
                  "span",
                  { className: c.status === "ready" ? "muted" : "attention" },
                  c.status === "ready"
                    ? uiText("Xem chi tiết →")
                    : uiText("Thiết lập / kiểm tra →"),
                ),
              ),
            ),
          ),
          h(
            "section",
            { className: "panel" },
            h("h3", null, uiText("Tiến độ tự động hóa")),
            h("p", { className: "muted" }, data.window),
            h(
              "div",
              { className: "ops-counts" },
              ...Object.entries(data.runs).map(([key, count]) =>
                h(
                  "div",
                  { key },
                  h("strong", null, count),
                  h("span", null, statuses[key]),
                ),
              ),
            ),
          ),
          h(
            "section",
            { className: "panel" },
            h(
              "div",
              { className: "section-title" },
              h("h3", null, uiText("Hộp thông báo")),
              h(
                "a",
                { href: "/api/operations/export", download: true },
                uiText("Xuất báo cáo"),
              ),
            ),
            h(
              "label",
              null,
              h("input", {
                type: "checkbox",
                checked: onlyUnread,
                onChange: (e) => setOnlyUnread(e.target.checked),
              }),
              uiText(" Chỉ chưa đọc"),
            ),
            h(
              "button",
              {
                disabled: !data.notifications.some((n) => !n.read),
                onClick: () =>
                  acknowledge(
                    data.notifications.filter((n) => !n.read).map((n) => n.id),
                  ),
              },
              uiText("Đánh dấu tất cả đã đọc"),
            ),
            ...data.notifications
              .filter((n) => !onlyUnread || !n.read)
              .map((n) =>
                h(
                  "article",
                  { key: n.id, className: "notification-row" },
                  h(
                    "div",
                    null,
                    h("strong", null, n.title),
                    h("p", null, statuses[n.status]),
                    h(
                      "small",
                      { className: "muted" },
                      new Date(n.updated * 1000).toLocaleString(),
                    ),
                    n.error && h("p", null, n.error),
                  ),
                  h(
                    "div",
                    { className: "button-row" },
                    h(
                      "button",
                      {
                        onClick: () =>
                          onNavigate(
                            n.status === "waiting" ? "approvals" : "automation",
                          ),
                      },
                      uiText("Xử lý"),
                    ),
                    !n.read &&
                      h(
                        "button",
                        { onClick: () => acknowledge([n.id]) },
                        uiText("Đã đọc"),
                      ),
                  ),
                ),
              ),
            !data.notifications.some((n) => !onlyUnread || !n.read) &&
              h("p", { className: "empty" }, uiText("Không có thông báo cần xử lý.")),
          ),
        ),
  );
}
