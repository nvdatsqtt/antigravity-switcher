# Chính Sách Bảo Mật (Security Policy)

## 1. Phiên Bản Được Hỗ Trợ

| Phiên Bản | Hỗ Trợ Bảo Mật |
| :--- | :--- |
| `1.x.x` | :white_check_mark: Được hỗ trợ |
| `< 1.0` | :x: Không hỗ trợ |

---

## 2. Cam Kết An Toàn & Bảo Vệ Quyền Riêng Tư (Privacy & Token Hygiene)

Công cụ **Antigravity Account Switcher** được thiết kế dựa trên các nguyên tắc bảo mật nghiêm ngặt:

1. **Không Thu Thập Dữ Liệu (Zero Telemetry & Third-party Transmission):**
   - Ứng dụng **hoàn toàn mã nguồn mở**, không chứa bất kỳ mã theo dõi (analytics), nhật ký từ xa (remote logging) hay máy chủ trung gian nào.
   - Các yêu cầu mạng **chỉ duy nhất** gửi tới máy chủ xác thực chính thức của Google: `https://oauth2.googleapis.com/token` để làm mới `access_token` bằng `refresh_token`.

2. **Cơ Chế Phân Quyền Cục Bộ Nghiêm Ngặt (POSIX 0600 Permissions):**
   - Mọi tệp chứa token hoặc thông tin tài khoản tại `~/.config/antigravity-switcher/accounts.json` và các tệp fallback `antigravity-oauth-token` đều được tự động thiết lập quyền `chmod 0600` (chỉ duy nhất tài khoản người dùng hiện tại có quyền đọc và ghi).
   - Cơ chế ghi nguyên tử (Atomic write: ghi ra file `.tmp` trước khi thay thế) đảm bảo dữ liệu không bị hỏng hóc hoặc rò rỉ nếu quá trình ghi bị ngắt đột ngột.

3. **Tích Hợp SecretService / GNOME Keyring Chuẩn Mực:**
   - Ưu tiên lưu trữ và đọc thông tin phiên làm việc từ keyring được mã hóa của hệ điều hành thông qua DBus SecretService (`gemini` / `antigravity`).

---

## 3. Báo Cáo Lỗ Hổng Bảo Mật (Reporting a Vulnerability)

Nếu bạn phát hiện một vấn đề bảo mật tiềm ẩn:
- **Vui lòng không mở công khai Issue trên GitHub.**
- Gửi báo cáo chi tiết kèm mã nguồn tái hiện (Proof of Concept) qua tính năng **GitHub Security Advisories** của kho lưu trữ (nút "Report a vulnerability" trong tab Security).
- Nhóm phát triển sẽ xác nhận trong vòng 48 giờ và phát hành bản vá kịp thời.

