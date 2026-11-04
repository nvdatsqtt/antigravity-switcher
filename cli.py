# -*- coding: utf-8 -*-
"""
Giao diện dòng lệnh (CLI) cho Antigravity Account Switcher.
Cung cấp lệnh `achange` hỗ trợ chuyển đổi tài khoản nhanh chóng từ terminal.
"""

import sys
from typing import Optional
try:
    from .core import (
        add_account_by_token,
        get_active_account_email,
        import_from_cockpit,
        load_all_accounts,
        login_with_google,
        remove_account,
        switch_account,
    )
except ImportError:
    from core import (
        add_account_by_token,
        get_active_account_email,
        import_from_cockpit,
        load_all_accounts,
        login_with_google,
        remove_account,
        switch_account,
    )


class AnsiColor:
    """Mã màu ANSI hiển thị giao diện terminal."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"


def print_banner() -> None:
    """Hiển thị tiêu đề công cụ."""
    print(f"\n{AnsiColor.CYAN}{AnsiColor.BOLD}===================================================={AnsiColor.RESET}")
    print(f"{AnsiColor.CYAN}{AnsiColor.BOLD}   ANTIGRAVITY ACCOUNT SWITCHER (v1.0){AnsiColor.RESET}")
    print(f"{AnsiColor.DIM}   Hỗ trợ Antigravity IDE, agy CLI & Antigravity-x64{AnsiColor.RESET}")
    print(f"{AnsiColor.CYAN}{AnsiColor.BOLD}===================================================={AnsiColor.RESET}\n")


def list_accounts_cli() -> None:
    """Liệt kê tất cả các tài khoản có trong kho và trạng thái kích hoạt."""
    print_banner()
    accounts = load_all_accounts()
    active_email = get_active_account_email()

    print(f"  {AnsiColor.BOLD}TRẠNG THÁI HIỆN TẠI:{AnsiColor.RESET}")
    if active_email:
        print(f"  [ ACTIVE ] {AnsiColor.GREEN}{AnsiColor.BOLD}{active_email}{AnsiColor.RESET}")
    else:
        print(f"  [ ACTIVE ] {AnsiColor.YELLOW}Chưa xác định / Chưa đăng nhập{AnsiColor.RESET}")

    print(f"\n  {AnsiColor.BOLD}DANH SÁCH TÀI KHOẢN ({len(accounts)}):{AnsiColor.RESET}")
    print(f"  {'-' * 52}")

    if not accounts:
        print(f"  {AnsiColor.RED}(Không tìm thấy tài khoản nào trong kho){AnsiColor.RESET}")
    else:
        for idx, acc in enumerate(accounts, start=1):
            email = acc.get("email", "N/A")
            name = acc.get("name", "")
            is_active = (email == active_email)
            
            if is_active:
                marker = f"{AnsiColor.GREEN}[*]{AnsiColor.RESET}"
                label = f"{AnsiColor.GREEN}{AnsiColor.BOLD}{email}{AnsiColor.RESET}"
                tag = f" {AnsiColor.GREEN}(Đang dùng){AnsiColor.RESET}"
            else:
                marker = f"{AnsiColor.DIM}[ ]{AnsiColor.RESET}"
                label = email
                tag = ""

            name_str = f" {AnsiColor.DIM}({name}){AnsiColor.RESET}" if name and name != email else ""
            print(f"  {idx:02d}. {marker} {label}{name_str}{tag}")

    print(f"  {'-' * 52}")
    print(f"\n  {AnsiColor.BOLD}HƯỚNG DẪN SỬ DỤNG:{AnsiColor.RESET}")
    print(f"  achange <số|email>     : Chuyển tài khoản (nhận ngay cho CLI & lượt mở IDE tiếp theo)")
    print(f"  achange <số> --restart : Chuyển tài khoản & tự động khởi động lại Antigravity IDE")
    print(f"  achange next           : Chuyển sang tài khoản kế tiếp trong danh sách")
    print(f"  achange add            : Đăng nhập & thêm tài khoản mới qua Google OAuth (mở trình duyệt)")
    print(f"  achange add --token <TK>: Thêm tài khoản mới bằng Google Refresh Token")
    print(f"  achange remove <số|mail>: Xóa tài khoản khỏi danh sách")
    print(f"  achange import-cockpit : Nhập tài khoản từ Cockpit Tools cũ (tính năng phụ trợ)")
    print(f"  achange gui            : Mở giao diện đồ họa 1-click")
    print(f"\n{AnsiColor.CYAN}===================================================={AnsiColor.RESET}\n")


def handle_add_account(args: list) -> None:
    """Xử lý lệnh thêm tài khoản mới vào hệ thống."""
    # 1. Trường hợp người dùng truyền Refresh Token trực tiếp
    if "--token" in args or "-t" in args:
        try:
            token_idx = args.index("--token") if "--token" in args else args.index("-t")
            refresh_token = args[token_idx + 1]
        except IndexError:
            print(f"{AnsiColor.RED}[Lỗi] Thiếu giá trị Refresh Token: achange add --token <REFRESH_TOKEN>{AnsiColor.RESET}")
            return

        print("[*] Đang xác thực Refresh Token với Google OAuth...")
        ok, msg, acc = add_account_by_token(refresh_token)
        if ok and acc:
            print(f"{AnsiColor.GREEN}[OK] {msg}{AnsiColor.RESET}")
        else:
            print(f"{AnsiColor.RED}[Lỗi] {msg}{AnsiColor.RESET}")
        return

    # 2. Mặc định: Đăng nhập Google trực tiếp qua trình duyệt
    print(f"\n{AnsiColor.CYAN}{AnsiColor.BOLD}[*] Bắt đầu quy trình đăng nhập Google OAuth...{AnsiColor.RESET}")
    
    def on_url_ready(url: str) -> None:
        print(f"\n  Đang mở trình duyệt để xác thực tài khoản Google.")
        print(f"  Nếu trình duyệt không tự mở, vui lòng mở liên kết sau trong trình duyệt:")
        print(f"  {AnsiColor.CYAN}{url}{AnsiColor.RESET}\n")
        print(f"  {AnsiColor.DIM}Đang chờ phản hồi xác thực từ trình duyệt (tối đa 120s)...{AnsiColor.RESET}")

    ok, msg, new_acc = login_with_google(url_callback=on_url_ready)
    if ok and new_acc:
        print(f"\n{AnsiColor.GREEN}{AnsiColor.BOLD}[OK] {msg}{AnsiColor.RESET}")
        # Hỏi người dùng có muốn chuyển sang tài khoản này ngay không
        try:
            choice = input(f"\nBạn có muốn chuyển sang tài khoản {new_acc.get('email')} ngay bây giờ? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                switch_account(new_acc, restart_ide=False)
        except (KeyboardInterrupt, EOFError):
            pass
    else:
        print(f"\n{AnsiColor.RED}[Lỗi] {msg}{AnsiColor.RESET}")


def handle_remove_account(args: list) -> None:
    """Xử lý lệnh xóa tài khoản khỏi kho lưu trữ."""
    if not args:
        print(f"{AnsiColor.RED}[Lỗi] Vui lòng nhập số thứ tự hoặc email cần xóa: achange remove <số|email>{AnsiColor.RESET}")
        return

    query = args[0]
    ok, msg = remove_account(query)
    if ok:
        print(f"{AnsiColor.GREEN}[OK] {msg}{AnsiColor.RESET}")
    else:
        print(f"{AnsiColor.RED}[Lỗi] {msg}{AnsiColor.RESET}")


def handle_import_cockpit() -> None:
    """Xử lý lệnh nhập tài khoản từ Cockpit Tools cũ."""
    print("[*] Đang kiểm tra và nhập tài khoản từ Cockpit Tools (~/.antigravity_cockpit)...")
    count, msg = import_from_cockpit()
    if count > 0:
        print(f"{AnsiColor.GREEN}[OK] {msg}{AnsiColor.RESET}")
    else:
        print(f"{AnsiColor.YELLOW}[!] {msg}{AnsiColor.RESET}")


def switch_by_query(query: str, restart: bool = False) -> None:
    """
    Chuyển tài khoản theo số thứ tự (index) hoặc địa chỉ email.

    :param query: Chuỗi nhập vào từ CLI (số hoặc email)
    :param restart: Có khởi động lại IDE hay không
    """
    accounts = load_all_accounts()
    if not accounts:
        print(f"{AnsiColor.RED}[Lỗi] Không có tài khoản nào trong hệ thống.{AnsiColor.RESET}")
        return

    target = None

    # 1. Thử phân tích cú pháp dạng số thứ tự (1-based)
    if query.isdigit():
        idx = int(query) - 1
        if 0 <= idx < len(accounts):
            target = accounts[idx]
        else:
            print(f"{AnsiColor.RED}[Lỗi] Số thứ tự không hợp lệ (1 - {len(accounts)}).{AnsiColor.RESET}")
            return
    else:
        # 2. Tìm kiếm theo email
        query_lower = query.lower().strip()
        matches = [a for a in accounts if query_lower in a.get("email", "").lower()]
        if len(matches) == 1:
            target = matches[0]
        elif len(matches) > 1:
            print(f"{AnsiColor.YELLOW}[Cảnh báo] Có nhiều tài khoản khớp với '{query}':{AnsiColor.RESET}")
            for m in matches:
                print(f"  - {m.get('email')}")
            print("Vui lòng nhập chính xác email hoặc dùng số thứ tự.")
            return
        else:
            print(f"{AnsiColor.RED}[Lỗi] Không tìm thấy tài khoản nào khớp với '{query}'.{AnsiColor.RESET}")
            return

    success, msg = switch_account(target, restart_ide=restart)
    if not success:
        print(f"{AnsiColor.RED}[Lỗi] {msg}{AnsiColor.RESET}")


def switch_to_next(restart: bool = False) -> None:
    """Xoay vòng chuyển sang tài khoản kế tiếp."""
    accounts = load_all_accounts()
    if not accounts:
        print(f"{AnsiColor.RED}[Lỗi] Không có tài khoản nào.{AnsiColor.RESET}")
        return

    active_email = get_active_account_email()
    next_idx = 0
    if active_email:
        for idx, a in enumerate(accounts):
            if a.get("email") == active_email:
                next_idx = (idx + 1) % len(accounts)
                break

    target = accounts[next_idx]
    success, msg = switch_account(target, restart_ide=restart)
    if not success:
        print(f"{AnsiColor.RED}[Lỗi] {msg}{AnsiColor.RESET}")


def main_cli() -> None:
    """Hàm điều hướng chính cho CLI."""
    args = sys.argv[1:]
    restart = ("--restart" in args or "-r" in args)
    filtered_args = [a for a in args if a not in ("--restart", "-r")]

    if not filtered_args:
        list_accounts_cli()
        return

    cmd = filtered_args[0].strip()

    if cmd in ("gui", "-g", "--gui"):
        try:
            from .gui import launch_gui
        except ImportError:
            from gui import launch_gui
        launch_gui()
    elif cmd in ("next", "-n", "--next"):
        switch_to_next(restart=restart)
    elif cmd in ("list", "-l", "--list"):
        list_accounts_cli()
    elif cmd in ("status", "-s", "--status"):
        active = get_active_account_email()
        print(f"Active Account: {active or 'None'}")
    elif cmd in ("add", "login", "--add"):
        handle_add_account(filtered_args[1:])
    elif cmd in ("remove", "rm", "delete", "del"):
        handle_remove_account(filtered_args[1:])
    elif cmd in ("import-cockpit", "import_cockpit", "cockpit"):
        handle_import_cockpit()
    else:
        switch_by_query(cmd, restart=restart)


if __name__ == "__main__":
    main_cli()
