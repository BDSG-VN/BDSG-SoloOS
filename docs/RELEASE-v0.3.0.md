# BDSG SoloOS v0.3.0

AI Studio có màn hình tài khoản AI, hỗ trợ luồng đăng nhập ChatGPT chính thức mà không yêu cầu API key. Thông tin đăng nhập được mã hóa, scope và danh tính được xác minh; refresh token xoay vòng được tuần tự hóa. Tài khoản đã ngắt không bị callback cũ bật lại.

Bổ sung cuộc trò chuyện theo dự án, tìm kiếm lịch sử, ghim/lưu trữ/xuất JSON; kỹ năng và trợ lý; quy trình nhiều bước AI, MCP và ghi chú; lịch lặp, hàng đợi và hộp kết quả. MCP Hub kiểm tra cả quyền công cụ và trạng thái lượt chạy. Hủy hoặc lỗi chưa xác định không dẫn đến tự replay thao tác.

Có adapter cho Claude Code nguyên bản do người vận hành cài và đăng nhập. Bản image mặc định chưa kèm CLI hoặc tài khoản. AI thuê bao thật cần chính chủ đăng nhập và hoàn tất một lượt kiểm chứng; các kiểm thử mô phỏng không thay thế bước đó.

Các tính năng còn thiếu được ghi rõ trong FEATURE-COVERAGE.md. Đây là một mốc triển khai, chưa phải hoàn tất toàn bộ phạm vi mở rộng.
