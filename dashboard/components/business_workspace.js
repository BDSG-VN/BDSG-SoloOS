import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, { useEffect, useState } from "react";
const h = React.createElement;
const TABS = {
  get channels() { return uiText("Đa kênh"); },
  get inbox() { return uiText("Hộp thư"); },
  customers: "Customer 360",
  campaigns: "Marketing",
  get sales() { return uiText("Bán hàng"); },
  get tickets() { return uiText("CSKH / Ticket"); },
  get ledger() { return uiText("Thu chi"); },
  get staff() { return uiText("Nhân sự"); },
  analytics: "Analytics",
};
const money = (n) =>
  new Intl.NumberFormat(localeTag(), { style: "currency", currency: "VND" }).format(
    n || 0,
  );
export default function BusinessWorkspace({
  api,
  post,
  onPending,
  onConfigure,
  onAskAI,
}) {
  const [tab, setTab] = useState("channels"),
    [data, setData] = useState(null),
    [customers, setCustomers] = useState([]),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [detail, setDetail] = useState(null);
  const load = async () => {
    setData(await api("/business/" + tab));
    setCustomers(await api("/business/customers"));
  };
  useEffect(() => {
    let active = true;
    setData(null);
    setDetail(null);
    setError("");
    Promise.all([api("/business/" + tab), api("/business/customers")])
      .then(([d, c]) => {
        if (active) {
          setData(d);
          setCustomers(c);
        }
      })
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [tab]);
  const run = async (fn) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await fn();
      await load();
      await onPending();
      if (r?.status === "requires_confirmation")
        setNotice(uiText("Đã chuyển yêu cầu sang Phê duyệt."));
      return r;
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const button = (label, fn) =>
    h(
      "button",
      { type: "button", disabled: busy, onClick: () => run(fn) },
      label,
    );
  const field = (name, label, type = "text", required = true) =>
    h(
      "label",
      { key: name },
      label,
      h("input", {
        name,
        type,
        required,
        min: type === "number" ? 0 : undefined,
      }),
    );
  const select = (name, label, options) =>
    h(
      "label",
      null,
      label,
      h(
        "select",
        { name, required: true, "aria-label": label },
        ...options.map(([value, text]) =>
          h("option", { key: value, value }, text),
        ),
      ),
    );
  const customerSelect = () =>
    select(
      "customer_id",
      uiText("Khách hàng"),
      customers.map((c) => [c.id, c.name]),
    );
  const channelSelect = () =>
    select(
      "channel",
      uiText("Kênh"),
      Object.entries({
        zalo: "Zalo OA",
        facebook: "Facebook",
        instagram: "Instagram",
        tiktok: "TikTok",
        google_ads: "Google Ads",
        email: "Email",
        hotline: "Hotline",
        website: "Website",
        sms: "SMS / ZNS",
      }),
    );
  const form = (title, fields, submit) =>
    h(
      "form",
      {
        className: "panel business-form",
        onSubmit: (e) => {
          e.preventDefault();
          const values = Object.fromEntries(new FormData(e.currentTarget));
          run(() => submit(values));
        },
      },
      h("h3", null, title),
      ...fields,
      h("button", { className: "primary", disabled: busy }, uiText("Lưu")),
    );
  const cards = (rows, render) =>
    h(
      "div",
      { className: "business-grid" },
      ...rows.map((r) =>
        h("article", { className: "panel", key: r.id }, ...render(r)),
      ),
      !rows.length && h("p", { className: "muted" }, uiText("Chưa có dữ liệu.")),
    );
  let content = null;
  if (data && tab === "channels")
    content = h(
      React.Fragment,
      null,
      h(
        "p",
        { className: "muted" },
        uiText("MCP được kiểm tra tại Hub. Kiểm tra công cụ thành công chưa xác nhận quyền truy cập tài khoản. Cần OAuth/API và máy chủ MCP phù hợp trước khi sử dụng."),
      ),
      cards(data.channels, (c) => {
        const official = data.official_catalog.find((o) => o.id === c.id);
        return [
          h("h3", null, c.name),
          h("p", null, c.capabilities),
          h("span", { className: "badge" }, c.status),
          h("p", null, official?.scope),
          h("p", { className: "muted" }, official?.note),
          official?.source &&
            h(
              "a",
              { href: official.source, target: "_blank", rel: "noreferrer" },
              uiText("Tài liệu chính thức ↗"),
            ),
          official?.template &&
            button(uiText("Mở mẫu MCP"), () => onConfigure(official.template)),
          c.connector &&
            button(uiText("Kiểm tra MCP"), async () => {
              const r = await post("/business/channels/" + c.id + "/test", {});
              setNotice(
                r.mcp_reachable
                  ? uiText("MCP phản hồi; cần kiểm tra tài khoản riêng.")
                  : uiText("Công cụ chưa khớp cấu hình."),
              );
            }),
          c.read_tool &&
            button(uiText("Đọc qua MCP"), async () => {
              const r = await post("/business/channels/" + c.id + "/read", {
                arguments: {},
              });
              setNotice(JSON.stringify(r));
            }),
        ];
      }),
      form(
        uiText("Ánh xạ kênh → MCP"),
        [
          channelSelect(),
          field("connector", uiText("ID connector MCP đã lưu")),
          field("read_tool", uiText("Công cụ đọc"), "text", false),
          field("send_tool", uiText("Công cụ gửi"), "text", false),
          h(
            "label",
            null,
            uiText("Mẫu JSON tham số gửi ($recipient, $content)"),
            h("textarea", {
              name: "template",
              defaultValue: '{"recipient":"$recipient","content":"$content"}',
            }),
          ),
          field(
            "webhook_secret",
            uiText("Khóa webhook bridge ≥32 ký tự"),
            "password",
            false,
          ),
        ],
        (v) =>
          post(
            "/business/channels/" + v.channel,
            {
              connector: v.connector,
              read_tool: v.read_tool || null,
              send_tool: v.send_tool || null,
              argument_template: JSON.parse(v.template),
              enabled: true,
              webhook_secret: v.webhook_secret || null,
            },
            "PUT",
          ),
      ),
    );
  if (data && tab === "customers")
    content = h(
      React.Fragment,
      null,
      form(
        uiText("Tạo khách hàng"),
        [
          field("name", uiText("Tên khách hàng")),
          field("email", "Email", "email", false),
          field("phone", uiText("Điện thoại"), "text", false),
        ],
        (v) => post("/business/customers", v),
      ),
      cards(data, (c) => [
        h("h3", null, c.name),
        h("p", null, [c.email, c.phone].filter(Boolean).join(" · ")),
        h(
          "p",
          null,
          uiText("{0} · {1} tin nhắn · {2}", [c.stage, c.message_count, money(c.revenue)]),
        ),
        button(uiText("Hồ sơ 360"), async () =>
          setDetail(await api("/business/customers/" + c.id)),
        ),
      ]),
      detail &&
        h(
          "section",
          { className: "panel" },
          h("h3", null, detail.name),
          h(
            "p",
            null,
            uiText("{0} tin nhắn · {1} báo giá/đơn · {2} ticket", [detail.messages.length, detail.sales.length, detail.tickets.length]),
          ),
          ...detail.messages.map((m) =>
            h("p", { key: m.id }, `${m.channel}: ${m.content}`),
          ),
          form(
            uiText("Cập nhật vòng đời"),
            [
              select("stage", uiText("Giai đoạn"), [
                ["lead", "Lead"],
                ["prospect", uiText("Tiềm năng")],
                ["customer", uiText("Khách hàng")],
                ["loyal", uiText("Trung thành")],
              ]),
              field("notes", uiText("Ghi chú"), "text", false),
            ],
            (v) => post("/business/customers/" + detail.id, v, "PATCH"),
          ),
          form(
            uiText("Gắn định danh kênh"),
            [channelSelect(), field("external_id", uiText("ID khách trên nền tảng"))],
            (v) => post("/business/customers/" + detail.id + "/identities", v),
          ),
        ),
    );
  if (data && tab === "inbox")
    content = h(
      React.Fragment,
      null,
      form(
        uiText("Nhập tin nhắn thủ công"),
        [
          channelSelect(),
          field("external_id", uiText("ID tin nhắn")),
          field("sender_id", uiText("ID người gửi")),
          field("sender_name", uiText("Tên người gửi")),
          field("content", uiText("Nội dung")),
        ],
        ({ channel, ...v }) =>
          post("/business/inbox/" + channel + "/import", v),
      ),
      form(
        uiText("Soạn phản hồi"),
        [
          channelSelect(),
          field("recipient", uiText("ID người nhận")),
          field("content", uiText("Nội dung")),
        ],
        (v) => post("/business/inbox/drafts", v),
      ),
      cards(data, (m) => [
        h("h3", null, m.customer_name || m.sender_id),
        h(
          "p",
          { className: "muted" },
          `${m.channel} · ${m.direction} · ${m.status}`,
        ),
        h("p", null, m.content),
        m.status === "draft" &&
          button(uiText("Gửi qua MCP"), () =>
            post("/business/inbox/" + m.id + "/send", {}),
          ),
      ]),
    );
  if (data && tab === "campaigns")
    content = h(
      React.Fragment,
      null,
      form(
        uiText("Chiến dịch đa kênh"),
        [
          field("title", uiText("Tên chiến dịch")),
          field("objective", uiText("Mục tiêu")),
          field("channels", uiText("Kênh, phân cách dấu phẩy")),
          field("budget", uiText("Ngân sách VND"), "number"),
        ],
        (v) =>
          post("/business/campaigns", {
            ...v,
            channels: v.channels.split(",").map((s) => s.trim()),
            budget: Number(v.budget),
          }),
      ),
      cards(data, (c) => [
        h("h3", null, c.title),
        h("p", null, c.objective),
        h(
          "p",
          null,
          `${c.channels.join(" · ")} / ${money(c.budget)} / ${c.status}`,
        ),
        button(uiText("Lập kế hoạch bằng AI"), () =>
          onAskAI(
            uiText("Lập kế hoạch cho chiến dịch {0}. Mục tiêu: {1}. Kênh: {2}. Ngân sách: {3} VND. Tạo lịch triển khai, nội dung và chỉ số đo lường.", [c.title, c.objective, c.channels.join(", "), c.budget]),
          ),
        ),
        form(
          uiText("Lưu kế hoạch"),
          [
            h(
              "label",
              null,
              uiText("Kế hoạch"),
              h("textarea", { name: "plan", defaultValue: c.plan }),
            ),
            select("status", uiText("Trạng thái"), [
              ["draft", uiText("Nháp")],
              ["planned", uiText("Đã lập kế hoạch")],
              ["done", uiText("Hoàn thành")],
            ]),
          ],
          (v) => post("/business/campaigns/" + c.id, v, "PATCH"),
        ),
      ]),
    );
  if (data && tab === "sales")
    content = h(
      React.Fragment,
      null,
      form(
        uiText("Tạo báo giá"),
        [
          customerSelect(),
          field("title", uiText("Tên báo giá")),
          field("item", uiText("Sản phẩm / Dịch vụ")),
          field("quantity", uiText("Số lượng"), "number"),
          field("unit_price", uiText("Đơn giá VND"), "number"),
        ],
        (v) =>
          post("/business/sales", {
            customer_id: v.customer_id,
            title: v.title,
            items: [
              {
                name: v.item,
                quantity: Number(v.quantity),
                unit_price: Number(v.unit_price),
              },
            ],
          }),
      ),
      cards(data, (s) => [
        h("h3", null, s.title),
        h("p", null, s.customer_name),
        h("strong", null, money(s.total)),
        h("p", null, s.status),
        s.status === "quote" &&
          button(uiText("Chuyển thành đơn"), () =>
            post("/business/sales/" + s.id, { status: "order" }, "PATCH"),
          ),
        s.status === "order" &&
          button(uiText("Ghi nhận đã thu tiền"), () =>
            post("/business/sales/" + s.id, { status: "paid" }, "PATCH"),
          ),
      ]),
    );
  if (data && tab === "tickets")
    content = h(
      React.Fragment,
      null,
      form(
        uiText("Tạo ticket hỗ trợ"),
        [
          field("title", uiText("Tiêu đề")),
          field("description", uiText("Mô tả"), "text", false),
          select("priority", uiText("Ưu tiên"), [
            ["normal", uiText("Thường")],
            ["high", uiText("Cao")],
          ]),
        ],
        (v) => post("/business/tickets", v),
      ),
      cards(data, (t) => [
        h("h3", null, t.title),
        h("p", null, t.description),
        h("p", null, t.priority + " · " + t.status),
        t.status !== "resolved" &&
          button(uiText("Giải quyết"), () =>
            post("/business/tickets/" + t.id, { status: "resolved" }, "PATCH"),
          ),
      ]),
    );
  if (data && tab === "ledger")
    content = h(
      React.Fragment,
      null,
      h(
        "p",
        { className: "muted" },
        uiText("Sổ thu chi nội bộ VND. Ghi nhận thanh toán thủ công; chưa đối soát ngân hàng hoặc phát hành hóa đơn thuế."),
      ),
      form(
        "Ghi thu / chi",
        [
          select("direction", uiText("Loại"), [
            ["income", "Thu"],
            ["expense", "Chi"],
          ]),
          field("amount", uiText("Số tiền VND"), "number"),
          field("description", uiText("Diễn giải")),
        ],
        (v) => post("/business/ledger", { ...v, amount: Number(v.amount) }),
      ),
      cards(data, (r) => [
        h("h3", null, r.description),
        h(
          "strong",
          null,
          (r.direction === "income" ? "+" : "−") + money(r.amount),
        ),
      ]),
    );
  if (data && tab === "staff")
    content = h(
      React.Fragment,
      null,
      form(
        uiText("Thành viên / Cộng tác viên"),
        [
          field("name", uiText("Họ tên")),
          field("role", uiText("Vai trò")),
          field("email", "Email", "email", false),
        ],
        (v) => post("/business/staff", v),
      ),
      cards(data, (s) => [
        h("h3", null, s.name),
        h("p", null, s.role),
        h("p", null, s.email),
        h("p", null, s.status),
        button(s.status === "active" ? uiText("Tạm nghỉ") : uiText("Kích hoạt"), () =>
          post(
            "/business/staff/" + s.id,
            { status: s.status === "active" ? "leave" : "active" },
            "PATCH",
          ),
        ),
      ]),
    );
  if (data && tab === "analytics")
    content = h(
      React.Fragment,
      null,
      h(
        "div",
        { className: "business-grid" },
        ...Object.entries({
          customers: uiText("Khách hàng"),
          paid_orders: uiText("Đơn đã thu"),
          open_tickets: uiText("Ticket đang mở"),
          income: uiText("Tổng thu"),
          expense: uiText("Tổng chi"),
          balance: uiText("Chênh lệch thu chi"),
        }).map(([key, label]) =>
          h(
            "article",
            { className: "panel", key },
            h("p", null, label),
            h(
              "h2",
              null,
              ["income", "expense", "balance"].includes(key)
                ? money(data[key])
                : data[key],
            ),
          ),
        ),
      ),
      h(
        "section",
        { className: "panel" },
        h("h3", null, uiText("Tin nhắn theo kênh")),
        ...data.channels.map((c) =>
          h("p", { key: c.channel }, `${c.channel}: ${c.messages}`),
        ),
        h("h3", null, uiText("Vòng đời khách hàng")),
        ...data.stages.map((s) =>
          h("p", { key: s.stage }, `${s.stage}: ${s.count}`),
        ),
      ),
    );
  return h(
    "section",
    null,
    h("span", { className: "eyebrow" }, "ONE PERSON COMPANY"),
    h("h1", null, uiText("Điều hành doanh nghiệp")),
    h(
      "div",
      { className: "business-tabs" },
      ...Object.entries(TABS).map(([id, label]) =>
        h(
          "button",
          {
            key: id,
            className: tab === id ? "primary" : "",
            disabled: busy,
            onClick: () => {
              if (id === tab) return;
              setData(null);
              setDetail(null);
              setTab(id);
            },
          },
          label,
        ),
      ),
    ),
    error && h("p", { role: "alert", className: "error" }, error),
    notice && h("p", { role: "status", className: "notice" }, notice),
    !data && h("p", null, uiText("Đang tải…")),
    content,
  );
}
