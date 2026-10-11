# Cài BDSG Solo-OS trên phamvanthu.com

Đây là hướng dẫn triển khai bản v0.1 cho một chủ doanh nghiệp. Mã đã có cấu hình
tên miền, nhưng cài lên máy chủ cần quyền truy cập VPS/Coolify và DNS.

## VPS dùng Docker Compose

1. Chuẩn bị VPS Linux có Docker Engine + Compose plugin, Git, Python 3.11+ và uv.
2. Trỏ bản ghi A của `phamvanthu.com` tới IP VPS. Chỉ giữ AAAA nếu IPv6 VPS hoạt
   động. Cho phép TCP 80/443; UDP 443 tùy chọn cho HTTP/3. Nếu domain đang phục vụ
   website khác, xác định kế hoạch chuyển trước khi đổi DNS.
3. Clone mã và tạo secrets ngay trên VPS:

```bash
git clone https://github.com/BDSG-VN/BDSG-SoloOS.git
cd BDSG-SoloOS
uv sync --frozen --no-dev
uv run python scripts/init_env.py --production
docker compose up -d --build
docker compose ps
curl --fail https://phamvanthu.com/api/health
```

Caddy cấp/gia hạn HTTPS tự động và proxy SSE không gom đợi luồng. Docker build
frontend rồi gói vào backend; chỉ Caddy xuất cổng ra Internet. Container API dùng
UID 10001, không gắn Docker socket hay thư mục chủ máy.

Đọc `BDSG_OWNER_TOKEN` từ `.env` bằng editor trên VPS để đăng nhập. Không đặt
`BDSG_OWNER_TOKEN`, `BDSG_AGENT_TOKEN`, `BDSG_STORE_KEY` trong biến frontend hoặc
commit vào Git. Secure cookies bật với cấu hình production. API login giới hạn
10 lần/phút/IP; API khác giới hạn 240 lần/phút/IP, lưu trong SQLite dùng chung.

`BDSG_DATA_DIR=/data` trong container. Volume `soloos_data` giữ toàn bộ dữ liệu;
khởi động lại/build lại không xóa dữ liệu hay đổi quyền. Mẫu Markdown chỉ được
copy khi file chưa tồn tại. Không chạy `docker compose down -v` để cập nhật.

## Nếu đã dùng Coolify

Tạo ứng dụng Dockerfile từ repo này, expose cổng 8000, gắn persistent volume vào
`/data`, đặt domain `https://phamvanthu.com` và cấu hình secrets tương tự `.env`
production. Để Coolify quản lý TLS/proxy. Không chạy service Caddy của Compose
trên máy đã có proxy chiếm cổng 80/443. Tắt buffering cho `text/event-stream`.

## LLM và dịch vụ ngoài

Gateway LiteLLM không được kèm trong Compose này. Dùng gateway của bạn hoặc một
dịch vụ tương thích OpenAI; đặt URL có hậu tố `/v1`, API key và model alias trong
biến `BDSG_LLM_*`. API gửi bộ nhớ đã lưu và lịch sử chat tới gateway khi bạn chat;
chọn gateway/model phù hợp với chính sách dữ liệu của mình.

MCP remote phải dùng HTTPS, ngoại trừ loopback. Với stdio, executable cần có trong
container; ảnh mặc định chỉ kèm Python và MCP Second Brain. Nếu cần `npx` hoặc
một binary khác, tạo image có dependencies đó hoặc chạy MCP bằng HTTP trên
container riêng; không giả định mọi plugin đã cài sẵn.

## Backup và cập nhật

Dừng API ngắn trước khi sao lưu SQLite để giữ một snapshot nhất quán; Caddy có
thể tiếp tục chạy. Tên project Compose có thể khác, nên sao lưu theo volume gắn
thực tế của service `soloos`:

```bash
docker compose stop soloos
docker compose run --rm --no-deps --user root --entrypoint tar soloos czf - -C /data . > soloos-data.tgz
docker compose start soloos
```

Sao lưu `.env` riêng và mã hóa cả hai bản sao. Không có `BDSG_STORE_KEY` thì không
giải mã được credentials MCP. Archive chứa bộ nhớ, lịch sử và tham số phê duyệt:
không upload nó lên repo công khai.

Khôi phục thử trên volume mới trong môi trường staging trước khi cần phục hồi
production. Cấu hình stdio chứa đường dẫn executable; khi chuyển giữa local và
Docker, cập nhật connector theo môi trường mới qua tài khoản chủ.

```bash
git pull --ff-only
docker compose up -d --build
curl --fail https://phamvanthu.com/api/health
```

## Xác minh sau cài

- Health trả `status: ok`, HTTPS đúng domain và API không đăng nhập trả 401.
- Đăng nhập, thêm một task, tải lại: task còn nguyên.
- Thử luồng UI mẫu: biểu đồ và form hiện dần; gửi mục tiêu thêm task.
- Lưu ghi chú: chưa duyệt chưa có file; duyệt rồi xuất hiện trong bộ nhớ.
- Đổi model alias đang có trên gateway: kết nối MCP và quyền giữ nguyên.
- Đổi quyền Second Brain sang read-only: `write_note` bị chặn tại Hub.
- Khôi phục dữ liệu trên staging và kiểm tra đọc được ghi chú/credentials.

Trong phiên phát triển, không có Docker Engine trên máy local; build/container
smoke test được chạy qua GitHub Actions. DNS, TLS và LLM có khóa thật cần kiểm
chứng trên máy chủ đích.
