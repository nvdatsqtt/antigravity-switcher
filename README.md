# Antigravity Account Switcher

[![CI](https://github.com/dat98/antigravity-switcher/actions/workflows/ci.yml/badge.svg)](https://github.com/dat98/antigravity-switcher/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux-orange.svg)]()

Công cụ chuyên dụng **độc lập**, quản lý và chuyển đổi tài khoản Google 1-click tức thì cho toàn bộ hệ sinh thái **Antigravity**:
- **Antigravity IDE (2.6+)**
- **Antigravity CLI (`agy`)**
- **Antigravity Desktop Hub (Antigravity-x64)**

> [!NOTE]
> **Dự Án Độc Lập Hoàn Toàn:** Switcher quản lý kho tài khoản riêng biệt tại `~/.config/antigravity-switcher/accounts.json` và hỗ trợ người dùng **tự đăng nhập/thêm tài khoản mới trực tiếp qua Google OAuth2**. Việc kế thừa tài khoản từ Cockpit Tools (`~/.antigravity_cockpit/`) chỉ là một tính năng nhập dữ liệu phụ trợ tùy chọn, không bắt buộc cài đặt.

---

## 🌟 Tính Năng Nổi Bật

- ⚡ **Chuyển đổi 1-click tức thì:** Nhấp đúp trong giao diện đồ họa (GUI) hoặc gõ 1 lệnh ngắn trên terminal (CLI) để đổi tài khoản đang hoạt động.
- ➕ **Tự thêm tài khoản dễ dàng:**
  - **Đăng nhập Google trực tiếp:** Mở trình duyệt xác thực Google OAuth2 an toàn, tự động bắt callback và lưu tài khoản.
  - **Nhập Refresh Token:** Hỗ trợ nhập thủ công chuỗi refresh token cho máy chủ headless hoặc môi trường không có trình duyệt.
- 🗑️ **Quản lý danh sách tài khoản:** Thêm, xóa, tìm kiếm thời gian thực theo email hoặc tên hiển thị.
- 🔄 **Đồng bộ đa đích (Multi-Target Injection):** Ghi token đồng thời vào GNOME Keyring (SecretService), SQLite database (`state.vscdb`), Desktop Hub Storage (`app_storage.json`) và các file token CLI.
- 📥 **Kế thừa linh hoạt:** Tích hợp sẵn lệnh nhập tài khoản từ Cockpit Tools cũ (`achange import-cockpit`) nếu có nhu cầu chuyển dịch dữ liệu.
- 🔐 **Bảo mật tuyệt đối:** Hoàn toàn chạy cục bộ (zero telemetry), phân quyền tệp `0600`, không gửi dữ liệu ra máy chủ bên thứ ba.
- 🎨 **Giao diện trực quan:** Hỗ trợ Dark Mode chuẩn VS Code, tự động dò tìm đường dẫn ứng dụng, điều phối đóng và mở lại IDE an toàn.

---

## 📋 Yêu Cầu Hệ Thống

- **Hệ điều hành:** Linux (Ubuntu/Debian, Fedora, Arch Linux, v.v.)
- **Python:** Phiên bản 3.8 trở lên
- **Thư viện hệ thống:**
  - `libsecret-tools` (quản lý GNOME Keyring / SecretService qua lệnh `secret-tool`)
  - `python3-tk` (hỗ trợ giao diện đồ họa Tkinter)

### Cài đặt gói phụ thuộc trên các bản phân phối Linux:
```bash
# Ubuntu / Debian / Linux Mint:
sudo apt update && sudo apt install -y python3-tk libsecret-tools

# Arch Linux / Manjaro:
sudo pacman -S tk libsecret

# Fedora / RHEL:
sudo dnf install -y python3-tkinter libsecret
```

---

## 🚀 Cài Đặt (Installation)

### 1. Clone mã nguồn về máy:
```bash
git clone https://github.com/nvdatsqtt/antigravity-switcher.git
cd antigravity-switcher
```

### 2. Cài đặt các thư viện Python:
```bash
pip install -r requirements.txt
```

### 3. Chạy script cài đặt hệ thống:
```bash
./install.sh
```
Script sẽ tự động:
- Tạo lệnh CLI toàn cục `achange` tại `~/.local/bin/achange`.
- Tạo biểu tượng ứng dụng tại `~/.local/share/applications/antigravity-switcher.desktop` để bạn có thể mở trực tiếp từ **Application Menu / Dock** của hệ điều hành.

*(Lưu ý: Đảm bảo thư mục `~/.local/bin` đã có trong biến `PATH` của bạn).*

### Gỡ cài đặt (Uninstallation):
```bash
./install.sh --uninstall
```

---

## 💻 Hướng Dẫn Sử Dụng

### 1. Giao Diện Dòng Lệnh (CLI `achange`)

```bash
# Xem danh sách tất cả tài khoản và tài khoản đang active:
achange

# Chuyển tài khoản theo số thứ tự (ví dụ: chuyển sang tài khoản số 2):
achange 2

# Chuyển tài khoản và tự động khởi động lại Antigravity IDE:
achange 2 --restart

# Chuyển tài khoản theo email (hỗ trợ tìm kiếm chuỗi con):
achange user@gmail.com

# Xoay vòng chuyển sang tài khoản kế tiếp:
achange next

# Kiểm tra tài khoản đang active:
achange status

# Thêm tài khoản mới bằng đăng nhập Google OAuth (tự động mở trình duyệt):
achange add

# Thêm tài khoản mới bằng Refresh Token thủ công:
achange add --token "1//04..."

# Xóa tài khoản khỏi danh sách (theo số thứ tự hoặc email):
achange remove 2
achange remove user@gmail.com

# Nhập tài khoản từ Cockpit Tools cũ (nếu có thư mục ~/.antigravity_cockpit):
achange import-cockpit

# Mở giao diện đồ họa:
achange gui
```

### 2. Giao Diện Đồ Họa (GUI 1-Click)

Chạy lệnh `achange gui` hoặc nhấp mở biểu tượng **Antigravity Account Switcher** trong menu ứng dụng:

- **1-Click Chuyển đổi:** Nhấp đúp chuột vào bất kỳ tài khoản nào trong bảng để kích hoạt ngay lập tức.
- **Nút `⚡ Kích hoạt (Không restart)`:** Đổi token cho CLI và các lượt mở IDE tiếp theo mà không làm gián đoạn cửa sổ IDE hiện tại.
- **Nút `🔄 Kích hoạt & Khởi động lại IDE`:** Đóng an toàn các phiên làm việc cũ và khởi động lại Antigravity IDE với tài khoản mới.
- **Nút `➕ Thêm tài khoản`:** Mở hộp thoại đăng nhập Google OAuth trực tiếp trên trình duyệt hoặc dán Refresh Token thủ công.
- **Nút `🗑️ Xóa`:** Xóa tài khoản đang chọn khỏi kho lưu trữ (có xác nhận an toàn).
- **Nút `📥 Nhập Cockpit`:** Nhập toàn bộ tài khoản từ Cockpit Tools cũ (bỏ qua các tài khoản trùng lặp).
- **Tìm kiếm tức thì:** Gõ vào ô tìm kiếm để lọc nhanh danh sách theo email hoặc tên hiển thị.

---

## 🏛️ Cơ Chế Hoạt Động & Kiến Trúc

Trong hệ sinh thái Antigravity, token xác thực Google OAuth được lưu trữ phân tán ở các vị trí:
1. **Kho độc lập của Switcher:** `~/.config/antigravity-switcher/accounts.json` (bảo vệ quyền `0600`).
2. **GNOME Keyring (SecretService qua DBus):** Service `gemini`, user `antigravity`.
3. **File Token Fallback CLI & Hub:** `~/.gemini/antigravity-cli/antigravity-oauth-token` và `~/.gemini/antigravity/antigravity-oauth-token`.
4. **Antigravity Desktop Storage:** `~/.config/Antigravity/app_storage.json`.
5. **Antigravity IDE SQLite & JSON:** `state.vscdb` (Topic nhị phân Protobuf `antigravityUnifiedStateSync.oauthToken` và `antigravityOnboarding`) & `storage.json`.

👉 *Xem tài liệu chi tiết tại:* **[Tài liệu Kiến trúc (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)** và **[Đặc tả Kỹ thuật (docs/SPECIFICATION.md)](docs/SPECIFICATION.md)**.

---

## 🧪 Kiểm Thử Tự Động (Testing)

Dự án áp dụng chiến lược Tiered Testing với độ bao phủ đầy đủ thuật toán nhị phân Protobuf, atomic file I/O, mô phỏng refresh token, đăng nhập token độc lập và môi trường cô lập:

```bash
python3 -m unittest -v test_switcher.py
```

---

## 📁 Cấu Trúc Thư Mục

```
antigravity-switcher/
├── .github/
│   ├── workflows/ci.yml           # GitHub Actions CI matrix test
│   ├── ISSUE_TEMPLATE/            # Mẫu báo cáo lỗi & yêu cầu tính năng
│   └── pull_request_template.md   # Mẫu Pull Request
├── assets/                        # Biểu tượng và tài nguyên đồ họa
├── docs/
│   ├── ARCHITECTURE.md            # Tài liệu thiết kế kiến trúc và luồng dữ liệu
│   └── SPECIFICATION.md           # Đặc tả kỹ thuật chi tiết
├── core.py                        # Module lõi: OAuth, Protobuf, Keyring, SQLite, Add/Remove
├── cli.py                         # Giao diện dòng lệnh (CLI achange)
├── gui.py                         # Giao diện đồ họa Dark Theme (Tkinter)
├── main.py                        # Entrypoint phân luồng GUI / CLI
├── install.sh                     # Script cài đặt & gỡ cài đặt hệ thống
├── test_switcher.py               # Bộ kiểm thử tự động toàn diện (14 tests)
├── requirements.txt               # Danh sách thư viện Python
├── pyproject.toml                 # Cấu hình gói tiêu chuẩn PEP 621
├── CONTRIBUTING.md                # Quy định và hướng dẫn đóng góp mã nguồn
├── SECURITY.md                    # Chính sách bảo mật & bảo vệ token
├── LICENSE                        # Giấy phép mã nguồn mở MIT
└── README.md                      # Tài liệu hướng dẫn sử dụng
```

---

## 🤝 Đóng Góp (Contributing)

Mọi đóng góp từ cộng đồng đều được hoan nghênh! Vui lòng đọc kỹ **[CONTRIBUTING.md](CONTRIBUTING.md)** trước khi tạo Pull Request.

---

## 🔒 Bảo Mật & Tuyên Bố Từ Chối Trách Nhiệm (Disclaimer)

- **Bảo mật:** Dự án này xử lý toàn bộ khóa và token ở cấp độ cục bộ trên máy của bạn với phân quyền `0600`. Xem chi tiết tại **[SECURITY.md](SECURITY.md)**.
- **Tuyên bố từ chối trách nhiệm:** Đây là tiện ích mã nguồn mở do cộng đồng phát triển và không phải là sản phẩm chính thức của Google LLC. "Antigravity", "Gemini" và các nhãn hiệu liên quan thuộc sở hữu của Google LLC.

---

## 📄 Giấy Phép (License)

Dự án được phân phối dưới giấy phép [MIT License](LICENSE).
