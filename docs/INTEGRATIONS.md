# MCP và nghiệp vụ trong bản 0.1.0

BDSG SoloOS thực thi quyền ở MCP Hub, độc lập với LLM. Kết nối qua stdio hoặc Streamable HTTP, allowlist công cụ do chủ hệ thống xác nhận. Các mẫu bên dưới không đồng nghĩa tài khoản đã được kết nối. Tình trạng nguồn chính thức kiểm tra ngày 11/10/2026.

| Kênh | Bằng chứng chính thức | Phạm vi và trạng thái |
|---|---|---|
| Google Ads | [Google Ads MCP](https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server), [mã nguồn Google](https://github.com/googleads/google-ads-mcp) | Đọc báo cáo/tài khoản. Cần self-host/Cloud Run và quyền OAuth; không tạo hoặc dừng quảng cáo. |
| Email/Gmail | [Gmail MCP](https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server) | Developer Preview. Endpoint `https://gmailmcp.googleapis.com/mcp/v1`. Đọc hội thoại, nhãn, soạn draft; chưa cấu hình tài khoản, không hứa gửi email. |
| Hotline/Twilio | [Twilio docs MCP](https://www.twilio.com/docs/ai/mcp) | `https://mcp.twilio.com/docs`, chỉ tài liệu công khai. Không điều khiển cuộc gọi/SMS. |
| Zalo OA / ZNS | [Zalo Developers](https://developers.zalo.me/docs) | Có API chính thức; chưa xác minh MCP nghiệp vụ của nhà cung cấp. |
| Facebook | [Messenger Platform](https://developers.facebook.com/docs/messenger-platform/) | Chưa xác minh MCP nghiệp vụ chính thức. |
| Instagram | [Instagram Platform](https://developers.facebook.com/docs/instagram-platform/) | Chưa xác minh MCP nghiệp vụ chính thức. |
| TikTok | [Content Posting API](https://developers.tiktok.com/doc/en/content-posting-api-get-started) | Chưa xác minh MCP nghiệp vụ chính thức. |
| SMS | Tùy nhà mạng | Chưa có nhà cung cấp được chọn/xác minh. |
| Website | Máy chủ do chủ website cung cấp | Không có một MCP nhà cung cấp chung cho mọi website. |

Không tự cài MCP cộng đồng và không gắn nhãn chúng là chính thức. Danh mục có nguồn/capability và mẫu để chủ hệ thống xem, cấu hình, discovery, xét quyền. Trạng thái `tested` chỉ chứng minh công cụ MCP phản hồi, chưa chứng minh đủ quyền truy cập dữ liệu tài khoản. Thao tác gửi phải qua Hub; `accepted_by_tool` là công cụ hoàn tất, không phải xác nhận giao nhận từ nền tảng.

## Nghiệp vụ có thể sử dụng ngay

- Customer 360: khách hàng, vòng đời, ghi chú, định danh đa kênh và lịch sử tin nhắn/bán hàng/ticket. Không tự gộp người có cùng tên; chủ hệ thống gắn định danh rõ ràng.
- Inbox: nhập tin nhắn thủ công, webhook chuẩn hóa có HMAC, chống trùng; draft → MCP Hub → phê duyệt → thực thi một lần. Kênh chưa cấu hình không gửi được.
- Marketing: chiến dịch, mục tiêu, kênh, ngân sách, kế hoạch lưu bền vững; chuyển yêu cầu lập kế hoạch sang AI Studio. Chưa tự đăng nội dung/lên lịch nền.
- Sales: báo giá nhiều dòng qua API, tạo đơn, ghi nhận đã thu tiền; tổng tính bằng số nguyên VND, sổ thu chỉ tạo một lần cho một đơn.
- CSKH: ticket, mô tả, ưu tiên và trạng thái xử lý.
- Thu chi: sổ nội bộ liên kết đơn; chưa đối soát ngân hàng/phát hành hóa đơn thuế.
- Nhân sự: danh sách thành viên/cộng tác viên, vai trò và tình trạng; chưa tính lương.
- Công việc: Kanban lưu bền vững. Analytics: thu/chi, khách hàng, đơn đã thu, ticket và tin nhắn theo kênh từ dữ liệu thật trong DB.
- AI: MCP `business-read` chỉ đọc; `business-write` tạo khách/chiến dịch/ticket có xác nhận. Gateway LLM cần endpoint/API key trước khi AI thật hoạt động. Luồng minh họa luôn được gắn nhãn.

Không đưa con số tiết kiệm 70% trong ảnh thành cam kết. Không tuyên bố hoạt động 24/7 hay tất cả các kênh đã live khi thiếu hạ tầng, credentials và MCP nhà cung cấp.
