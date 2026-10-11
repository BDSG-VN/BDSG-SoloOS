# Phạm vi mở rộng SoloOS

Đối chiếu toàn bộ danh mục mô-đun và tuyến API của gói tham khảo do chủ dự án cung cấp: 182 mô-đun Python, 380 tuyến HTTP/WebSocket. Đây là bảng theo dõi, không phải tuyên bố tương đương toàn bộ sản phẩm. Mã bổ sung được viết độc lập cho kiến trúc FastAPI/React của SoloOS.

| Nhóm | Trạng thái triển khai |
|---|---|
| AI Studio streaming, form/biểu đồ OpenUI | Đã có; công cụ qua MCP Hub |
| ChatGPT thuê bao, nhiều tài khoản, đổi model, ngắt và gia hạn | Có mã và kiểm thử mô phỏng; chờ chính chủ đăng nhập và inference thật |
| Claude thuê bao | Adapter CLI nguyên bản có mã; chưa cài/đăng nhập/nghiệm thu CLI thật |
| Các nhà cung cấp API, Ollama/model riêng | Gateway tương thích OpenAI; chưa có catalog riêng từng nền tảng |
| Grok/Antigravity/Gemini đăng nhập thuê bao | Chưa triển khai; cần xác minh phương thức chính thức từng nền tảng |
| Cuộc trò chuyện, tìm kiếm, ghim, lưu trữ, xuất | Có backend và giao diện; xuất JSON, lưu dữ liệu riêng từng cuộc trò chuyện |
| Dự án và bối cảnh dùng cho chat | Có; chưa có upload tài liệu riêng từng dự án |
| Bộ nhớ Markdown, wiki, biểu đồ tri thức | Có nhiều bộ nhớ độc lập, chọn theo cuộc trò chuyện, nhập Markdown/text; chưa có pipeline PDF/web và đồ thị tương tác |
| Tự học, đề xuất ký ức, duyệt, lịch sử/hoàn tác | Có AI đề xuất từ lịch sử, chủ duyệt, phát hiện bản cũ, lịch sử và đề xuất khôi phục; AI thật chờ đăng nhập |
| Kỹ năng và trợ lý | Tạo/sửa/tắt, gắn kỹ năng, chọn trợ lý cho chat và giới hạn connector được Hub kiểm tra lại lúc thực thi |
| Workflow nhiều bước | AI, ghi chú và MCP; checkpoint, kết quả, chờ phê duyệt, hủy các bước tiếp theo |
| Lịch chạy | Lặp theo phút, cron 5 trường/múi giờ IANA, chạy một lần, xem trước và bỏ qua khi workflow đang chạy |
| Hàng đợi nền | Một worker, lưu bền vững, phục hồi trạng thái chưa xác định sau crash; không tự replay write |
| Agent tự lập lại kế hoạch, goals/feedback | Chưa có runtime tự điều chỉnh kế hoạch |
| MCP permissions, danh sách cho phép, phê duyệt, audit | Đã có; chưa có OAuth tổng quát cho mọi MCP vendor |
| CRM, inbox, marketing, sales, ticket, nhân sự, analytics | Đã có nền tảng nghiệp vụ; kênh thật phụ thuộc API/MCP được cấu hình |
| Telegram, Slack, WhatsApp, Zalo, Lark bots | Chưa có adapter bot hoàn chỉnh cho từng nhà cung cấp |
| Voice, STT/TTS, live voice | Nhập/đọc qua Web Speech của trình duyệt; chưa nghiệm thu microphone thật hoặc live voice hội thoại |
| Tạo ảnh/video bằng từng provider | Chưa triển khai |
| Code workspace, PTY terminal, checkpoint git | Chưa triển khai |
| Gói plugin, cài/gỡ, kho bí mật riêng | Có nhập/xuất gói kỹ năng/trợ lý/workflow khai báo, luôn tắt khi nhập và bỏ quyền connector; chưa cài mã thực thi bên thứ ba |
| Backup GitHub hai chiều, import/export toàn brain | Xuất ZIP tài liệu và nhập từng Markdown/text; chưa có đồng bộ GitHub hoặc phục hồi toàn DB |
| TOTP, quản lý API token/phiên đăng nhập | Có xác thực owner/agent, CSRF, revoke phiên hiện tại; chưa có UI TOTP/token manager |
| Public share và thu hồi | Bản chụp chỉ đọc, token băm, hạn 1–30 ngày, chủ thu hồi; không tự cập nhật nội dung mới |
| PWA, thông báo push, linh vật, thương hiệu tùy chỉnh | Manifest và trang mất mạng; không cache dữ liệu người dùng. Chưa nghiệm thu cài đặt đa thiết bị, push/linh vật/thương hiệu tùy chỉnh |
| CMS tin tức/pages/homepage, AI biên tập | Có; thêm mẫu ngành, tài khoản khách, khởi tạo admin, tìm kiếm, RSS/sitemap; chưa toàn bộ WordPress |
| Theo dõi sử dụng | Token/lượt/status ChatGPT theo model/nguồn; chưa có budget chung và giá thực trả |

Vận hành workflow hiện yêu cầu một tiến trình worker cho mỗi thư mục dữ liệu. Kết quả `uncertain` cần kiểm tra công cụ đích trước khi chạy một lượt mới. Hủy không hoàn tác thao tác đã gửi đi.

Native iOS/macOS/Android: mã nguồn và cấu hình build thử nghiệm; macOS đã biên dịch cục bộ. Chưa nghiệm thu thiết bị thật. Cloudflare full-runtime/D1/R2 chưa hoàn tất.
