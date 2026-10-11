# Nội dung & website — SoloOS 0.2

Mở `/admin`, đăng nhập bằng khóa chủ doanh nghiệp rồi chọn **Nội dung & website**.

## Biên tập và xuất bản

1. Chọn **Bài viết** hoặc **Trang**, tạo bản mới.
2. Nhập tiêu đề, tóm tắt và các khối: mở đầu, tiêu đề, đoạn văn, danh sách, trích dẫn, nút, ảnh, đường phân cách. Có thể đổi thứ tự khối.
3. Thêm chuyên mục, thẻ, nguồn HTTPS và thông tin SEO. Ảnh JPEG/PNG/WebP tối đa 5 MiB, 20 triệu điểm ảnh được giải mã, bỏ metadata và chuyển WebP tối đa 2560px. Không nhận SVG/HTML.
4. **Lưu bản nháp** → **Xem bản đã lưu** → **Xuất bản phiên bản đã lưu**. Bài viết ở `/news/{slug}`, trang ở `/pages/{slug}`; `/news` có lọc chuyên mục.
5. Với một trang đã xuất bản, chọn **Đặt làm trang chủ** để phục vụ tại `/`. `/admin` luôn mở khu quản trị.

Sửa một nội dung đã xuất bản chỉ thay bản nháp; người đọc vẫn nhận bản xuất bản trước đó. Khôi phục lịch sử cũng chỉ thay bản nháp. Gỡ xuất bản/chuyển vào thùng rác gỡ nội dung công khai; khôi phục từ thùng rác không tự xuất bản lại. Đường dẫn của trang đang xuất bản được khóa để tránh làm hỏng liên kết. Hai cửa sổ sửa đồng thời được kiểm bằng `expected_version`; lỗi 409 yêu cầu tải lại, không ghi đè âm thầm.

Ảnh chưa được tham chiếu trong nội dung đã xuất bản chỉ đọc được qua API chủ doanh nghiệp. Khi bỏ xuất bản, URL ảnh không còn được phục vụ công khai nếu không có trang khác sử dụng. Người đọc đã tải ảnh trước đó vẫn có thể giữ bản sao.

## Viết bài và tạo trang bằng lệnh AI

Trong **Cấu hình AI**, nhập Base URL của cổng tương thích OpenAI (gồm `/v1` nếu cổng yêu cầu), model và API key. Dùng được cổng BDSG/LiteLLM hoặc cổng riêng. Khóa mã hóa bằng `BDSG_STORE_KEY`; API không trả lại khóa. Cấu hình này dùng chung cho CMS và AI Studio. Có thể dùng biến môi trường `BDSG_LLM_BASE_URL`, `BDSG_LLM_API_KEY`, `BDSG_LLM_MODEL` khi chưa lưu cấu hình trong CMS.

Cổng từ xa phải dùng HTTPS. HTTP chỉ được dùng với loopback hoặc host được người vận hành khai báo rõ trong `BDSG_LLM_ALLOW_HTTP_HOSTS` (danh sách hostname phân cách dấu phẩy), dành cho mạng Docker riêng. Đổi origin sẽ không giữ khóa cũ. Sao lưu `BDSG_STORE_KEY` an toàn cùng quy trình sao lưu dữ liệu; mất khóa sẽ không giải mã được cấu hình.

Ví dụ lệnh:

- “Viết bản tin từ các dữ kiện dưới đây, giọng trung lập, chia thành 3 phần, không thêm số liệu ngoài tài liệu.”
- “Tạo trang chủ giới thiệu hoạt động tư vấn, gồm phần mở đầu, dịch vụ, quy trình Tư vấn → Triển khai → Vận hành → Tăng trưởng và nút dẫn đến /news.”
- “Rút gọn trang hiện tại, làm rõ giá trị dịch vụ và giữ nguyên các thông tin liên hệ đã có.”

Lưu nội dung đang sửa trước khi yêu cầu AI chỉnh tiếp. Dán dữ kiện vào ô tài liệu tham khảo. Danh sách URL chỉ là nguồn do người biên tập cung cấp: phiên bản này không tự duyệt và xác minh nội dung URL. AI truyền tiến độ qua SSE rồi trả đề xuất gồm các khối đã kiểm tra cấu trúc. Đề xuất chưa được lưu hay xuất bản; chủ doanh nghiệp kiểm chứng, sửa rồi lưu. Khi model lỗi, bị cắt đầu ra hoặc trả nội dung không hợp lệ, bản đang sửa được giữ nguyên. Nội dung có hỗ trợ AI được gắn nhãn trên trang công khai.

## MCP và quyền

- `cms-read`: `list_content`, chỉ đọc.
- `cms-write`: `save_content_draft`, cần phê duyệt tại Hub; kiểm phiên bản khi sửa nội dung cũ.
- Không có công cụ MCP xuất bản hoặc thay trang chủ. Tài khoản agent không được gọi API CMS quản trị. Quyết định xuất bản và cài đặt trang chủ là thao tác trực tiếp của chủ qua API xác thực, có CSRF với cookie.

## Lưu trữ, vận hành

Dữ liệu trong `system/cms.db`, ảnh trong `media/` dưới `BDSG_DATA_DIR`. Sao lưu SQLite bằng backup API hoặc khi container SoloOS đã dừng, kèm thư mục ảnh; không ghi đè dữ liệu production bằng dữ liệu thử. Bản nâng cấp thêm DB riêng, không đổi dữ liệu CRM/bộ nhớ/MCP hiện có. Reverse proxy phải cho phép ít nhất 5 MiB trên `/api/cms/media`; API vẫn tự chặn đúng 5 MiB. Tắt cache cho admin/API/preview và bỏ `noindex` toàn site nếu muốn trang đã xuất bản được tìm kiếm.

## Tham khảo WordPress

Thiết kế tham khảo cách WordPress tách bài viết/trang, trạng thái xuất bản, chuyên mục/thẻ, revisions và block editor:

- [WordPress tiếng Việt](https://vi.wordpress.org/)
- [REST Posts](https://developer.wordpress.org/rest-api/reference/posts/) và [Pages](https://developer.wordpress.org/rest-api/reference/pages/)
- [Post revisions](https://developer.wordpress.org/rest-api/reference/post-revisions/)
- [Block Editor Handbook](https://developer.wordpress.org/block-editor/)
- [WP REST Posts Controller](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/rest-api/endpoints/class-wp-rest-posts-controller.php): tham khảo phân tách kiểm quyền tạo/sửa và quyền xuất bản.

Đây là mã FastAPI/React do SoloOS triển khai độc lập theo MIT, không sao chép mã WordPress, không chạy WordPress/PHP và không tương thích plugin/theme WordPress. Phiên bản đầu chưa có lịch xuất bản, bình luận, đa tác giả hoặc nhập dữ liệu WordPress.
