import React, { useEffect, useState } from "react";
const h = React.createElement;
const TABS = {
  channels: "Đa kênh",
  inbox: "Hộp thư",
  customers: "Customer 360",
  campaigns: "Marketing",
  sales: "Bán hàng",
  tickets: "CSKH / Ticket",
  ledger: "Thu chi",
  staff: "Nhân sự",
  analytics: "Analytics",
};
const money = (n) =>
  new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(
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
        setNotice("Đã chuyển yêu cầu sang Phê duyệt.");
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
      "Khách hàng",
      customers.map((c) => [c.id, c.name]),
    );
  const channelSelect = () =>
    select(
      "channel",
      "Kênh",
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
      h("button", { className: "primary", disabled: busy }, "Lưu"),
    );
  const cards = (rows, render) =>
    h(
      "div",
      { className: "business-grid" },
      ...rows.map((r) =>
        h("article", { className: "panel", key: r.id }, ...render(r)),
      ),
      !rows.length && h("p", { className: "muted" }, "Chưa có dữ liệu."),
    );
  let content = null;
  if (data && tab === "channels")
    content = h(
      React.Fragment,
      null,
      h(
        "p",
        { className: "muted" },
        "MCP được kiểm tra tại Hub. Kiểm tra công cụ thành công chưa xác nhận quyền truy cập tài khoản. Cần OAuth/API và máy chủ MCP phù hợp trước khi sử dụng.",
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
              "Tài liệu chính thức ↗",
            ),
          official?.template &&
            button("Mở mẫu MCP", () => onConfigure(official.template)),
          c.connector &&
            button("Kiểm tra MCP", async () => {
              const r = await post("/business/channels/" + c.id + "/test", {});
              setNotice(
                r.mcp_reachable
                  ? "MCP phản hồi; cần kiểm tra tài khoản riêng."
                  : "Công cụ chưa khớp cấu hình.",
              );
            }),
          c.read_tool &&
            button("Đọc qua MCP", async () => {
              const r = await post("/business/channels/" + c.id + "/read", {
                arguments: {},
              });
              setNotice(JSON.stringify(r));
            }),
        ];
      }),
      form(
        "Ánh xạ kênh → MCP",
        [
          channelSelect(),
          field("connector", "ID connector MCP đã lưu"),
          field("read_tool", "Công cụ đọc", "text", false),
          field("send_tool", "Công cụ gửi", "text", false),
          h(
            "label",
            null,
            "Mẫu JSON tham số gửi ($recipient, $content)",
            h("textarea", {
              name: "template",
              defaultValue: '{"recipient":"$recipient","content":"$content"}',
            }),
          ),
          field(
            "webhook_secret",
            "Khóa webhook bridge ≥32 ký tự",
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
        "Tạo khách hàng",
        [
          field("name", "Tên khách hàng"),
          field("email", "Email", "email", false),
          field("phone", "Điện thoại", "text", false),
        ],
        (v) => post("/business/customers", v),
      ),
      cards(data, (c) => [
        h("h3", null, c.name),
        h("p", null, [c.email, c.phone].filter(Boolean).join(" · ")),
        h(
          "p",
          null,
          `${c.stage} · ${c.message_count} tin nhắn · ${money(c.revenue)}`,
        ),
        button("Hồ sơ 360", async () =>
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
            `${detail.messages.length} tin nhắn · ${detail.sales.length} báo giá/đơn · ${detail.tickets.length} ticket`,
          ),
          ...detail.messages.map((m) =>
            h("p", { key: m.id }, `${m.channel}: ${m.content}`),
          ),
          form(
            "Cập nhật vòng đời",
            [
              select("stage", "Giai đoạn", [
                ["lead", "Lead"],
                ["prospect", "Tiềm năng"],
                ["customer", "Khách hàng"],
                ["loyal", "Trung thành"],
              ]),
              field("notes", "Ghi chú", "text", false),
            ],
            (v) => post("/business/customers/" + detail.id, v, "PATCH"),
          ),
          form(
            "Gắn định danh kênh",
            [channelSelect(), field("external_id", "ID khách trên nền tảng")],
            (v) => post("/business/customers/" + detail.id + "/identities", v),
          ),
        ),
    );
  if (data && tab === "inbox")
    content = h(
      React.Fragment,
      null,
      form(
        "Nhập tin nhắn thủ công",
        [
          channelSelect(),
          field("external_id", "ID tin nhắn"),
          field("sender_id", "ID người gửi"),
          field("sender_name", "Tên người gửi"),
          field("content", "Nội dung"),
        ],
        ({ channel, ...v }) =>
          post("/business/inbox/" + channel + "/import", v),
      ),
      form(
        "Soạn phản hồi",
        [
          channelSelect(),
          field("recipient", "ID người nhận"),
          field("content", "Nội dung"),
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
          button("Gửi qua MCP", () =>
            post("/business/inbox/" + m.id + "/send", {}),
          ),
      ]),
    );
  if (data && tab === "campaigns")
    content = h(
      React.Fragment,
      null,
      form(
        "Chiến dịch đa kênh",
        [
          field("title", "Tên chiến dịch"),
          field("objective", "Mục tiêu"),
          field("channels", "Kênh, phân cách dấu phẩy"),
          field("budget", "Ngân sách VND", "number"),
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
        button("Lập kế hoạch bằng AI", () =>
          onAskAI(
            `Lập kế hoạch cho chiến dịch ${c.title}. Mục tiêu: ${c.objective}. Kênh: ${c.channels.join(", ")}. Ngân sách: ${c.budget} VND. Tạo lịch triển khai, nội dung và chỉ số đo lường.`,
          ),
        ),
        form(
          "Lưu kế hoạch",
          [
            h(
              "label",
              null,
              "Kế hoạch",
              h("textarea", { name: "plan", defaultValue: c.plan }),
            ),
            select("status", "Trạng thái", [
              ["draft", "Nháp"],
              ["planned", "Đã lập kế hoạch"],
              ["done", "Hoàn thành"],
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
        "Tạo báo giá",
        [
          customerSelect(),
          field("title", "Tên báo giá"),
          field("item", "Sản phẩm / Dịch vụ"),
          field("quantity", "Số lượng", "number"),
          field("unit_price", "Đơn giá VND", "number"),
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
          button("Chuyển thành đơn", () =>
            post("/business/sales/" + s.id, { status: "order" }, "PATCH"),
          ),
        s.status === "order" &&
          button("Ghi nhận đã thu tiền", () =>
            post("/business/sales/" + s.id, { status: "paid" }, "PATCH"),
          ),
      ]),
    );
  if (data && tab === "tickets")
    content = h(
      React.Fragment,
      null,
      form(
        "Tạo ticket hỗ trợ",
        [
          field("title", "Tiêu đề"),
          field("description", "Mô tả", "text", false),
          select("priority", "Ưu tiên", [
            ["normal", "Thường"],
            ["high", "Cao"],
          ]),
        ],
        (v) => post("/business/tickets", v),
      ),
      cards(data, (t) => [
        h("h3", null, t.title),
        h("p", null, t.description),
        h("p", null, t.priority + " · " + t.status),
        t.status !== "resolved" &&
          button("Giải quyết", () =>
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
        "Sổ thu chi nội bộ VND. Ghi nhận thanh toán thủ công; chưa đối soát ngân hàng hoặc phát hành hóa đơn thuế.",
      ),
      form(
        "Ghi thu / chi",
        [
          select("direction", "Loại", [
            ["income", "Thu"],
            ["expense", "Chi"],
          ]),
          field("amount", "Số tiền VND", "number"),
          field("description", "Diễn giải"),
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
        "Thành viên / Cộng tác viên",
        [
          field("name", "Họ tên"),
          field("role", "Vai trò"),
          field("email", "Email", "email", false),
        ],
        (v) => post("/business/staff", v),
      ),
      cards(data, (s) => [
        h("h3", null, s.name),
        h("p", null, s.role),
        h("p", null, s.email),
        h("p", null, s.status),
        button(s.status === "active" ? "Tạm nghỉ" : "Kích hoạt", () =>
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
          customers: "Khách hàng",
          paid_orders: "Đơn đã thu",
          open_tickets: "Ticket đang mở",
          income: "Tổng thu",
          expense: "Tổng chi",
          balance: "Chênh lệch thu chi",
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
        h("h3", null, "Tin nhắn theo kênh"),
        ...data.channels.map((c) =>
          h("p", { key: c.channel }, `${c.channel}: ${c.messages}`),
        ),
        h("h3", null, "Vòng đời khách hàng"),
        ...data.stages.map((s) =>
          h("p", { key: s.stage }, `${s.stage}: ${s.count}`),
        ),
      ),
    );
  return h(
    "section",
    null,
    h("span", { className: "eyebrow" }, "ONE PERSON COMPANY"),
    h("h1", null, "Điều hành doanh nghiệp"),
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
    !data && h("p", null, "Đang tải…"),
    content,
  );
}
