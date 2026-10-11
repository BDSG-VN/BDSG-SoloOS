# Website public, quản trị và triển khai

## Phân tách truy cập

- `/`: website công khai; thiếu trang chủ đã xuất bản thì hiển thị giới thiệu website, không trả dashboard.
- `/account`: đăng ký/đăng nhập khách hàng. Chủ website phải bật đăng ký. Phiên khách không cấp quyền quản trị, AI Studio hay MCP.
- `/admin`: đăng nhập quản trị bằng tên và mật khẩu sau khi khởi tạo. Khóa máy chủ vẫn là thông tin khôi phục có toàn quyền, cần giữ kín.
- `/api/setup`: khởi tạo tài khoản quản trị một lần, yêu cầu khóa máy chủ và Origin hợp lệ. Người truy cập đầu tiên không thể tự chiếm website.
- Mật khẩu scrypt với salt riêng; cookie HttpOnly/SameSite, Secure khi bật HTTPS; phiên khách tách khỏi phiên chủ, CSRF khi đăng xuất, giới hạn đăng ký/đăng nhập.

## Giao diện

Tám mẫu nội dung gốc bằng tiếng Việt: cá nhân/chuyên gia, tư vấn, cửa hàng, ẩm thực, giáo dục, bất động sản/kiến trúc, du lịch/lưu trú, chăm sóc sức khỏe. Mẫu tạo **bản nháp**, chưa tự xuất bản hoặc thay trang chủ. Các mục chứa hướng dẫn thay nội dung; không tự bịa dự án, khách hàng, chứng nhận hay số liệu.

Trong Nội dung & website → Giao diện & thông tin website, đặt tên, lời giới thiệu và màu giao diện. Tạo bản nháp từ mẫu, chỉnh nội dung, xuất bản rồi chọn làm trang chủ. Mẫu hiện dùng cùng hệ khối; chưa phải tám bộ bố cục chuyên ngành đầy đủ.

## Đối chiếu gói WordPress do chủ dự án cung cấp

Đã lập danh mục ZIP (4.493 mục) và đọc cơ chế installer, vai trò/quyền. Chỉ học thiết kế, không đưa mã PHP vào nguồn MIT. Không thực thi tệp trong ZIP. Tệp version.php trong ZIP tự khai phiên bản 7.1.3; chưa xác minh nguồn phát hành.

Có trong SoloOS: bài/trang, danh mục/nhãn, ảnh đã tái mã hóa, bản nháp, xuất bản snapshot, lịch sử/khôi phục, thùng rác, SEO cơ bản, tìm kiếm công khai, RSS/sitemap/robots, trang chủ chọn từ trang, đề xuất nội dung AI, tài khoản khách tách quản trị.

Còn thiếu so với một CMS tổng quát: xác minh email và quên mật khẩu qua nhà cung cấp mail, phân quyền biên tập viên/tác giả, bình luận/chống spam, menu kéo thả, mẫu bố cục đa dạng, lịch xuất bản, nhập/xuất toàn bộ website, cập nhật/migration có phục hồi, hệ sinh thái plugin. Chưa có kiểm toán bảo mật độc lập cho bản website mới. Không tuyên bố tương đương toàn bộ WordPress.

## Cloudflare: kết luận kỹ thuật đã kiểm tra

Tài liệu chính thức:
- https://developers.cloudflare.com/workers/platform/deploy-buttons/
- https://developers.cloudflare.com/workers/languages/python/packages/fastapi/
- https://developers.cloudflare.com/workers/languages/python/stdlib/
- https://developers.cloudflare.com/containers/api/container-class/

Deploy to Cloudflare có thể sao chép GitHub và tạo D1/R2 từ cấu hình Wrangler. FastAPI được hỗ trợ trên Python Workers, nhưng điều đó không tự làm SoloOS tương thích: dữ liệu hiện nằm trong nhiều SQLite, Markdown và media cục bộ; MCP stdio/Claude CLI và worker nền cần môi trường tiến trình. Filesystem Workers và disk container mặc định không phải nơi lưu bền.

Cần hoàn thành trước khi phát hành nút cài **toàn bộ** SoloOS trên Cloudflare:
1. Kho dữ liệu D1 với migration và transaction tương đương; R2 cho media/tài liệu, Secrets cho khóa.
2. Durable Objects/Queues/Workflows cho phiên AI, lịch và tác vụ, chống thực thi hai lần.
3. MCP HTTP qua Workers; MCP stdio/CLI chuyển sang máy kết nối riêng đã ghép đôi.
4. Kiểm thử phiên đăng nhập, CSRF, phân quyền Hub và khôi phục dữ liệu trên môi trường thật.
5. Wrangler, migration tự chạy và trình cài đặt một lần; kiểm chứng Deploy Button bằng tài khoản Cloudflare trước khi công bố hỗ trợ.

Hiện bản máy chủ riêng vẫn là bản triển khai đầy đủ. Chưa được thay SQLite bằng bộ nhớ tạm hoặc quảng bá cấu hình Cloudflare là tương đương bản máy chủ.
