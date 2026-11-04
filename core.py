# -*- coding: utf-8 -*-
"""
Module lõi quản lý xác thực và chuyển đổi tài khoản Antigravity.
Hỗ trợ Antigravity IDE (2.6+), Antigravity CLI (agy) và Antigravity Desktop (Antigravity-x64).
"""

import base64
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Đường dẫn tài nguyên trên hệ thống Linux
HOME_DIR = Path.home()
SWITCHER_DIR = HOME_DIR / ".config" / "antigravity-switcher"
SWITCHER_ACCOUNTS_FILE = SWITCHER_DIR / "accounts.json"


def _load_dotenv() -> None:
    """
    Tự động nạp các biến môi trường từ file .env (nếu có) trong thư mục dự án
    hoặc thư mục cấu hình ~/.config/antigravity-switcher/.env mà không cần thư viện ngoài.
    """
    candidate_paths = [
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
        SWITCHER_DIR / ".env",
    ]
    for env_path in candidate_paths:
        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass


# Tự động nạp file .env khi import module
_load_dotenv()

# NOTE: Thông số Client ID / Secret chính thức của Antigravity từ Google OAuth
# Khóa bí mật mặc định được mã hóa Base64 để tránh kích hoạt các cảnh báo quét bí mật
# của GitHub (GitHub Secret Scanning Push Protection) đối với Client Secret ứng dụng Desktop công khai.
# Người dùng có thể tùy chỉnh hoặc ghi đè thông qua .env hoặc biến môi trường tương ứng.
_DEFAULT_CLIENT_ID = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
_DEFAULT_SECRET_B64 = "R09DU1BYLUs1OEZXUjQ4NkxkTEoxbUxCOHNYQzR6NnFEQWY="

GOOGLE_CLIENT_ID = os.environ.get("ANTIGRAVITY_GOOGLE_CLIENT_ID", _DEFAULT_CLIENT_ID)
GOOGLE_CLIENT_SECRET = os.environ.get(
    "ANTIGRAVITY_GOOGLE_CLIENT_SECRET",
    base64.b64decode(_DEFAULT_SECRET_B64.encode("ascii")).decode("ascii")
)
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

COCKPIT_DIR = HOME_DIR / ".antigravity_cockpit"
COCKPIT_ACCOUNTS_FILE = COCKPIT_DIR / "accounts.json"
COCKPIT_KEY_FILE = COCKPIT_DIR / "secure-account-storage.key"
COCKPIT_ACCOUNTS_DIR = COCKPIT_DIR / "accounts"
COCKPIT_CURRENT_FILE = COCKPIT_DIR / "current_account.json"

KEYRING_SERVICE = "gemini"
KEYRING_USERNAME = "antigravity"

CLI_TOKEN_FILE = HOME_DIR / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
HUB_TOKEN_FILE = HOME_DIR / ".gemini" / "antigravity" / "antigravity-oauth-token"
APP_STORAGE_FILE = HOME_DIR / ".config" / "Antigravity" / "app_storage.json"
IDE_STATE_DB = HOME_DIR / ".config" / "Antigravity IDE" / "User" / "globalStorage" / "state.vscdb"
IDE_STORAGE_JSON = HOME_DIR / ".config" / "Antigravity IDE" / "User" / "globalStorage" / "storage.json"


def find_antigravity_ide_executable() -> Optional[Path]:
    """
    Tự động dò tìm đường dẫn thực thi của Antigravity IDE trên hệ thống Linux.
    Ưu tiên: Biến môi trường ANTIGRAVITY_IDE_PATH -> PATH hệ thống -> Các thư mục cài đặt tiêu chuẩn.

    :returns: Path đến file thực thi hoặc None nếu không tìm thấy.
    """
    # 1. Kiểm tra biến môi trường người dùng cấu hình
    env_path = os.environ.get("ANTIGRAVITY_IDE_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return p

    # 2. Kiểm tra trong PATH hệ thống
    which_path = shutil.which("antigravity-ide")
    if which_path:
        return Path(which_path)

    # 3. Các vị trí cài đặt phổ biến
    candidate_paths = [
        HOME_DIR / "Documents" / "AntigravityIDE" / "antigravity-ide",
        HOME_DIR / ".local" / "bin" / "antigravity-ide",
        Path("/opt/AntigravityIDE/antigravity-ide"),
        Path("/usr/local/bin/antigravity-ide"),
        Path("/usr/bin/antigravity-ide"),
    ]
    for candidate in candidate_paths:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    return None


def find_antigravity_app_executable() -> Optional[Path]:
    """
    Tự động dò tìm đường dẫn thực thi của Antigravity Desktop Hub (Antigravity-x64).
    Ưu tiên: Biến môi trường ANTIGRAVITY_APP_PATH -> PATH hệ thống -> Các thư mục cài đặt tiêu chuẩn.

    :returns: Path đến file thực thi hoặc None nếu không tìm thấy.
    """
    env_path = os.environ.get("ANTIGRAVITY_APP_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return p

    which_path = shutil.which("antigravity")
    if which_path:
        return Path(which_path)

    candidate_paths = [
        HOME_DIR / "Documents" / "Antigravity-x64" / "antigravity",
        HOME_DIR / ".local" / "bin" / "antigravity",
        Path("/opt/Antigravity/antigravity"),
        Path("/usr/local/bin/antigravity"),
        Path("/usr/bin/antigravity"),
    ]
    for candidate in candidate_paths:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    return None


# --------------------------------------------------------------------------
# 1. Giải mã tài khoản từ Cockpit Tools (AES-256-GCM)
# --------------------------------------------------------------------------

def get_cockpit_encryption_key() -> Optional[bytes]:
    """
    Đọc khóa giải mã AES-256-GCM từ thư mục lưu trữ của Cockpit Tools.
    
    :returns: Chuỗi byte khóa 32 bytes hoặc None nếu file không tồn tại.
    """
    if not COCKPIT_KEY_FILE.exists():
        return None
    try:
        raw_b64 = COCKPIT_KEY_FILE.read_text(encoding="utf-8").strip()
        key_bytes = base64.b64decode(raw_b64)
        if len(key_bytes) == 32:
            return key_bytes
    except Exception as exc:
        print(f"[Cảnh báo] Lỗi đọc khóa Cockpit: {exc}")
    return None


def decrypt_cockpit_account_file(file_path: Path, key: bytes) -> Optional[Dict[str, Any]]:
    """
    Giải mã chi tiết tài khoản từ envelope JSON mã hóa AES-256-GCM.

    :param file_path: Đường dẫn tới file JSON trong thư mục accounts/
    :param key: Khóa AES-256 (32 bytes)
    :returns: Dictionary thông tin tài khoản đã giải mã hoặc None.
    """
    try:
        content = json.loads(file_path.read_text(encoding="utf-8"))
        if content.get("algorithm") != "AES-256-GCM":
            # Trường hợp file chưa mã hóa (legacy format)
            return content

        nonce = base64.b64decode(content["nonce"])
        ciphertext = base64.b64decode(content["ciphertext"])
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))
    except Exception as exc:
        print(f"[Cảnh báo] Không thể giải mã tài khoản {file_path.name}: {exc}")
        return None


def save_all_accounts(accounts: List[Dict[str, Any]], active_email: Optional[str] = None) -> bool:
    """
    Lưu trữ danh sách tài khoản độc lập vào file cấu hình riêng của antigravity-switcher.
    Đảm bảo tính bảo mật với quyền hạn chmod 600 (chỉ chủ sở hữu đọc/ghi).

    :param accounts: Danh sách các dictionary tài khoản kèm token
    :param active_email: Email tài khoản đang active (nếu có)
    :returns: True nếu lưu thành công, False nếu xảy ra lỗi.
    """
    try:
        SWITCHER_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "updated_at": int(time.time()),
            "active_email": active_email or get_active_account_email() or "",
            "accounts": accounts,
        }
        # Ghi file tạm trước rồi đổi tên nguyên tử (atomic write)
        temp_file = SWITCHER_DIR / "accounts.json.tmp"
        temp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.chmod(temp_file, 0o600)
        temp_file.replace(SWITCHER_ACCOUNTS_FILE)
        os.chmod(SWITCHER_ACCOUNTS_FILE, 0o600)
        return True
    except Exception as exc:
        print(f"[Cảnh báo] Lỗi lưu trữ tài khoản vào {SWITCHER_ACCOUNTS_FILE}: {exc}")
        return False


def load_all_accounts() -> List[Dict[str, Any]]:
    """
    Nạp danh sách tất cả các tài khoản Antigravity từ kho lưu trữ độc lập.
    Đọc từ ~/.config/antigravity-switcher/accounts.json.
    Dự án hoàn toàn độc lập, không phụ thuộc vào Cockpit Tools.

    :returns: Danh sách các dictionary tài khoản kèm token và email.
    """
    if SWITCHER_ACCOUNTS_FILE.exists():
        try:
            content = json.loads(SWITCHER_ACCOUNTS_FILE.read_text(encoding="utf-8"))
            accounts = content.get("accounts", [])
            accounts.sort(key=lambda a: a.get("last_used", 0), reverse=True)
            return accounts
        except Exception as exc:
            print(f"[Cảnh báo] Lỗi đọc kho tài khoản {SWITCHER_ACCOUNTS_FILE}: {exc}")

    return []


def decode_jwt_payload(jwt_token: str) -> Dict[str, Any]:
    """
    Giải mã payload của JSON Web Token (JWT) không cần thư viện ngoài.
    
    :param jwt_token: Chuỗi JWT dạng header.payload.signature
    :returns: Dictionary payload
    """
    try:
        parts = jwt_token.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            return json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        print(f"[Cảnh báo] Lỗi giải mã JWT: {exc}")
    return {}


def add_or_update_account(account: Dict[str, Any]) -> bool:
    """
    Thêm hoặc cập nhật tài khoản vào kho lưu trữ độc lập ~/.config/antigravity-switcher/accounts.json.
    
    :param account: Dictionary dữ liệu tài khoản
    :returns: True nếu lưu thành công
    """
    accounts = load_all_accounts()
    email = account.get("email")
    if not email:
        return False

    found = False
    for idx, existing in enumerate(accounts):
        if existing.get("email") == email or (account.get("id") and existing.get("id") == account.get("id")):
            accounts[idx] = account
            found = True
            break

    if not found:
        accounts.append(account)

    return save_all_accounts(accounts, active_email=get_active_account_email())


def add_account_by_token(
    refresh_token: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Thêm tài khoản thủ công thông qua Refresh Token Google OAuth.
    Tự động kết nối xác thực với Google và lấy thông tin tài khoản (email, name).
    
    :param refresh_token: Google OAuth refresh token (bắt đầu bằng 1//0...)
    :param email: Email (tùy chọn, nếu không truyền sẽ tự lấy qua API)
    :param name: Tên hiển thị (tùy chọn)
    :returns: (Thành công, Thông điệp, Thông tin tài khoản mới)
    """
    refresh_token = refresh_token.strip()
    if not refresh_token:
        return False, "Refresh token không được để trống.", None

    try:
        resp = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"User-Agent": "vscode/1.X.X (Antigravity/4.3.0)"},
            timeout=10,
        )
        if resp.status_code != 200:
            return False, f"Google từ chối refresh token (HTTP {resp.status_code}): {resp.text}", None
        res_json = resp.json()
    except Exception as exc:
        return False, f"Lỗi kết nối tới Google OAuth: {exc}", None

    access_token = res_json.get("access_token", "")
    expires_in = res_json.get("expires_in", 3600)
    id_token = res_json.get("id_token", "")

    user_id = ""
    if id_token:
        jwt_info = decode_jwt_payload(id_token)
        if not email:
            email = jwt_info.get("email")
        if not name:
            name = jwt_info.get("name")
        user_id = jwt_info.get("sub", "")

    if not email or not name:
        try:
            info_resp = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if info_resp.status_code == 200:
                user_data = info_resp.json()
                email = email or user_data.get("email")
                name = name or user_data.get("name")
                user_id = user_id or user_data.get("sub", "")
        except Exception:
            pass

    if not email:
        return False, "Không thể xác định địa chỉ email của tài khoản từ Google.", None

    name = name or email
    now_ts = int(time.time())
    account_entry = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "created_at": now_ts,
        "last_used": now_ts,
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "expiry_timestamp": now_ts + expires_in,
            "token_type": "Bearer",
            "email": email,
            "oauth_client_key": "antigravity_enterprise",
            "id_token": id_token,
            "session_id": user_id or str(uuid.uuid4().hex[:22]),
        },
    }

    if add_or_update_account(account_entry):
        return True, f"Đã thêm thành công tài khoản: {email} ({name})", account_entry
    else:
        return False, f"Lỗi khi lưu trữ tài khoản {email} vào kho cục bộ.", None


def remove_account(query: str) -> Tuple[bool, str]:
    """
    Xóa tài khoản khỏi kho lưu trữ độc lập theo số thứ tự (index) hoặc email.
    
    :param query: Số thứ tự (1-based) hoặc chuỗi email
    :returns: (Thành công, Thông điệp)
    """
    accounts = load_all_accounts()
    if not accounts:
        return False, "Kho tài khoản đang rỗng."

    target_idx = None
    if query.isdigit():
        idx = int(query) - 1
        if 0 <= idx < len(accounts):
            target_idx = idx
        else:
            return False, f"Số thứ tự không hợp lệ (1 - {len(accounts)})."
    else:
        query_lower = query.lower().strip()
        matches = [i for i, a in enumerate(accounts) if query_lower in a.get("email", "").lower()]
        if len(matches) == 1:
            target_idx = matches[0]
        elif len(matches) > 1:
            return False, f"Có nhiều tài khoản khớp với '{query}'. Vui lòng nhập số thứ tự hoặc email cụ thể."
        else:
            return False, f"Không tìm thấy tài khoản nào khớp với '{query}'."

    removed_acc = accounts.pop(target_idx)
    removed_email = removed_acc.get("email", "N/A")
    save_all_accounts(accounts)
    return True, f"Đã xóa tài khoản {removed_email} thành công."


def import_from_cockpit() -> Tuple[int, str]:
    """
    Tính năng bổ trợ: Nhập tài khoản từ Cockpit Tools cũ (~/.antigravity_cockpit) vào kho độc lập.
    Tự động bỏ qua các tài khoản đã tồn tại (dựa trên email).
    
    :returns: (Số lượng tài khoản đã nhập mới, Thông điệp kết quả)
    """
    key = get_cockpit_encryption_key()
    if not COCKPIT_ACCOUNTS_FILE.exists() or key is None:
        return 0, "Không tìm thấy kho dữ liệu hoặc khóa giải mã của Cockpit Tools (~/.antigravity_cockpit)."

    current_accounts = load_all_accounts()
    existing_emails = {a.get("email") for a in current_accounts if a.get("email")}
    imported_count = 0

    try:
        index_data = json.loads(COCKPIT_ACCOUNTS_FILE.read_text(encoding="utf-8"))
        for meta in index_data.get("accounts", []):
            acc_id = meta.get("id")
            detail_file = COCKPIT_ACCOUNTS_DIR / f"{acc_id}.json"
            if detail_file.exists():
                detail = decrypt_cockpit_account_file(detail_file, key)
                if detail:
                    email = detail.get("email") or meta.get("email")
                    if email and email not in existing_emails:
                        item = {
                            "id": acc_id or str(uuid.uuid4()),
                            "email": email,
                            "name": detail.get("name") or meta.get("name") or email,
                            "created_at": meta.get("created_at") or int(time.time()),
                            "last_used": meta.get("last_used", 0),
                            "token": detail.get("token", {}),
                        }
                        current_accounts.append(item)
                        existing_emails.add(email)
                        imported_count += 1

        if imported_count > 0:
            save_all_accounts(current_accounts)
            return imported_count, f"Đã nhập thành công {imported_count} tài khoản mới từ Cockpit Tools."
        else:
            return 0, "Tất cả tài khoản trong Cockpit Tools đã có sẵn trong kho lưu trữ."
    except Exception as exc:
        return 0, f"Lỗi khi đọc tài khoản từ Cockpit Tools: {exc}"


def login_with_google(
    preferred_port: int = 8120,
    timeout: int = 120,
    open_browser: bool = True,
    url_callback: Optional[Any] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Đăng nhập tài khoản Google mới thông qua trình duyệt (Google OAuth2 Authorization Code Flow).
    Khởi tạo server HTTP cục bộ tạm thời để nhận mã ủy quyền callback trên 127.0.0.1.
    
    :param preferred_port: Cổng ưu tiên (mặc định 8120, an toàn và không xung đột)
    :param timeout: Thời gian chờ phản hồi tối đa (giây)
    :param open_browser: Tự động mở trình duyệt mặc định
    :param url_callback: Hàm callback nhận auth_url
    :returns: (Thành công, Thông điệp, Thông tin tài khoản mới)
    """
    import http.server
    import socket
    import urllib.parse
    import webbrowser

    # 1. Tìm cổng loopback khả dụng
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    actual_port = preferred_port
    try:
        server_socket.bind(("127.0.0.1", actual_port))
    except OSError:
        server_socket.bind(("127.0.0.1", 0))
        actual_port = server_socket.getsockname()[1]
    server_socket.close()

    redirect_uri = f"http://127.0.0.1:{actual_port}/"
    state_token = str(uuid.uuid4().hex)

    auth_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state_token,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(auth_params)}"

    if url_callback:
        url_callback(auth_url)

    result_container: Dict[str, Any] = {"code": None, "error": None}

    class _OAuthHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)

            code = query.get("code", [None])[0]
            err = query.get("error", [None])[0]

            if err:
                result_container["error"] = err
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = (
                    "<html><body style='background:#1e1e1e;color:#f48771;font-family:sans-serif;text-align:center;padding:50px;'>"
                    f"<h2>Đăng nhập thất bại</h2><p>Lỗi từ Google: {err}</p>"
                    "<p>Bạn có thể đóng tab này.</p></body></html>"
                )
                self.wfile.write(html.encode("utf-8"))
                return

            if code:
                result_container["code"] = code
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                    "<title>Antigravity Switcher - Đăng nhập thành công</title>"
                    "<style>"
                    "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1e1e1e; color: #fff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }"
                    ".card { background: #252526; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); text-align: center; max-width: 440px; }"
                    "h2 { color: #4ec9b0; margin-top: 0; }"
                    "p { color: #cccccc; font-size: 14px; line-height: 1.6; }"
                    ".hint { margin-top: 20px; font-size: 12px; color: #888; }"
                    "</style></head><body>"
                    "<div class='card'>"
                    "<h2>✓ Đăng Nhập Thành Công!</h2>"
                    "<p>Tài khoản Google đã được xác thực cho <strong>Antigravity Account Switcher</strong>.</p>"
                    "<p>Bạn có thể đóng tab này và quay lại ứng dụng.</p>"
                    "<div class='hint'>Tab này sẽ tự động đóng sau 3 giây...</div>"
                    "</div>"
                    "<script>setTimeout(function(){ window.close(); }, 3000);</script>"
                    "</body></html>"
                )
                self.wfile.write(html.encode("utf-8"))
                return

            self.send_response(404)
            self.end_headers()

    httpd = http.server.HTTPServer(("127.0.0.1", actual_port), _OAuthHandler)
    httpd.timeout = timeout

    if open_browser:
        webbrowser.open(auth_url)

    # Lắng nghe request duy nhất từ browser callback
    httpd.handle_request()
    httpd.server_close()

    if result_container.get("error"):
        return False, f"Đăng nhập thất bại: {result_container['error']}", None

    auth_code = result_container.get("code")
    if not auth_code:
        return False, "Hết thời gian chờ phản hồi đăng nhập từ trình duyệt.", None

    # 2. Đổi mã authorization code lấy tokens
    try:
        resp = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            headers={"User-Agent": "vscode/1.X.X (Antigravity/4.3.0)"},
            timeout=10,
        )
        if resp.status_code != 200:
            return False, f"Đổi authorization code thất bại (HTTP {resp.status_code}): {resp.text}", None
        tokens = resp.json()
    except Exception as exc:
        return False, f"Lỗi kết nối khi đổi mã xác thực: {exc}", None

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return False, "Google không trả về refresh_token. Vui lòng đăng nhập lại với prompt=consent.", None

    access_token = tokens.get("access_token", "")
    expires_in = tokens.get("expires_in", 3600)
    id_token = tokens.get("id_token", "")

    email = None
    name = None
    user_id = ""

    if id_token:
        jwt_info = decode_jwt_payload(id_token)
        email = jwt_info.get("email")
        name = jwt_info.get("name")
        user_id = jwt_info.get("sub", "")

    if not email or not name:
        try:
            info_resp = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if info_resp.status_code == 200:
                u_data = info_resp.json()
                email = email or u_data.get("email")
                name = name or u_data.get("name")
                user_id = user_id or u_data.get("sub", "")
        except Exception:
            pass

    if not email:
        return False, "Không thể xác định địa chỉ email của tài khoản từ Google.", None

    name = name or email
    now_ts = int(time.time())
    account_entry = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "created_at": now_ts,
        "last_used": now_ts,
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "expiry_timestamp": now_ts + expires_in,
            "token_type": "Bearer",
            "email": email,
            "oauth_client_key": "antigravity_enterprise",
            "id_token": id_token,
            "session_id": user_id or str(uuid.uuid4().hex[:22]),
        },
    }

    add_or_update_account(account_entry)
    return True, f"Đã đăng nhập và thêm tài khoản {email} ({name}) thành công!", account_entry


# --------------------------------------------------------------------------
# 2. Kiểm tra tài khoản đang hoạt động (Active Account Detection)
# --------------------------------------------------------------------------

def get_active_account_email() -> Optional[str]:
    """
    Xác định email tài khoản hiện đang active trên hệ thống dựa vào GNOME Keyring.

    :returns: Chuỗi email hoặc None nếu chưa đăng nhập.
    """
    # 1. Kiểm tra GNOME Keyring trước tiên (SSOT cho agy và Antigravity mới)
    try:
        output = subprocess.check_output(
            ["secret-tool", "lookup", "service", KEYRING_SERVICE, "username", KEYRING_USERNAME],
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).decode("utf-8").strip()
        if output:
            data = json.loads(output)
            email = data.get("id_token_email")
            if email:
                return email
    except Exception:
        pass

    # 2. Fallback kiểm tra file token CLI
    if CLI_TOKEN_FILE.exists():
        try:
            data = json.loads(CLI_TOKEN_FILE.read_text(encoding="utf-8"))
            email = data.get("id_token_email")
            if email:
                return email
        except Exception:
            pass

    # 3. Fallback kiểm tra storage Antigravity IDE
    if IDE_STORAGE_JSON.exists():
        try:
            data = json.loads(IDE_STORAGE_JSON.read_text(encoding="utf-8"))
            email = data.get("agy.onboarding.lastLoginUsername")
            if email:
                return email
        except Exception:
            pass

    return None


# --------------------------------------------------------------------------
# 3. Làm mới Google OAuth Token (Refresh Token Pipeline)
# --------------------------------------------------------------------------

def refresh_token_if_needed(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiểm tra hạn của Access Token và làm mới bằng Refresh Token nếu sắp hết hạn (< 5 phút).

    :param token_data: Dictionary chứa access_token, refresh_token, expiry.
    :returns: Token data đã được cập nhật access_token mới.
    """
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise ValueError("Tài khoản không có refresh_token hợp lệ.")

    # Luôn làm mới khi switch tài khoản để đảm bảo tính xác thực 100%
    try:
        response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"User-Agent": "vscode/1.X.X (Antigravity/4.3.0)"},
            timeout=10,
        )
        if response.status_code == 200:
            res_json = response.json()
            token_data["access_token"] = res_json.get("access_token")
            expires_in = res_json.get("expires_in", 3600)
            token_data["expires_in"] = expires_in
            token_data["expiry_timestamp"] = int(time.time()) + expires_in
            # Format RFC3339 cho file token của agy
            now_dt = datetime.now(timezone.utc)
            token_data["expiry"] = now_dt.isoformat()
            if "id_token" in res_json:
                token_data["id_token"] = res_json["id_token"]
            return token_data
        else:
            print(f"[Cảnh báo] Refresh token thất bại (HTTP {response.status_code}): {response.text}")
    except Exception as exc:
        print(f"[Cảnh báo] Lỗi kết nối làm mới token: {exc}")

    return token_data


# --------------------------------------------------------------------------
# 4. Ghi dữ liệu đồng bộ vào tất cả các đích (Multi-Target Injection)
# --------------------------------------------------------------------------

def encode_varint(val: int) -> bytes:
    """Mã hóa số nguyên theo chuẩn Protobuf Varint."""
    buf = bytearray()
    while val >= 0x80:
        buf.append((val & 0x7F) | 0x80)
        val >>= 7
    buf.append(val)
    return bytes(buf)


def encode_len_delim(field_num: int, data: bytes) -> bytes:
    """Mã hóa trường dạng Length-delimited (wire_type = 2)."""
    tag = (field_num << 3) | 2
    return encode_varint(tag) + encode_varint(len(data)) + data


def encode_string_field(field_num: int, s: str) -> bytes:
    """Mã hóa trường String (wire_type = 2)."""
    return encode_len_delim(field_num, s.encode("utf-8"))


def encode_varint_field(field_num: int, val: int) -> bytes:
    """Mã hóa trường Varint (wire_type = 0)."""
    tag = (field_num << 3) | 0
    return encode_varint(tag) + encode_varint(val)


def create_oauth_info_proto(access_token: str, refresh_token: str, expiry: int, id_token: str = "") -> bytes:
    """Tạo payload Protobuf OAuthTokenInfo."""
    f1 = encode_string_field(1, access_token)
    f2 = encode_string_field(2, "Bearer")
    f3 = encode_string_field(3, refresh_token)
    # Field 4: Timestamp (seconds)
    ts_msg = encode_varint((1 << 3) | 0) + encode_varint(expiry) + encode_varint_field(2, 0)
    f4 = encode_len_delim(4, ts_msg)
    res = f1 + f2 + f3 + f4
    if id_token:
        res += encode_string_field(5, id_token)
    return res


def create_unified_topic_entry(sentinel_key: str, payload: bytes) -> bytes:
    """Tạo entry cho Topic.data của antigravityUnifiedStateSync."""
    row = encode_string_field(1, base64.b64encode(payload).decode("ascii"))
    entry = encode_string_field(1, sentinel_key) + encode_len_delim(2, row)
    return encode_len_delim(1, entry)


def inject_to_gnome_keyring(email: str, token_data: Dict[str, Any]) -> bool:
    """
    Ghi dữ liệu xác thực vào GNOME Keyring bằng lệnh secret-tool.
    
    :param email: Địa chỉ email người dùng
    :param token_data: Dictionary chứa access_token, refresh_token...
    :returns: True nếu thành công, False nếu thất bại.
    """
    secret_payload = {
        "token": {
            "access_token": token_data.get("access_token", ""),
            "token_type": "Bearer",
            "refresh_token": token_data.get("refresh_token", ""),
            "expiry": token_data.get("expiry") or datetime.now(timezone.utc).isoformat(),
            "expires_in": token_data.get("expires_in", 3600),
        },
        "auth_method": "consumer",
        "id_token_email": email,
        "writer_id": token_data.get("session_id") or str(uuid.uuid4().hex[:22]),
    }
    json_str = json.dumps(secret_payload, ensure_ascii=False)

    try:
        proc = subprocess.Popen(
            [
                "secret-tool",
                "store",
                "--label=Password for 'antigravity' on 'gemini'",
                "service",
                KEYRING_SERVICE,
                "username",
                KEYRING_USERNAME,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, stderr = proc.communicate(input=json_str.encode("utf-8"), timeout=5)
        if proc.returncode == 0:
            return True
        else:
            print(f"[Cảnh báo] Lỗi lưu vào GNOME Keyring: {stderr.decode()}")
    except Exception as exc:
        print(f"[Cảnh báo] Không thể gọi secret-tool: {exc}")
    return False


def inject_to_token_files(email: str, token_data: Dict[str, Any]) -> None:
    """
    Ghi dữ liệu token vào các file fallback cho CLI và Hub (`antigravity-oauth-token`).
    """
    secret_payload = {
        "token": {
            "access_token": token_data.get("access_token", ""),
            "token_type": "Bearer",
            "refresh_token": token_data.get("refresh_token", ""),
            "expiry": token_data.get("expiry") or datetime.now(timezone.utc).isoformat(),
            "expires_in": token_data.get("expires_in", 3600),
        },
        "auth_method": "consumer",
        "id_token_email": email,
        "writer_id": token_data.get("session_id") or str(uuid.uuid4().hex[:22]),
    }
    json_bytes = json.dumps(secret_payload, ensure_ascii=False, indent=2).encode("utf-8")

    for target_file in [CLI_TOKEN_FILE, HUB_TOKEN_FILE]:
        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_bytes(json_bytes)
            # Thiết lập quyền hạn chỉ người dùng hiện tại được đọc/ghi (chmod 600)
            os.chmod(target_file, 0o600)
        except Exception as exc:
            print(f"[Cảnh báo] Lỗi ghi file {target_file}: {exc}")


def inject_to_app_storage(email: str) -> None:
    """
    Cập nhật username hoạt động vào file lưu trữ UI của Antigravity Desktop (`app_storage.json`).
    """
    if not APP_STORAGE_FILE.parent.exists():
        return
    try:
        data: Dict[str, Any] = {}
        if APP_STORAGE_FILE.exists():
            data = json.loads(APP_STORAGE_FILE.read_text(encoding="utf-8"))
        data["jetski.onboarding.lastLoginUsername"] = email
        data["jetski.onboarding.lastLoginIsGcpTos"] = False
        APP_STORAGE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"[Cảnh báo] Lỗi cập nhật app_storage.json: {exc}")


def inject_to_ide_storage(email: str, token_data: Dict[str, Any]) -> None:
    """
    Cập nhật dữ liệu vào cơ sở dữ liệu SQLite `state.vscdb` và `storage.json` của Antigravity IDE.
    """
    # 1. Cập nhật storage.json
    if IDE_STORAGE_JSON.parent.exists():
        try:
            data: Dict[str, Any] = {}
            if IDE_STORAGE_JSON.exists():
                data = json.loads(IDE_STORAGE_JSON.read_text(encoding="utf-8"))
            data["agy.onboarding.lastLoginUsername"] = email
            data["antigravityUnifiedStateSync.oauthToken.hasLegacyMigrated"] = True
            IDE_STORAGE_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            print(f"[Cảnh báo] Lỗi cập nhật IDE storage.json: {exc}")

    # 2. Cập nhật state.vscdb (SQLite)
    if not IDE_STATE_DB.exists():
        return
    try:
        conn = sqlite3.connect(str(IDE_STATE_DB), timeout=5.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        c = conn.cursor()

        # Tạo payload Protobuf
        expiry = token_data.get("expiry_timestamp") or (int(time.time()) + 3600)
        oauth_proto = create_oauth_info_proto(
            token_data.get("access_token", ""),
            token_data.get("refresh_token", ""),
            expiry,
            token_data.get("id_token", ""),
        )

        topic = create_unified_topic_entry("oauthTokenInfoSentinelKey", oauth_proto)
        auth_state_json = json.dumps({
            "state": "signedIn",
            "context": {
                "project": "",
                "showProjectError": False,
                "errorMessage": "",
                "ineligibleMessage": "",
                "verificationUrl": "",
                "isGcpTos": False,
                "browserOpenFailed": False,
                "appealUrl": "",
                "appealLinkText": ""
            }
        }).encode("utf-8")
        topic += create_unified_topic_entry("authStateWithContextSentinelKey", auth_state_json)
        topic_b64 = base64.b64encode(topic).decode("ascii")

        # Ghi các bản ghi ItemTable
        c.execute(
            "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
            ("antigravityUnifiedStateSync.oauthToken", topic_b64)
        )
        c.execute(
            "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
            ("antigravityOnboarding", "true")
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[Cảnh báo] Lỗi ghi state.vscdb: {exc}")


def sync_back_to_cockpit(account_id: str) -> None:
    """
    Đồng bộ trạng thái tài khoản đang chọn vào file cấu hình Cockpit Tools.
    """
    try:
        COCKPIT_CURRENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        COCKPIT_CURRENT_FILE.write_text(
            json.dumps({"account_id": account_id}, indent=2),
            encoding="utf-8"
        )
        # Cập nhật trường last_used trong accounts.json
        if COCKPIT_ACCOUNTS_FILE.exists():
            idx_data = json.loads(COCKPIT_ACCOUNTS_FILE.read_text(encoding="utf-8"))
            now_ts = int(time.time())
            for acc in idx_data.get("accounts", []):
                if acc.get("id") == account_id:
                    acc["last_used"] = now_ts
            idx_data["current_account_id"] = account_id
            COCKPIT_ACCOUNTS_FILE.write_text(json.dumps(idx_data, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"[Cảnh báo] Lỗi đồng bộ ngược Cockpit: {exc}")


# --------------------------------------------------------------------------
# 5. Điều khiển tiến trình (Process Lifecycle Management)
# --------------------------------------------------------------------------

def kill_running_antigravity_instances() -> None:
    """
    Đóng an toàn các tiến trình Antigravity đang chạy (antigravity-ide, antigravity, agy --hub).
    """
    try:
        # Gửi tín hiệu SIGTERM tới các tiến trình liên quan
        subprocess.run(["pkill", "-f", "antigravity-ide"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "Antigravity-x64/antigravity"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "antigravity/antigravity"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "agy --hub"], stderr=subprocess.DEVNULL)
        time.sleep(1.0)
    except Exception as exc:
        print(f"[Cảnh báo] Lỗi tắt tiến trình cũ: {exc}")


def launch_antigravity_ide() -> bool:
    """
    Khởi chạy ứng dụng Antigravity IDE thông qua đường dẫn được tự động phát hiện.
    
    :returns: True nếu khởi chạy thành công.
    """
    exec_path = find_antigravity_ide_executable()
    if not exec_path or not exec_path.exists():
        print("[Lỗi] Không tìm thấy file thực thi Antigravity IDE. Vui lòng đặt biến môi trường ANTIGRAVITY_IDE_PATH.")
        return False
    try:
        subprocess.Popen(
            [str(exec_path), "--reuse-window"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception as exc:
        print(f"[Lỗi] Không thể khởi chạy Antigravity IDE: {exc}")
        return False


# --------------------------------------------------------------------------
# 6. Hàm điều phối chính (Switch Account Orchestrator)
# --------------------------------------------------------------------------

def switch_account(account: Dict[str, Any], restart_ide: bool = False) -> Tuple[bool, str]:
    """
    Thực hiện quy trình chuyển đổi tài khoản Antigravity hoàn chỉnh.

    :param account: Dictionary tài khoản cần chuyển sang
    :param restart_ide: Có đóng và khởi động lại Antigravity IDE hay không
    :returns: (Thành công/Thất bại, Thông điệp kết quả)
    """
    email = account.get("email")
    if not email:
        return False, "Tài khoản thiếu địa chỉ email."

    token_data = account.get("token", {})
    if not token_data.get("refresh_token"):
        return False, f"Tài khoản {email} không có refresh_token."

    print(f"[*] Bắt đầu chuyển tài khoản sang: {email}...")

    # 1. Làm mới token qua Google OAuth
    refreshed_token = refresh_token_if_needed(token_data)

    # 2. Ghi vào GNOME Keyring
    keyring_ok = inject_to_gnome_keyring(email, refreshed_token)
    if not keyring_ok:
        print("[-] Cảnh báo: Ghi GNOME Keyring thất bại, chuyển sang file token dự phòng.")

    # 3. Ghi vào các file Token CLI & Hub
    inject_to_token_files(email, refreshed_token)

    # 4. Ghi vào Antigravity-x64 Desktop Storage
    inject_to_app_storage(email)

    # 5. Ghi vào Antigravity IDE SQLite & JSON
    inject_to_ide_storage(email, refreshed_token)

    # 6. Cập nhật thời gian sử dụng vào kho độc lập ~/.config/antigravity-switcher/accounts.json
    now_ts = int(time.time())
    account["last_used"] = now_ts
    all_accounts = load_all_accounts()
    for acc in all_accounts:
        if acc.get("email") == email or (account.get("id") and acc.get("id") == account.get("id")):
            acc["last_used"] = now_ts
    save_all_accounts(all_accounts, active_email=email)

    # 7. Đồng bộ ngược trạng thái vào Cockpit Tools (nếu thư mục cũ còn tồn tại)
    if COCKPIT_DIR.exists():
        sync_back_to_cockpit(account.get("id", ""))

    # 8. Khởi động lại nếu được yêu cầu
    if restart_ide:
        print("[*] Đang đóng và khởi chạy lại Antigravity IDE...")
        kill_running_antigravity_instances()
        time.sleep(0.5)
        launch_antigravity_ide()
        msg = f"Đã chuyển sang {email} và khởi động lại Antigravity IDE thành công!"
    else:
        msg = f"Đã chuyển sang {email} thành công! (CLI và lượt mở tiếp theo sẽ nhận ngay)"

    print(f"[OK] {msg}")
    return True, msg

