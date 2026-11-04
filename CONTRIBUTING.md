# Hướng Dẫn Đóng Góp (Contributing Guide)

Cảm ơn bạn đã quan tâm và muốn đóng góp cho dự án **Antigravity Account Switcher**!  
Để duy trì chất lượng mã nguồn và sự an toàn cho người dùng, vui lòng tham khảo các hướng dẫn dưới đây.

---

## 1. Thiết Lập Môi Trường Phát Triển

1. **Fork và Clone repository:**
   ```bash
   git clone https://github.com/nvdatsqtt/antigravity-switcher.git
   cd antigravity-switcher
   ```

2. **Cài đặt phụ thuộc hệ thống (Linux):**
   - Ubuntu / Debian:
     ```bash
     sudo apt update && sudo apt install -y python3-tk libsecret-tools
     ```
   - Arch Linux:
     ```bash
     sudo pacman -S tk libsecret
     ```
   - Fedora:
     ```bash
     sudo dnf install python3-tkinter libsecret
     ```

3. **Cài đặt môi trường ảo Python & Dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

---

## 2. Quy Trình Đóng Góp (Workflow)

1. Tạo một nhánh (branch) mới từ `main`:
   ```bash
   git checkout -b feature/ten-tinh-nang-moi
   # hoặc:
   git checkout -b fix/mo-ta-loi
   ```
2. Thực hiện thay đổi mã nguồn.
3. **Chạy bộ kiểm thử tự động (Bắt buộc pass 100%):**
   ```bash
   python3 -m unittest -v test_switcher.py
   ```
4. Cam kết thay đổi (commit) với thông điệp rõ ràng theo định dạng Conventional Commits:
   - `feat: thêm tùy chọn tìm kiếm theo tên trong GUI`
   - `fix: xử lý ngoại lệ khi file SQLite bị khóa tạm thời`
   - `docs: bổ sung hướng dẫn chạy trên Fedora`
5. Tạo Pull Request trên GitHub và điền đầy đủ thông tin vào PR Template.

---

## 3. Tiêu Chuẩn Mã Nguồn

- Tuân thủ chuẩn lập trình Python (PEP 8).
- Viết type hints đầy đủ cho tham số và giá trị trả về của hàm.
- Viết docstrings giải thích rõ ràng mục đích, tham số đầu vào và đầu ra.
- Tuyệt đối **không đưa thông tin cá nhân, email thực tế hoặc token cá nhân** vào mã nguồn hoặc file test. Mọi test phải sử dụng dữ liệu giả lập (mock data) hoặc môi trường cô lập.

