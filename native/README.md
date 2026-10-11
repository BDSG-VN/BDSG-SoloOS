# Ứng dụng native SoloOS (bản đang phát triển)

Apple: SwiftUI riêng cho iOS/macOS; Android: Android SDK/Java, không nhúng trang web. Ghép bằng mã do chủ cấp trong Thiết bị & ứng dụng. Credential được lưu trong Keychain (Apple), mã hóa AES-GCM bằng Android Keystore (Android). Token có phạm vi, ngày hết hạn, thu hồi trên máy chủ. Không yêu cầu khóa AI trong ứng dụng.

Hiện có chat văn bản streaming, công việc và ghép/ngắt thiết bị; Apple thêm thông báo vận hành và chọn hội thoại. Chưa có toàn bộ trình kết xuất biểu đồ/form, camera, màn hình, push, offline đồng bộ hoặc đầy đủ các màn hình web. Chưa phát hành App Store/Play Store; chưa kiểm thử thiết bị thật.

## Dựng

- macOS: `swift build --package-path native/apple` (đã biên dịch trên máy phát triển).
- iOS/macOS app bundle: cài Xcode và XcodeGen, vào `native/apple`, chạy `xcodegen`, mở `SoloOS.xcodeproj`; chọn team ký của chủ dự án. Không đưa khóa ký vào Git.
- Android: JDK 17, Android SDK 35 và Gradle 8.9; vào `native/android`, chạy `gradle :app:assembleDebug`. Build release cần cấu hình ký riêng.

Ghép thiết bị cần HTTPS. Android tắt backup và HTTP rõ. Cả hai không đi theo redirect có credential. Mã ghép một lần hết hạn sau năm phút; dùng quyền tối thiểu phù hợp.
