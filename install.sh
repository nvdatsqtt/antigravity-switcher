#!/usr/bin/env bash
# Script cài đặt tiện ích Antigravity Account Switcher vào hệ thống Linux
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_PATH="$BASE_DIR/assets/antigravity-ide-app.png"

# Xử lý cờ gỡ cài đặt (Uninstall)
if [ "$1" = "--uninstall" ] || [ "$1" = "-u" ]; then
    echo "=== Đang gỡ bỏ Antigravity Account Switcher ==="
    rm -f "$BIN_DIR/achange"
    rm -f "$APP_DIR/antigravity-switcher.desktop"
    echo "[OK] Đã xóa lệnh $BIN_DIR/achange"
    echo "[OK] Đã xóa desktop shortcut $APP_DIR/antigravity-switcher.desktop"
    echo "Gỡ cài đặt hoàn tất!"
    exit 0
fi

echo "=== Cài đặt Antigravity Account Switcher ==="

# 1. Kiểm tra Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[Lỗi] Không tìm thấy python3 trên hệ thống. Vui lòng cài đặt Python 3.8+."
    exit 1
fi

# 2. Kiểm tra các thư viện hệ thống khuyến nghị
if ! command -v secret-tool >/dev/null 2>&1; then
    echo "[Lưu ý] Chưa tìm thấy 'secret-tool' (GNOME Keyring CLI)."
    echo "       Khuyến nghị cài đặt để hỗ trợ SecretService đầy đủ:"
    echo "       - Debian/Ubuntu: sudo apt install libsecret-tools"
    echo "       - Fedora:        sudo dnf install libsecret"
    echo "       - Arch Linux:    sudo pacman -S libsecret"
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "[Lưu ý] Chưa tìm thấy module 'tkinter' cho giao diện đồ họa."
    echo "       - Debian/Ubuntu: sudo apt install python3-tk"
    echo "       - Fedora:        sudo dnf install python3-tkinter"
    echo "       - Arch Linux:    sudo pacman -S tk"
fi

# 3. Kiểm tra hoặc cài đặt dependencies từ requirements.txt nếu có pip
if [ -f "$BASE_DIR/requirements.txt" ]; then
    if python3 -c "import requests, cryptography" >/dev/null 2>&1; then
        echo "[OK] Các thư viện Python (requests, cryptography) đã sẵn sàng."
    else
        echo "[*] Đang cài đặt các thư viện Python cần thiết..."
        pip3 install -r "$BASE_DIR/requirements.txt" || pip install -r "$BASE_DIR/requirements.txt" || {
            echo "[Cảnh báo] Không thể tự động chạy pip. Bạn có thể tự chạy: pip install -r requirements.txt"
        }
    fi
fi

# 4. Phân quyền thực thi cho main.py
chmod +x "$BASE_DIR/main.py"

# 5. Tạo wrapper script cho lệnh `achange` trong ~/.local/bin
mkdir -p "$BIN_DIR"
cat << EOF > "$BIN_DIR/achange"
#!/usr/bin/env bash
exec /usr/bin/env python3 "$BASE_DIR/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/achange"
echo "[OK] Đã tạo lệnh CLI: $BIN_DIR/achange"

# 6. Tạo Desktop Entry để mở từ Application Menu / Dock của Linux
mkdir -p "$APP_DIR"
cat << EOF > "$APP_DIR/antigravity-switcher.desktop"
[Desktop Entry]
Name=Antigravity Account Switcher
Comment=Chuyển đổi tài khoản Antigravity IDE, agy CLI & Antigravity-x64
Exec=/usr/bin/env python3 "$BASE_DIR/main.py" --gui
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Development;IDE;Utility;
Keywords=antigravity;switch;account;gemini;
EOF
chmod +x "$APP_DIR/antigravity-switcher.desktop"
echo "[OK] Đã tạo biểu tượng ứng dụng: $APP_DIR/antigravity-switcher.desktop"

# 7. Nhắc nhở về PATH nếu chưa có ~/.local/bin
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "[Lưu ý] Thư mục $BIN_DIR chưa có trong PATH của bạn."
    echo "Thêm dòng sau vào ~/.bashrc hoặc ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "=== Cài đặt hoàn tất! ==="
echo "Cách sử dụng:"
echo "  - CLI: gõ lệnh 'achange' trong terminal"
echo "  - GUI: gõ 'achange gui' hoặc mở 'Antigravity Account Switcher' từ menu ứng dụng"
echo "  - Gỡ cài đặt: ./install.sh --uninstall"

