# Đặc Tả Kỹ Thuật & Yêu Cầu (Product Specification)

Tài liệu này quy chuẩn các đặc tả tính năng, giao diện CLI/GUI, biến môi trường và cấu trúc dữ liệu của **Antigravity Account Switcher**.

---

## 1. Giao Diện Dòng Lệnh (CLI Interface)

### 1.1. Cú Pháp Lệnh
```bash
achange [LỆNH | TRUY_VẤN | SỐ_THỨ_TỰ] [TÙY_CHỌN]
```

### 1.2. Bảng Lệnh & Cờ Tham Số

| Lệnh / Tham số | Tùy chọn viết tắt | Mô tả chi tiết |
| :--- | :--- | :--- |
| *(không đối số)* | `list`, `-l` | Hiển thị bảng danh sách tất cả các tài khoản và tài khoản active |
| `<index>` | *(ví dụ: `achange 1`)* | Chuyển sang tài khoản theo số thứ tự (1-based index) |
| `<email>` | *(ví dụ: `achange user@gmail.com`)* | Chuyển sang tài khoản theo địa chỉ email (hỗ trợ khớp chuỗi con) |
| `next` | `-n`, `--next` | Xoay vòng chuyển sang tài khoản kế tiếp trong danh sách |
| `status` | `-s`, `--status` | Kiểm tra và in ra email tài khoản đang kích hoạt |
| `add` | `login`, `--add` | Thêm tài khoản mới bằng đăng nhập Google OAuth qua trình duyệt |
| `add --token <TK>` | `-t` | Thêm tài khoản mới thủ công bằng Refresh Token Google |
| `remove <query>` | `rm`, `del` | Xóa tài khoản khỏi kho lưu trữ theo số thứ tự hoặc email |
| `import-cockpit` | `cockpit` | Nhập tài khoản từ Cockpit Tools cũ (bỏ qua các tài khoản trùng lặp) |
| `gui` | `-g`, `--gui` | Khởi chạy giao diện đồ họa người dùng |
| `--restart` | `-r` | Cờ kết hợp: tự động đóng và khởi chạy lại Antigravity IDE sau khi đổi tài khoản |

### 1.3. Mã Thoát (Exit Codes)
- `0`: Thực thi thành công.
- `1`: Lỗi tham số, không tìm thấy tài khoản hoặc lỗi kết nối refresh token.

---

## 2. Giao Diện Đồ Họa (GUI Specification)

### 2.1. Cửa Sổ & Giao Diện
- **Kích thước cửa sổ chuẩn:** 880 x 560 px (cho phép thu phóng tối thiểu 760 x 480 px).
- **Vị trí hiển thị:** Tự động căn giữa màn hình khi khởi chạy.
- **Bảng màu giao diện (Dark Theme Palette):**
  - Nền chính (`bg_main`): `#1e1e1e`
  - Nền bảng điều khiển (`bg_panel`): `#252526`
  - Nền card/thẻ (`bg_card`): `#2d2d2d`
  - Điểm nhấn Active (`color_active`): `#4ec9b0` (Teal/Xanh ngọc)
  - Nút Primary Action (`color_accent`): `#0e639c` (VS Code Blue)
  - Nút Restart Action (`color_restart`): `#2d7d46` (Success Green)
  - Nút Delete Action (`color_delete`): `#5a2323` (Crimson Red)

### 2.2. Tương Tác & Thao Tác Chuột
- **1-Click / Double-Click:** Nhấp đúp chuột trái vào bất kỳ hàng tài khoản nào trong danh sách để kích hoạt chuyển đổi ngay lập tức.
- **Thêm tài khoản (➕):** Mở cửa sổ popup `540x440 px` hỗ trợ 2 chế độ:
  1. *Đăng nhập trình duyệt:* Lắng nghe callback trên cổng an toàn `127.0.0.1:8120`, hoàn tất xác thực trong 120s.
  2. *Dán token:* Nhập trực tiếp chuỗi Refresh Token Google (`1//0...`).
- **Xóa tài khoản (🗑️):** Xóa tài khoản đang được chọn với hộp thoại xác nhận.
- **Nhập từ Cockpit (📥):** Nhập tài khoản kế thừa từ Cockpit Tools cũ nếu người dùng muốn chuyển đổi.
- **Tùy chọn tự động restart:** Checkbox `Tự restart IDE khi nhấp đúp` lưu trạng thái trong phiên làm việc.
- **Bộ lọc tìm kiếm tức thì (Real-time Filter):** Tìm kiếm không phân biệt hoa thường theo email hoặc tên hiển thị.

---

## 3. Biến Môi Trường (Environment Variables)

| Tên Biến | Mặc định | Mô tả |
| :--- | :--- | :--- |
| `ANTIGRAVITY_IDE_PATH` | Tự động dò tìm | Đường dẫn tuyệt đối tới file thực thi `antigravity-ide` |
| `ANTIGRAVITY_APP_PATH` | Tự động dò tìm | Đường dẫn tuyệt đối tới file thực thi Desktop Hub `antigravity` |
| `ANTIGRAVITY_GOOGLE_CLIENT_ID` | Client ID Antigravity chính thức | Cho phép tùy chỉnh Client ID OAuth nếu chạy môi trường riêng |
| `ANTIGRAVITY_GOOGLE_CLIENT_SECRET` | Client Secret Antigravity chính thức | Cho phép tùy chỉnh Client Secret OAuth tương ứng |

---

## 4. Cấu Trúc Dữ Liệu Lưu Trữ (JSON Schema)

File cấu hình độc lập được lưu tại: `~/.config/antigravity-switcher/accounts.json`

```json
{
  "version": "1.0",
  "updated_at": 1730680000,
  "active_email": "developer@example.com",
  "accounts": [
    {
      "id": "acc-uuid-string",
      "email": "developer@example.com",
      "name": "Developer Name",
      "created_at": 1730000000,
      "last_used": 1730680000,
      "token": {
        "access_token": "ya29.a0AfH6SM...",
        "token_type": "Bearer",
        "refresh_token": "1//04...",
        "expires_in": 3600,
        "expiry_timestamp": 1730683600,
        "expiry": "2026-11-04T08:00:00Z",
        "id_token": "eyJhbGci..."
      }
    }
  ]
}
```
Phân quyền truy cập bắt buộc: `0600` (`-rw-------`).

