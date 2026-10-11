# Cài SoloOS trên máy chủ riêng

Yêu cầu Docker Compose, Git, Python 3 và `uv`; tên miền trỏ về máy chủ, cổng 80/443 dành cho Caddy của bản cài này. Nếu máy chủ đã có Apache/Nginx, dùng reverse proxy hiện có thay vì chạy thêm Caddy trên cùng cổng.

```sh
git clone https://github.com/BDSG-VN/BDSG-SoloOS.git
cd BDSG-SoloOS
uv run python scripts/init_env.py --domain example.com
docker compose up -d --build
```

Thay `example.com` bằng tên miền của bạn. Trình tạo cấu hình không ghi đè `.env` đã tồn tại. Giữ `.env` riêng, quyền 0600; không tải lên GitHub hay chia sẻ ảnh chứa khóa.

Mở `https://example.com/admin`. Lần đầu, nhập khóa máy chủ từ `BDSG_OWNER_TOKEN` trong `.env`, chọn tên admin và mật khẩu ít nhất 12 ký tự. Chỉ chủ máy chủ có khóa mới khởi tạo được. Sau đó đăng nhập bằng tài khoản admin; lưu khóa máy chủ vào nơi giữ bí mật để khôi phục truy cập.

Trong **Nội dung & website → Giao diện & thông tin website**:
1. Đặt tên website, lời giới thiệu và mẫu màu.
2. Tạo trang nháp từ mẫu ngành hoặc cá nhân; thay nội dung hướng dẫn bằng thông tin của bạn.
3. Xem trước, xuất bản, chọn trang làm trang chủ.
4. Bật đăng ký khách nếu cần. Khách dùng `/account`, admin dùng `/admin`.

Cấu hình nguồn AI trong quản trị trước khi dùng AI Studio hoặc viết bài bằng AI. Đăng ký khách không tự cấp quyền AI hay MCP.

## Dữ liệu và nâng cấp

Dữ liệu nằm trong Docker volume `soloos_data`. Sao lưu volume và `.env` trước cập nhật. Không chạy `docker compose down -v` khi muốn giữ dữ liệu. Nâng cấp bằng image/revision cụ thể, giữ image trước để hoàn tác. Không triển khai nhiều worker scheduler cho cùng kho SQLite.

## Cloudflare

Cloudflare DNS/proxy có thể đứng trước máy chủ này, dùng HTTPS Full (strict). Đây là bản máy chủ riêng, không phải bản chạy toàn bộ trên Workers/D1. Xem [trạng thái chuyển đổi Cloudflare](WEBSITE-AND-CLOUDFLARE.md) trước khi chọn hạ tầng. Chưa có nút Deploy to Cloudflare được chứng nhận cho toàn bộ SoloOS.
