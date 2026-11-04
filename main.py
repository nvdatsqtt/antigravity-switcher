#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entrypoint chính cho Antigravity Account Switcher.
Tự động kích hoạt GUI nếu có môi trường đồ họa hoặc thực thi lệnh CLI.
"""

import os
import sys

# Đảm bảo import được module local
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core import load_all_accounts, get_active_account_email
from cli import main_cli


def main() -> None:
    """Điều hướng thực thi: nếu không có cờ lệnh và có DISPLAY thì mở GUI, ngược lại dùng CLI."""
    has_display = bool(os.environ.get("DISPLAY"))
    args = sys.argv[1:]

    # Nếu truyền lệnh cụ thể hoặc không có màn hình hiển thị -> chạy CLI
    if args or not has_display:
        main_cli()
    else:
        # Nếu chỉ nhấp mở biểu tượng hoặc gõ lệnh không kèm cờ -> mở giao diện đồ họa
        try:
            from gui import launch_gui
            launch_gui()
        except Exception as exc:
            print(f"[Cảnh báo] Không thể mở GUI ({exc}), chuyển sang chế độ CLI:")
            main_cli()


if __name__ == "__main__":
    main()

