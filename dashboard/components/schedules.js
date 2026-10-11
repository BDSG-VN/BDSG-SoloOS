import React, { useState } from "react";
const h = React.createElement;
function localInput(value) {
  if (!value) return "";
  const d = new Date(value);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
const initial = {
  workflow_id: "",
  kind: "interval",
  interval_minutes: 60,
  cron: "0 9 * * 1-5",
  timezone: "Asia/Ho_Chi_Minh",
  at: null,
  enabled: false,
  skip_overlap: true,
};
export default function Schedules({ data, api, post, onSaved }) {
  const [draft, setDraft] = useState(initial),
    [id, setId] = useState(null),
    [times, setTimes] = useState([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const update = (patch) => {
    setDraft({ ...draft, ...patch });
    setTimes([]);
  };
  async function run(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function edit(s) {
    const { id, next_run, ...body } = s;
    setDraft({ ...initial, ...body });
    setId(id);
    setTimes([]);
  }
  const display = (value, zone) =>
    new Date(value * 1000).toLocaleString("vi-VN", {
      timeZone: zone || "Asia/Ho_Chi_Minh",
    });
  return h(
    "section",
    { className: "schedule-editor" },
    h("h3", null, "Lịch chạy"),
    h(
      "p",
      { className: "muted" },
      "Chạy một lần, theo khoảng thời gian hoặc lịch tuần/tháng. Lần bị bỏ lỡ không được chạy bù hàng loạt. Mỗi lượt vẫn tuân thủ quyền công cụ.",
    ),
    error && h("p", { role: "alert" }, error),
    h(
      "fieldset",
      { disabled: busy },
      h("legend", null, id ? "Sửa lịch" : "Lịch mới"),
      h(
        "label",
        null,
        "Quy trình của lịch",
        h(
          "select",
          {
            value: draft.workflow_id,
            onChange: (e) => update({ workflow_id: e.target.value }),
          },
          h("option", { value: "" }, "Chọn quy trình"),
          ...(data?.workflows || []).map((w) =>
            h(
              "option",
              { key: w.id, value: w.id, disabled: !w.enabled },
              w.title,
            ),
          ),
        ),
      ),
      h(
        "label",
        null,
        "Kiểu lịch",
        h(
          "select",
          {
            value: draft.kind,
            onChange: (e) => update({ kind: e.target.value }),
          },
          h("option", { value: "interval" }, "Lặp theo phút"),
          h("option", { value: "cron" }, "Lịch tuần / tháng"),
          h("option", { value: "once" }, "Một lần"),
        ),
      ),
      draft.kind === "interval" &&
        h(
          "label",
          null,
          "Khoảng cách (phút)",
          h("input", {
            type: "number",
            min: 15,
            max: 525600,
            value: draft.interval_minutes,
            onChange: (e) =>
              update({ interval_minutes: Number(e.target.value) }),
          }),
        ),
      draft.kind === "cron" &&
        h(
          React.Fragment,
          null,
          h(
            "label",
            null,
            "Lịch mẫu",
            h(
              "select",
              { value: "", onChange: (e) => update({ cron: e.target.value }) },
              h("option", { value: "" }, "Chọn nhanh"),
              h(
                "option",
                { value: "0 9 * * 1-5" },
                "9 giờ sáng các ngày làm việc",
              ),
              h("option", { value: "0 18 * * *" }, "18 giờ mỗi ngày"),
              h("option", { value: "0 9 1 * *" }, "9 giờ ngày đầu tháng"),
            ),
          ),
          h(
            "label",
            null,
            "Biểu thức cron (5 trường)",
            h("input", {
              value: draft.cron,
              onChange: (e) => update({ cron: e.target.value }),
            }),
          ),
          h(
            "label",
            null,
            "Múi giờ",
            h("input", {
              value: draft.timezone,
              onChange: (e) => update({ timezone: e.target.value }),
              placeholder: "Asia/Ho_Chi_Minh",
            }),
          ),
        ),
      draft.kind === "once" &&
        h(
          "label",
          null,
          "Thời điểm — theo giờ trên thiết bị này",
          h("input", {
            type: "datetime-local",
            value: localInput(draft.at),
            onChange: (e) =>
              update({
                at: e.target.value
                  ? new Date(e.target.value).toISOString()
                  : null,
              }),
          }),
          draft.at && h("small", null, new Date(draft.at).toLocaleString()),
        ),
      h(
        "label",
        null,
        h("input", {
          type: "checkbox",
          checked: draft.skip_overlap,
          onChange: (e) => update({ skip_overlap: e.target.checked }),
        }),
        " Bỏ qua lần mới nếu quy trình còn đang chạy hoặc chờ duyệt",
      ),
      h(
        "label",
        null,
        h("input", {
          type: "checkbox",
          checked: draft.enabled,
          onChange: (e) => update({ enabled: e.target.checked }),
        }),
        " Bật lịch này; các lượt có thể dùng hạn mức AI và công cụ đã cấp quyền",
      ),
      h(
        "div",
        { className: "button-row" },
        h(
          "button",
          {
            disabled: !draft.workflow_id,
            onClick: () =>
              run(async () =>
                setTimes(
                  (await post("/automation/schedules/preview", draft)).times,
                ),
              ),
          },
          "Xem trước lần chạy",
        ),
        h(
          "button",
          {
            disabled: !draft.workflow_id,
            onClick: () =>
              run(async () => {
                await post(
                  "/automation/schedules" + (id ? "/" + id : ""),
                  draft,
                  id ? "PUT" : "POST",
                );
                setDraft(initial);
                setId(null);
                setTimes([]);
                await onSaved();
              }),
          },
          "Lưu lịch",
        ),
        id &&
          h(
            "button",
            {
              onClick: () => {
                setId(null);
                setDraft(initial);
                setTimes([]);
              },
            },
            "Lịch mới",
          ),
      ),
    ),
    times.length > 0 &&
      h(
        "ol",
        { "aria-label": "Các lần chạy dự kiến" },
        ...times.map((t) =>
          h(
            "li",
            { key: t },
            display(t, draft.timezone) + " · " + draft.timezone,
          ),
        ),
      ),
    ...(data?.schedules || []).map((s) =>
      h(
        "article",
        { key: s.id, className: "schedule-row" },
        h(
          "strong",
          null,
          data.workflows.find((w) => w.id === s.workflow_id)?.title ||
            s.workflow_id,
        ),
        h(
          "p",
          null,
          (s.kind === "cron"
            ? s.cron
            : s.kind === "once"
              ? "Một lần"
              : `${s.interval_minutes} phút`) +
            " · " +
            (s.enabled ? "Đang bật" : "Tạm dừng"),
        ),
        s.enabled &&
          h("small", null, "Tiếp theo: " + display(s.next_run, s.timezone)),
        h(
          "div",
          { className: "button-row" },
          h("button", { disabled: busy, onClick: () => edit(s) }, "Sửa lịch"),
          h(
            "button",
            {
              disabled: busy,
              onClick: () =>
                run(async () => {
                  const { id, next_run, ...body } = s;
                  await post(
                    "/automation/schedules/" + id,
                    { ...body, enabled: !s.enabled },
                    "PUT",
                  );
                  await onSaved();
                }),
            },
            s.enabled ? "Tạm dừng" : "Bật lại",
          ),
          h(
            "button",
            {
              disabled: busy,
              onClick: () => {
                if (
                  window.confirm(
                    "Xóa lịch này? Các lượt chạy trước vẫn được giữ.",
                  )
                )
                  run(async () => {
                    await api("/automation/schedules/" + s.id, {
                      method: "DELETE",
                    });
                    await onSaved();
                  });
              },
            },
            "Xóa lịch",
          ),
        ),
      ),
    ),
  );
}
