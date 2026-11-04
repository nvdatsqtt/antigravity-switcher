# -*- coding: utf-8 -*-
"""
Bộ kiểm thử tự động toàn diện cho Antigravity Account Switcher.
Bao gồm cả Unit Tests cô lập (Hermetic Tests) chạy trên mọi môi trường (CI / Local)
và Integration Tests có điều kiện nếu môi trường máy chủ có sẵn tài khoản.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import core
from core import (
    SWITCHER_ACCOUNTS_FILE,
    _load_dotenv,
    add_account_by_token,
    add_or_update_account,
    create_oauth_info_proto,
    create_unified_topic_entry,
    decode_jwt_payload,
    encode_len_delim,
    encode_string_field,
    encode_varint,
    encode_varint_field,
    find_antigravity_app_executable,
    find_antigravity_ide_executable,
    get_active_account_email,
    import_from_cockpit,
    load_all_accounts,
    refresh_token_if_needed,
    remove_account,
    save_all_accounts,
    switch_account,
)


class TestProtobufEncoding(unittest.TestCase):
    """Kiểm thử thuật toán mã hóa Protobuf thủ công không dùng protoc."""

    def test_encode_varint(self) -> None:
        """Kiểm tra mã hóa số nguyên Varint chuẩn Protobuf."""
        self.assertEqual(encode_varint(0), b"\x00")
        self.assertEqual(encode_varint(1), b"\x01")
        self.assertEqual(encode_varint(127), b"\x7f")
        self.assertEqual(encode_varint(128), b"\x80\x01")
        self.assertEqual(encode_varint(300), b"\xac\x02")

    def test_encode_len_delim(self) -> None:
        """Kiểm tra trường dạng length-delimited."""
        payload = b"hello"
        encoded = encode_len_delim(1, payload)
        # Tag 1 wire 2 -> 0x0a, len 5 -> 0x05, sau đó là b'hello'
        self.assertEqual(encoded, b"\x0a\x05hello")

    def test_encode_string_field(self) -> None:
        """Kiểm tra mã hóa chuỗi UTF-8."""
        encoded = encode_string_field(2, "Bearer")
        self.assertEqual(encoded, b"\x12\x06Bearer")

    def test_create_oauth_info_proto(self) -> None:
        """Kiểm tra tạo cấu trúc binary protobuf cho oauthTokenInfo."""
        proto = create_oauth_info_proto(
            access_token="test_access",
            refresh_token="test_refresh",
            expiry=1793710000,
            id_token="test_id_token",
        )
        self.assertIsInstance(proto, bytes)
        self.assertGreater(len(proto), 30)
        self.assertIn(b"test_access", proto)
        self.assertIn(b"Bearer", proto)
        self.assertIn(b"test_refresh", proto)
        self.assertIn(b"test_id_token", proto)

    def test_create_unified_topic_entry(self) -> None:
        """Kiểm tra cấu trúc topic base64 entry cho SQLite state sync."""
        proto = create_oauth_info_proto("token1", "token2", 1700000000)
        entry = create_unified_topic_entry("sentinelKeyTest", proto)
        self.assertIsInstance(entry, bytes)
        self.assertIn(b"sentinelKeyTest", entry)


class TestStorageHermetic(unittest.TestCase):
    """Kiểm thử tính năng lưu trữ và nạp tài khoản trong môi trường cô lập tạm thời."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_dir = Path(self.temp_dir.name)
        self.mock_accounts_file = self.mock_dir / "accounts.json"

        # Patch đường dẫn trong core
        self.patch_dir = patch.object(core, "SWITCHER_DIR", self.mock_dir)
        self.patch_file = patch.object(core, "SWITCHER_ACCOUNTS_FILE", self.mock_accounts_file)
        self.patch_dir.start()
        self.patch_file.start()

    def tearDown(self) -> None:
        self.patch_file.stop()
        self.patch_dir.stop()
        self.temp_dir.cleanup()

    def test_save_and_load_accounts_hermetic(self) -> None:
        """Kiểm tra ghi nguyên tử (atomic save) và đọc tài khoản với phân quyền 600."""
        mock_accounts = [
            {
                "id": "acc-1",
                "email": "user1@example.com",
                "name": "User One",
                "last_used": 100,
                "token": {"refresh_token": "rf_1", "access_token": "acc_1"},
            },
            {
                "id": "acc-2",
                "email": "user2@example.com",
                "name": "User Two",
                "last_used": 200,
                "token": {"refresh_token": "rf_2", "access_token": "acc_2"},
            },
        ]

        # 1. Lưu tài khoản
        success = save_all_accounts(mock_accounts, active_email="user2@example.com")
        self.assertTrue(success, "Lưu danh sách tài khoản phải thành công")
        self.assertTrue(self.mock_accounts_file.exists(), "File tài khoản phải được tạo")

        # 2. Kiểm tra phân quyền file 600 (trên POSIX)
        if os.name == "posix":
            mode = oct(self.mock_accounts_file.stat().st_mode & 0o777)
            self.assertEqual(mode, "0o600", "Phân quyền file phải là 0600")

        # 3. Nạp lại và kiểm tra sắp xếp theo last_used giảm dần
        loaded = load_all_accounts()
        self.assertEqual(len(loaded), 2)
        # user2 có last_used = 200 nên phải đứng đầu
        self.assertEqual(loaded[0]["email"], "user2@example.com")
        self.assertEqual(loaded[1]["email"], "user1@example.com")

    def test_decode_jwt_payload(self) -> None:
        """Kiểm tra giải mã payload JWT không phụ thuộc thư viện ngoài."""
        import base64
        payload = {"email": "jwt_test@example.com", "name": "JWT User", "sub": "987654321"}
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
        fake_jwt = f"eyJhbGciOiJSUzI1NiJ9.{payload_b64}.signatureDummy"

        decoded = decode_jwt_payload(fake_jwt)
        self.assertEqual(decoded.get("email"), "jwt_test@example.com")
        self.assertEqual(decoded.get("name"), "JWT User")
        self.assertEqual(decoded.get("sub"), "987654321")

    @patch("requests.post")
    def test_add_account_by_token_success(self, mock_post: MagicMock) -> None:
        """Kiểm tra thêm tài khoản mới bằng Refresh Token thành công."""
        import base64
        jwt_payload = {"email": "new_added@gmail.com", "name": "New User", "sub": "sub_111"}
        payload_b64 = base64.urlsafe_b64encode(json.dumps(jwt_payload).encode("utf-8")).decode("ascii").rstrip("=")
        fake_jwt = f"header.{payload_b64}.sig"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock_access_token_123",
            "expires_in": 3600,
            "id_token": fake_jwt,
        }
        mock_post.return_value = mock_resp

        ok, msg, acc = add_account_by_token("1//dummy_refresh_123")
        self.assertTrue(ok, f"Thêm tài khoản phải thành công: {msg}")
        self.assertIsNotNone(acc)
        self.assertEqual(acc["email"], "new_added@gmail.com")
        self.assertEqual(acc["name"], "New User")

        # Kiểm tra tài khoản đã nằm trong kho lưu trữ
        accounts = load_all_accounts()
        self.assertTrue(any(a["email"] == "new_added@gmail.com" for a in accounts))

    def test_remove_account(self) -> None:
        """Kiểm tra xóa tài khoản theo email và số thứ tự."""
        mock_accounts = [
            {"id": "1", "email": "del1@example.com", "name": "Del 1", "last_used": 10},
            {"id": "2", "email": "del2@example.com", "name": "Del 2", "last_used": 20},
        ]
        save_all_accounts(mock_accounts)

        # Xóa theo email
        ok, msg = remove_account("del1@example.com")
        self.assertTrue(ok)
        loaded = load_all_accounts()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["email"], "del2@example.com")

        # Xóa theo số thứ tự (1)
        ok2, msg2 = remove_account("1")
        self.assertTrue(ok2)
        loaded2 = load_all_accounts()
        self.assertEqual(len(loaded2), 0)

    def test_load_dotenv_hermetic(self) -> None:
        """Kiểm tra đọc file .env cô lập và cập nhật biến môi trường chính xác."""
        env_file = self.mock_dir / ".env"
        env_file.write_text("TEST_ANTIGRAVITY_PORT=9999\nTEST_ANTIGRAVITY_ENV=sandbox\n", encoding="utf-8")

        with patch("core.SWITCHER_DIR", self.mock_dir):
            _load_dotenv()
            self.assertEqual(os.environ.get("TEST_ANTIGRAVITY_PORT"), "9999")
            self.assertEqual(os.environ.get("TEST_ANTIGRAVITY_ENV"), "sandbox")

        # Dọn dẹp biến môi trường test
        os.environ.pop("TEST_ANTIGRAVITY_PORT", None)
        os.environ.pop("TEST_ANTIGRAVITY_ENV", None)


class TestTokenRefresh(unittest.TestCase):
    """Kiểm thử cơ chế làm mới token Google OAuth."""

    @patch("requests.post")
    def test_refresh_token_success(self, mock_post: MagicMock) -> None:
        """Kiểm tra luồng refresh token thành công cập nhật access_token và expiry."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token_xyz",
            "expires_in": 3600,
            "id_token": "new_id_token_123",
        }
        mock_post.return_value = mock_response

        token_input = {"refresh_token": "valid_refresh_token", "access_token": "old_token"}
        updated = refresh_token_if_needed(token_input)

        self.assertEqual(updated["access_token"], "new_access_token_xyz")
        self.assertEqual(updated["id_token"], "new_id_token_123")
        self.assertIn("expiry_timestamp", updated)

    def test_refresh_token_missing_refresh_token(self) -> None:
        """Kiểm tra báo lỗi khi tài khoản không có refresh_token."""
        with self.assertRaises(ValueError):
            refresh_token_if_needed({})


class TestExecutableDiscovery(unittest.TestCase):
    """Kiểm thử tính năng tự động tìm đường dẫn ứng dụng."""

    def test_env_override_ide(self) -> None:
        """Kiểm tra biến môi trường ANTIGRAVITY_IDE_PATH ghi đè chính xác."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("#!/bin/sh\nexit 0")
            temp_path = f.name
        os.chmod(temp_path, 0o755)

        try:
            with patch.dict(os.environ, {"ANTIGRAVITY_IDE_PATH": temp_path}):
                found = find_antigravity_ide_executable()
                self.assertEqual(found, Path(temp_path))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestLiveEnvironment(unittest.TestCase):
    """Các kiểm thử tích hợp thực tế trên máy chạy (bỏ qua nếu không có môi trường)."""

    def test_live_storage_if_present(self) -> None:
        """Kiểm tra kho lưu trữ thực tế nếu máy tính đã cấu hình."""
        if not SWITCHER_ACCOUNTS_FILE.exists():
            self.skipTest("Bỏ qua do chưa cấu hình tài khoản thực tế trên máy host")

        mode = oct(SWITCHER_ACCOUNTS_FILE.stat().st_mode & 0o777)
        self.assertEqual(mode, "0o600")
        accounts = load_all_accounts()
        self.assertGreaterEqual(len(accounts), 1)

    def test_live_active_account_if_keyring_present(self) -> None:
        """Kiểm tra tài khoản active thực tế từ Keyring nếu có."""
        active_email = get_active_account_email()
        if not active_email:
            self.skipTest("Chưa có tài khoản đăng nhập trên GNOME Keyring host")
        self.assertIn("@", active_email)


if __name__ == "__main__":
    unittest.main()
