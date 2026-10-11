# Kết nối tài khoản AI

SoloOS có ba đường chạy AI Studio và biên tập nội dung: ChatGPT qua quyền ứng dụng được chủ tài khoản cấp, Claude Code chính thức cài riêng, và Gateway tương thích OpenAI. Không có cơ chế chung biến mọi thuê bao AI thành API miễn phí. Model, hạn mức và quyền ứng dụng phụ thuộc nhà cung cấp.

## ChatGPT trên máy chủ riêng

1. Trong **Tài khoản AI**, tải `soloos-chatgpt-login.py` về máy đang mở trình duyệt.
2. Chạy `python3 soloos-chatgpt-login.py --site https://TEN-MIEN-CUA-BAN` trong Terminal. Cần Python 3; giữ tiến trình mở.
3. Trang quản trị mở ra. Đăng nhập SoloOS rồi chọn **Continue with ChatGPT**. Đọc và cấp quyền trên trang chính thức của OpenAI.
4. Sau khi trở về SoloOS, chọn model trong danh sách mà tài khoản cung cấp. AI Studio và CMS dùng cùng nguồn đã chọn.

Trình hỗ trợ chỉ lắng nghe `127.0.0.1:1455` trong mười phút. Nó chuyển mã ủy quyền một lần về trang quản trị qua URL fragment; mã được xóa khỏi URL ngay khi trang tải. Máy chủ xác minh state, PKCE và chữ ký/danh tính ID token trước khi lưu thông tin được mã hóa. Token không được đưa vào browser storage. Không cần API key, client secret hay đọc thông tin đăng nhập Codex có sẵn.

Thông tin kết nối nằm trong `system/ai.db`, mã hóa bằng khóa kho dữ liệu của SoloOS. Sao lưu DB cùng khóa theo quy trình bảo mật riêng. Đăng xuất tài khoản xóa token ở SoloOS và thử thu hồi phía nhà cung cấp. Nếu thu hồi từ xa chưa được xác nhận, giao diện yêu cầu kiểm tra quyền ứng dụng trong cài đặt ChatGPT.

Đây là triển khai dựa trên [đăng nhập chính thức](https://developers.openai.com/siwc/token-sharing-open-source/sign-in), [máy chủ riêng](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms) và [inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference). Kết quả chỉ hoàn tất khi nhà cung cấp gửi `response.completed`; lỗi hạn mức có thể xảy ra sau vài token. Công cụ vẫn được MCP Hub kiểm tra quyền.

## Claude Code nguyên bản

Adapter đã có trong mã nguồn; binary và đăng nhập không được tự cài hoặc sao chép từ tài khoản khác. Người vận hành cài bản chính thức theo [hướng dẫn Anthropic](https://code.claude.com/docs/en/setup), xem [điều kiện tích hợp](https://code.claude.com/docs/en/legal-and-compliance), rồi cấu hình:

- `BDSG_CLAUDE_BINARY`: đường dẫn tuyệt đối đến binary chính thức, mặc định `/opt/claude/claude`.
- `BDSG_CLAUDE_HOME`: thư mục riêng và bền vững, mặc định `/data/native-claude`.

Chạy `claude auth login` bằng đúng user của dịch vụ, với `HOME` và `CLAUDE_CONFIG_DIR` trỏ vào thư mục riêng ở trên. Người dùng chọn phương thức đăng nhập trong CLI chính thức. SoloOS không nhận, hiển thị hay quản lý token Claude. Trong Docker cần gắn binary và thư mục riêng vào container, bảo đảm binary tương thích hệ điều hành và quyền thực thi.

Chọn **Claude Code** trong Tài khoản AI và bấm **Kiểm tra Claude Code**. Adapter chạy chế độ an toàn, tắt công cụ và MCP trong phiên CLI để soạn nội dung. Chưa hỗ trợ gọi công cụ SoloOS từ phiên Claude này. Chế độ `--bare` không được dùng vì theo tài liệu hiện tại nó bỏ qua đăng nhập thuê bao. Native adapter cần nghiệm thu với phiên bản CLI thực tế trước khi coi là kết nối hoạt động.

## Kiểm chứng

Kiểm thử tự động dùng identity server và luồng inference mô phỏng. Chúng không chứng minh tài khoản thuê bao thật đã đăng nhập hoặc được cấp hạn mức. Chỉ báo kết nối thành công sau callback đã xác minh, và chỉ báo AI chạy thật sau một lượt inference hoàn tất. Không lưu tài khoản mẫu trên production.
