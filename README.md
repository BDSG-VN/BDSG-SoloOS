# BDSG SoloOS

**BDSG SoloOS** là sản phẩm mã nguồn mở (Open-Source) đột phá được phát triển và
bảo trợ chính thức bởi **BDSG Foundation** — Tổ chức hoạt động vì mục tiêu xã hội
nằm trong Hệ sinh thái nền tảng số **BDSG** (bao gồm *BDSG Group* và *BDSG Holdings*).

Với triết lý **"Rent the model, own the brain"** (Thuê mô hình AI, nhưng làm chủ
tuyệt đối bộ não dữ liệu), **BDSG SoloOS** được kiến tạo để trở thành hạ tầng công
nghệ tối thượng cho các nhà khởi nghiệp độc lập (Solopreneur). Hệ thống giúp tự
động hóa toàn bộ dòng chảy kinh doanh theo mô hình 4 chặng khép kín:
**Tư vấn ➔ Triển khai ➔ Vận hành ➔ Tăng trưởng**.

Đó là định hướng của sản phẩm. Bản mã nguồn mở đầu tiên **v0.1** tập trung vào
hạ tầng một chủ doanh nghiệp tự lưu trữ, MCP có kiểm soát quyền và giao diện AI
streaming; các chức năng đã triển khai được liệt kê bên dưới.

## Có trong bản đầu tiên

- Dashboard React tiếng Việt: tổng quan, AI Studio, bộ nhớ, Kanban, MCP, phê duyệt.
- FastAPI với đăng nhập cookie HttpOnly, CSRF gắn phiên, CORS allowlist, giới hạn
  tần suất, kiểm tra Host và các header bảo mật.
- MCP thật qua `stdio` và Streamable HTTP, discovery có phân trang, kiểm tra JSON
  Schema. Mọi model và công cụ đi qua cùng một Hub.
- Ba cấp quyền do hệ thống thực thi: `read_only`, `requires_confirmation`, `full_access`.
  Công cụ chưa được chủ doanh nghiệp cấp đều bị chặn. Gợi ý read-only của máy chủ
  MCP không được dùng để cấp quyền.
- Phê duyệt một lần, hết hạn 5 phút, gắn với người yêu cầu, đúng công cụ/tham số,
  phiên bản cấu hình và định nghĩa công cụ. Đổi cấu hình/định nghĩa làm mất hiệu lực.
- OpenUI Lang được parser/renderer chính thức kết xuất theo luồng SSE: biểu đồ,
  tiến độ và biểu mẫu. Luồng mẫu được ghi rõ là dữ liệu minh họa.
- Bộ nhớ Markdown tương thích Obsidian, SQLite lưu lịch sử chat với FTS5,
  bảng việc Kanban lưu bền vững; MCP Second Brain tích hợp sẵn.
- Chat thật qua LLM Gateway tương thích OpenAI, gồm gọi công cụ MCP và luồng UI.
  Dùng LiteLLM để cấu hình model từ 13 nhóm nhà cung cấp; không kèm sẵn khóa API.
- Docker Compose + Caddy cho `phamvanthu.com`, CI, giấy phép MIT.

Bản này chưa triển khai các kênh Telegram/Zalo, sandbox sub-agent, tự phân rã
và chạy công việc nền, thanh toán, marketplace, hoặc tự học tự động. Kanban hiện
là bảng quản lý việc; lưu tri thức qua Hub cần chủ doanh nghiệp duyệt theo quyền
đã cấu hình. Hàm Git commit bộ nhớ là opt-in và chưa bật trên giao diện.

## Chạy trên máy cá nhân

Cần Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 22+ và npm.

```bash
git clone https://github.com/BDSG-VN/BDSG-SoloOS.git
cd BDSG-SoloOS
uv sync --frozen
uv run python scripts/init_env.py
cd dashboard
npm ci
npm run build
cd ..
uv run uvicorn server.main:create_app --factory --env-file .env --host 127.0.0.1 --port 8000
```

Mở `http://localhost:8000`. Đọc `BDSG_OWNER_TOKEN` trong `.env` bằng trình soạn
thảo cục bộ và nhập vào màn hình đăng nhập. Khóa chỉ dùng để tạo phiên, không
lưu vào localStorage. Script không in khóa và không ghi đè `.env` đã có.

Để phát triển frontend, chạy API ở cổng 8000 và `npm run dev` trong `dashboard/`;
Vite ở cổng 5173 proxy `/api` về backend.

### LLM Gateway

Sửa `.env` rồi khởi động lại API:

```dotenv
BDSG_LLM_BASE_URL=http://your-private-litellm:4000/v1
BDSG_LLM_API_KEY=your-gateway-virtual-key
BDSG_LLM_MODEL=solo-default
```

Model alias phải tồn tại trên gateway. AI Studio cho phép đổi alias, còn các
kết nối MCP và quyền vẫn giữ nguyên. `provider_specs.py` mô tả 13 nhóm nhà cung
cấp; việc xác thực từng nhà cung cấp nằm ở gateway. URL/key không gửi ra frontend.
Nếu chưa có gateway, nút **Thử luồng giao diện mẫu** vẫn chạy thật qua SSE và
OpenUI renderer, nhưng không sử dụng LLM.

### MCP

Trong **Kết nối MCP**, cấu hình máy chủ được tin cậy và danh sách công cụ:

```json
{
  "id": "calendar",
  "transport": "streamable_http",
  "url": "https://your-trusted-server.example/mcp",
  "permission": "read_only",
  "tools": {"list_events": true, "create_event": false},
  "enabled": true,
  "credentials": {"headers": {"Authorization": "Bearer YOUR_TOKEN"}}
}
```

`tools` là allowlist: `true` nghĩa là chủ đã kiểm tra công cụ chỉ đọc, `false`
nghĩa là công cụ có thể ghi. Với `read_only`, công cụ `false` bị chặn; với
`requires_confirmation`, mọi lời gọi đã allowlist cần duyệt; với `full_access`,
công cụ đã allowlist được chạy tự động. Không dùng tên công cụ hay nhãn do LLM
đề xuất để tự cấp quyền. Công cụ Second Brain mặc định cần xác nhận, gồm cả đọc.

Credentials mã hóa bằng Fernet trước khi lưu SQLite. API danh sách cấu hình không
trả credentials. Bỏ trường `credentials` khi cập nhật để giữ khóa cũ; gửi `{}`
để xóa khóa. Mỗi cập nhật tăng revision và vô hiệu hóa phê duyệt trước đó.

Agent dùng `Authorization: Bearer BDSG_AGENT_TOKEN` để gọi endpoint MCP;
credential này không thể duyệt, đổi quyền, đọc trực tiếp bộ nhớ hay sửa Kanban.
LLM chỉ nhận các alias công cụ, không nhận khóa chủ hay khóa mã hóa.

Hub bảo vệ đường gọi công cụ. Nó không sandbox một chương trình MCP độc hại:
chủ chỉ cài máy chủ tin cậy; dùng container riêng cho executable bên thứ ba.
Một thao tác đã được gửi đi không thể thu hồi khi thay đổi quyền. Lỗi không rõ
đã thực thi hay chưa không được tự động thử lại bằng phê duyệt cũ.

## Cài trên phamvanthu.com

Xem [hướng dẫn triển khai](docs/DEPLOYMENT.md). Docker Compose có volume riêng cho
bộ nhớ, SQLite, credentials mã hóa và chứng chỉ HTTPS. Dữ liệu thật trong `brains/`,
`.env`, `system/*.db` bị loại khỏi Git; mẫu công khai nằm ở `system/templates/`.

## Kiểm tra

```bash
uv run ruff check server tests scripts
uv run pytest -q
cd dashboard
npm test
npm run build
```

Tests gồm các đường vượt quyền, CSRF/CORS/agent-owner, hết hạn và dùng lại phê
duyệt, MCP thật trên cả hai transport, xử lý UTF-8/SSE chia nhỏ, form và chart
qua runtime OpenUI chính thức. GitHub Actions kiểm tra mã và build Docker image.

## Cấu trúc

```text
server/
  main.py                 FastAPI, middleware và API
  api/security.py         Đăng nhập, principal và quyền chủ
  core/mcp_hub.py          Cổng thực thi MCP duy nhất
  core/mcp_store.py        Credentials, quyền, phê duyệt, audit
  core/brain.py            Markdown + SQLite/FTS5
  core/tasks.py            Kanban lưu bền vững
  core/self_learning.py    Hàm lưu bộ nhớ đã duyệt + Git opt-in
  engines/router.py        Gateway streaming + vòng công cụ MCP
  engines/provider_specs.py
  plugins/brain_mcp.py     Máy chủ MCP Second Brain
dashboard/
  components/openui_render.js
  components/knowledge_graph.js
  i18n/
brains/default_brain/      Dữ liệu riêng, khởi tạo khi cài/chạy
  memory/FACTS.md
  wiki/QUICKSTART.md
  conversations.db
system/
  templates/              Mẫu dữ liệu công khai
  plugins/
  skills/
deploy/Caddyfile
```

Tham khảo [quyết định kiến trúc](docs/ARCHITECTURE.md) và
[nguồn/giấy phép bên thứ ba](THIRD_PARTY_NOTICES.md). MIT © BDSG Foundation.
