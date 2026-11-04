# -*- coding: utf-8 -*-
"""
Giao diện đồ họa (GUI) cho Antigravity Account Switcher.
Xây dựng trên nền Tkinter Dark Theme, cho phép chuyển đổi tài khoản 1-click.
"""

import sys
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional

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


class AntigravitySwitcherApp(tk.Tk):
    """Cửa sổ chính của ứng dụng Antigravity Account Switcher."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Antigravity Account Switcher")
        self.geometry("880x560")
        self.minsize(760, 480)

        # Cấu hình màu sắc giao diện Dark Theme
        self.bg_main = "#1e1e1e"
        self.bg_panel = "#252526"
        self.bg_card = "#2d2d2d"
        self.fg_primary = "#ffffff"
        self.fg_secondary = "#9d9d9d"
        self.color_active = "#4ec9b0"
        self.color_accent = "#0e639c"
        self.color_accent_hover = "#1177bb"
        self.color_restart = "#2d7d46"

        self.configure(bg=self.bg_main)
        self.accounts: List[Dict[str, Any]] = []
        self.active_email: Optional[str] = None
        self.auto_restart_var = tk.BooleanVar(value=False)

        self._setup_styles()
        self._create_widgets()
        self._center_window()
        self.refresh_data()

    def _center_window(self) -> None:
        """Đưa cửa sổ ra chính giữa màn hình."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_styles(self) -> None:
        """Cấu hình style cho các widget ttk theo phong cách Dark Mode."""
        style = ttk.Style(self)
        style.theme_use("clam")

        # Cấu hình Treeview (Bảng danh sách tài khoản)
        style.configure(
            "Treeview",
            background=self.bg_panel,
            foreground=self.fg_primary,
            fieldbackground=self.bg_panel,
            borderwidth=0,
            rowheight=32,
            font=("Ubuntu", 10),
        )
        style.configure(
            "Treeview.Heading",
            background=self.bg_card,
            foreground=self.fg_primary,
            relief="flat",
            font=("Ubuntu", 10, "bold"),
            padding=(8, 6),
        )
        style.map(
            "Treeview",
            background=[("selected", "#094771")],
            foreground=[("selected", "#ffffff")],
        )

        # Cấu hình Scrollbar
        style.configure(
            "Vertical.TScrollbar",
            background=self.bg_card,
            troughcolor=self.bg_main,
            borderwidth=0,
            arrowsize=12,
        )

    def _create_widgets(self) -> None:
        """Tạo các thành phần giao diện người dùng."""
        # --- Khung tiêu đề & Trạng thái tài khoản hiện tại ---
        header_frame = tk.Frame(self, bg=self.bg_panel, padx=20, pady=16)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_label = tk.Label(
            header_frame,
            text="Antigravity Account Switcher",
            font=("Ubuntu", 14, "bold"),
            fg=self.fg_primary,
            bg=self.bg_panel,
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            header_frame,
            text="Chuyển đổi tài khoản nhanh chóng cho Antigravity IDE, agy CLI & Antigravity-x64",
            font=("Ubuntu", 9),
            fg=self.fg_secondary,
            bg=self.bg_panel,
        )
        subtitle_label.pack(anchor="w", pady=(2, 10))

        # Card hiển thị tài khoản đang hoạt động
        self.status_card = tk.Frame(header_frame, bg=self.bg_card, padx=14, pady=10)
        self.status_card.pack(fill=tk.X)

        self.active_indicator = tk.Label(
            self.status_card,
            text="●",
            font=("Ubuntu", 14),
            fg=self.color_active,
            bg=self.bg_card,
        )
        self.active_indicator.pack(side=tk.LEFT, padx=(0, 8))

        self.active_label = tk.Label(
            self.status_card,
            text="Đang sử dụng: Đang tải...",
            font=("Ubuntu", 11, "bold"),
            fg=self.color_active,
            bg=self.bg_card,
        )
        self.active_label.pack(side=tk.LEFT)

        # --- Thanh tìm kiếm ---
        search_frame = tk.Frame(self, bg=self.bg_main, padx=20, pady=10)
        search_frame.pack(fill=tk.X)

        search_label = tk.Label(
            search_frame,
            text="🔍 Tìm kiếm:",
            font=("Ubuntu", 10),
            fg=self.fg_secondary,
            bg=self.bg_main,
        )
        search_label.pack(side=tk.LEFT, padx=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_accounts())
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("Ubuntu", 10),
            bg=self.bg_card,
            fg=self.fg_primary,
            insertbackground=self.fg_primary,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#404040",
            highlightcolor=self.color_accent,
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- Danh sách bảng tài khoản (Treeview) ---
        table_frame = tk.Frame(self, bg=self.bg_main, padx=20, pady=0)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("index", "email", "name", "status", "last_used")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("index", text="STT")
        self.tree.heading("email", text="Email Google")
        self.tree.heading("name", text="Tên người dùng")
        self.tree.heading("status", text="Trạng thái")
        self.tree.heading("last_used", text="Sử dụng lần cuối")

        self.tree.column("index", width=50, anchor="center")
        self.tree.column("email", width=250, anchor="w")
        self.tree.column("name", width=180, anchor="w")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("last_used", width=140, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Sự kiện nhấp đúp vào dòng để chuyển tài khoản
        self.tree.bind("<Double-1>", self._on_double_click)

        # --- Bảng điều khiển nút bấm phía dưới ---
        control_frame = tk.Frame(self, bg=self.bg_panel, padx=20, pady=12)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Nút Kích hoạt (Không restart)
        self.btn_switch = tk.Button(
            control_frame,
            text="⚡ Kích hoạt (Không restart)",
            font=("Ubuntu", 10, "bold"),
            bg=self.color_accent,
            fg="#ffffff",
            activebackground=self.color_accent_hover,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=lambda: self._execute_switch(restart=False),
        )
        self.btn_switch.pack(side=tk.LEFT, padx=(0, 10))

        # Nút Kích hoạt & Khởi động lại IDE
        self.btn_switch_restart = tk.Button(
            control_frame,
            text="🔄 Kích hoạt & Khởi động lại IDE",
            font=("Ubuntu", 10, "bold"),
            bg=self.color_restart,
            fg="#ffffff",
            activebackground="#389b57",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=lambda: self._execute_switch(restart=True),
        )
        self.btn_switch_restart.pack(side=tk.LEFT, padx=(0, 10))

        # Nút Thêm tài khoản mới
        self.btn_add = tk.Button(
            control_frame,
            text="➕ Thêm tài khoản",
            font=("Ubuntu", 10, "bold"),
            bg="#383838",
            fg="#ffffff",
            activebackground="#4a4a4a",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self._open_add_account_dialog,
        )
        self.btn_add.pack(side=tk.LEFT, padx=(0, 8))

        # Nút Xóa tài khoản
        self.btn_remove = tk.Button(
            control_frame,
            text="🗑️ Xóa",
            font=("Ubuntu", 10),
            bg="#5a2323",
            fg="#ffffff",
            activebackground="#7a2e2e",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._delete_selected_account,
        )
        self.btn_remove.pack(side=tk.LEFT, padx=(0, 8))

        # Nút Nhập từ Cockpit Tools cũ
        self.btn_cockpit = tk.Button(
            control_frame,
            text="📥 Nhập Cockpit",
            font=("Ubuntu", 10),
            bg="#2d3748",
            fg="#ffffff",
            activebackground="#4a5568",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._import_cockpit_action,
        )
        self.btn_cockpit.pack(side=tk.LEFT, padx=(0, 8))

        # Nút Làm mới
        self.btn_refresh = tk.Button(
            control_frame,
            text="↺ Làm mới",
            font=("Ubuntu", 10),
            bg="#3c3c3c",
            fg=self.fg_primary,
            activebackground="#505050",
            activeforeground=self.fg_primary,
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.refresh_data,
        )
        self.btn_refresh.pack(side=tk.LEFT)

        # Checkbox Tự động restart khi double click
        self.chk_auto = tk.Checkbutton(
            control_frame,
            text="Tự restart IDE khi nhấp đúp",
            variable=self.auto_restart_var,
            font=("Ubuntu", 9),
            fg=self.fg_secondary,
            bg=self.bg_panel,
            activebackground=self.bg_panel,
            activeforeground=self.fg_primary,
            selectcolor=self.bg_card,
        )
        self.chk_auto.pack(side=tk.RIGHT)

        # --- Thanh thông báo trạng thái dưới cùng ---
        self.status_bar = tk.Label(
            self,
            text="Sẵn sàng",
            font=("Ubuntu", 9),
            fg=self.fg_secondary,
            bg=self.bg_main,
            anchor="w",
            padx=20,
            pady=4,
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def refresh_data(self) -> None:
        """Nạp lại danh sách tài khoản từ file Cockpit và trạng thái active."""
        self.status_bar.config(text="Đang nạp dữ liệu...")
        self.accounts = load_all_accounts()
        self.active_email = get_active_account_email()

        if self.active_email:
            self.active_label.config(text=f"Đang sử dụng: {self.active_email}")
            self.active_indicator.config(fg=self.color_active)
        else:
            self.active_label.config(text="Đang sử dụng: Chưa đăng nhập / Chưa xác định")
            self.active_indicator.config(fg="#e5c07b")

        self._filter_accounts()
        self.status_bar.config(text=f"Đã nạp {len(self.accounts)} tài khoản thành công.")

    def _filter_accounts(self) -> None:
        """Lọc và cập nhật các dòng trên Treeview theo ô tìm kiếm."""
        search_kw = self.search_var.get().lower().strip()
        self.tree.delete(*self.tree.get_children())

        for idx, acc in enumerate(self.accounts, start=1):
            email = acc.get("email", "")
            name = acc.get("name", "")
            last_used_ts = acc.get("last_used", 0)

            # Lọc theo từ khóa
            if search_kw and (search_kw not in email.lower() and search_kw not in name.lower()):
                continue

            is_active = (email == self.active_email)
            status_text = "● Đang dùng" if is_active else "Chờ"

            # Định dạng thời gian sử dụng cuối
            if last_used_ts > 0:
                dt_str = datetime.fromtimestamp(last_used_ts).strftime("%d/%m/%Y %H:%M")
            else:
                dt_str = "Chưa rõ"

            item_id = self.tree.insert(
                "",
                tk.END,
                values=(idx, email, name, status_text, dt_str),
                tags=("active",) if is_active else ("normal",),
            )

        # Định dạng màu sắc cho hàng đang active
        self.tree.tag_configure("active", foreground=self.color_active, font=("Ubuntu", 10, "bold"))
        self.tree.tag_configure("normal", foreground=self.fg_primary)

    def _get_selected_account(self) -> Optional[Dict[str, Any]]:
        """Lấy thông tin tài khoản đang được chọn trên Treeview."""
        selected = self.tree.selection()
        if not selected:
            return None
        item_values = self.tree.item(selected[0], "values")
        if not item_values:
            return None
        selected_email = item_values[1]
        for acc in self.accounts:
            if acc.get("email") == selected_email:
                return acc
        return None

    def _on_double_click(self, event: Any) -> None:
        """Xử lý sự kiện nhấp đúp: Chuyển đổi tài khoản ngay lập tức."""
        restart = self.auto_restart_var.get()
        self._execute_switch(restart=restart)

    def _execute_switch(self, restart: bool) -> None:
        """Thực hiện chuyển đổi tài khoản đã chọn trong một background thread."""
        account = self._get_selected_account()
        if not account:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một tài khoản từ danh sách!")
            return

        email = account.get("email", "")
        self.status_bar.config(text=f"Đang chuyển sang {email}...")
        self.btn_switch.config(state=tk.DISABLED)
        self.btn_switch_restart.config(state=tk.DISABLED)

        def worker() -> None:
            success, msg = switch_account(account, restart_ide=restart)
            self.after(0, lambda: self._on_switch_completed(success, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_switch_completed(self, success: bool, msg: str) -> None:
        """Xử lý sau khi luồng chuyển đổi hoàn tất."""
        self.btn_switch.config(state=tk.NORMAL)
        self.btn_switch_restart.config(state=tk.NORMAL)
        self.refresh_data()
        self.status_bar.config(text=msg)

        if success:
            messagebox.showinfo("Thành công", msg)
        else:
            messagebox.showerror("Thất bại", msg)

    def _open_add_account_dialog(self) -> None:
        """Mở hộp thoại thêm tài khoản Google mới (OAuth qua trình duyệt hoặc Refresh Token)."""
        dialog = tk.Toplevel(self)
        dialog.title("Thêm tài khoản Antigravity")
        dialog.geometry("540x440")
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_panel)
        dialog.transient(self)
        dialog.grab_set()

        # Căn giữa cửa sổ dialog
        self.update_idletasks()
        dx = self.winfo_x() + (self.winfo_width() // 2) - 270
        dy = self.winfo_y() + (self.winfo_height() // 2) - 220
        dialog.geometry(f"+{dx}+{dy}")

        lbl_title = tk.Label(
            dialog,
            text="Thêm Tài Khoản Google Mới",
            font=("Ubuntu", 13, "bold"),
            fg=self.fg_primary,
            bg=self.bg_panel,
        )
        lbl_title.pack(anchor="w", padx=20, pady=(18, 4))

        lbl_desc = tk.Label(
            dialog,
            text="Chọn phương thức thêm tài khoản độc lập (không cần Cockpit Tools):",
            font=("Ubuntu", 9),
            fg=self.fg_secondary,
            bg=self.bg_panel,
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(0, 14))

        # --- Cách 1: Đăng nhập Google qua trình duyệt ---
        oauth_frame = tk.LabelFrame(
            dialog,
            text=" Cách 1: Đăng nhập Google trực tiếp (Khuyên dùng) ",
            font=("Ubuntu", 10, "bold"),
            fg=self.color_active,
            bg=self.bg_card,
            padx=14,
            pady=10,
        )
        oauth_frame.pack(fill=tk.X, padx=20, pady=(0, 14))

        lbl_oauth_info = tk.Label(
            oauth_frame,
            text="Mở trình duyệt để đăng nhập tài khoản Google an toàn qua OAuth2.",
            font=("Ubuntu", 9),
            fg=self.fg_secondary,
            bg=self.bg_card,
            wraplength=460,
            justify=tk.LEFT,
        )
        lbl_oauth_info.pack(anchor="w", pady=(0, 6))

        lbl_oauth_status = tk.Label(
            oauth_frame,
            text="",
            font=("Ubuntu", 9, "italic"),
            fg="#e5c07b",
            bg=self.bg_card,
        )
        lbl_oauth_status.pack(anchor="w", pady=(0, 6))

        btn_oauth = tk.Button(
            oauth_frame,
            text="🌐 Đăng nhập bằng Google (Mở trình duyệt)",
            font=("Ubuntu", 10, "bold"),
            bg=self.color_accent,
            fg="#ffffff",
            activebackground=self.color_accent_hover,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        )
        btn_oauth.pack(anchor="w")

        def start_oauth_flow() -> None:
            btn_oauth.config(state=tk.DISABLED, text="⏳ Đang chờ đăng nhập...")
            lbl_oauth_status.config(text="Đã mở trình duyệt. Vui lòng hoàn tất xác thực trên web Google...")

            def worker() -> None:
                ok, msg, acc = login_with_google(open_browser=True)

                def on_complete() -> None:
                    if ok and acc:
                        messagebox.showinfo("Thành công", msg, parent=dialog)
                        dialog.destroy()
                        self.refresh_data()
                    else:
                        messagebox.showerror("Đăng nhập thất bại", msg, parent=dialog)
                        btn_oauth.config(state=tk.NORMAL, text="🌐 Đăng nhập bằng Google (Mở trình duyệt)")
                        lbl_oauth_status.config(text="")

                self.after(0, on_complete)

            threading.Thread(target=worker, daemon=True).start()

        btn_oauth.config(command=start_oauth_flow)

        # --- Cách 2: Dán Refresh Token thủ công ---
        token_frame = tk.LabelFrame(
            dialog,
            text=" Cách 2: Dán Refresh Token thủ công ",
            font=("Ubuntu", 10, "bold"),
            fg=self.fg_primary,
            bg=self.bg_card,
            padx=14,
            pady=10,
        )
        token_frame.pack(fill=tk.X, padx=20, pady=(0, 14))

        lbl_token_info = tk.Label(
            token_frame,
            text="Dán chuỗi Refresh Token Google (bắt đầu bằng 1//0...):",
            font=("Ubuntu", 9),
            fg=self.fg_secondary,
            bg=self.bg_card,
        )
        lbl_token_info.pack(anchor="w", pady=(0, 6))

        token_entry = tk.Entry(
            token_frame,
            font=("Ubuntu", 9),
            bg=self.bg_panel,
            fg=self.fg_primary,
            insertbackground=self.fg_primary,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#404040",
            highlightcolor=self.color_accent,
        )
        token_entry.pack(fill=tk.X, pady=(0, 8))

        def submit_manual_token() -> None:
            rf = token_entry.get().strip()
            if not rf:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập Refresh Token.", parent=dialog)
                return

            lbl_token_info.config(text="Đang kết nối xác thực với Google OAuth...")
            dialog.update_idletasks()

            def token_worker() -> None:
                ok, msg, acc = add_account_by_token(rf)

                def on_token_complete() -> None:
                    if ok and acc:
                        messagebox.showinfo("Thành công", msg, parent=dialog)
                        dialog.destroy()
                        self.refresh_data()
                    else:
                        messagebox.showerror("Thất bại", msg, parent=dialog)
                        lbl_token_info.config(text="Dán chuỗi Refresh Token Google (bắt đầu bằng 1//0...):")

                self.after(0, on_token_complete)

            threading.Thread(target=token_worker, daemon=True).start()

        btn_token = tk.Button(
            token_frame,
            text="✓ Xác nhận thêm Token",
            font=("Ubuntu", 9, "bold"),
            bg="#383838",
            fg="#ffffff",
            activebackground="#4a4a4a",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=submit_manual_token,
        )
        btn_token.pack(anchor="w")

    def _delete_selected_account(self) -> None:
        """Xóa tài khoản đang được chọn khỏi kho lưu trữ."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhấp chọn một tài khoản trong bảng để xóa!")
            return

        values = self.tree.item(selected[0], "values")
        if not values:
            return

        email = values[1]
        name = values[2]

        confirm = messagebox.askyesno(
            "Xác nhận xóa tài khoản",
            f"Bạn có chắc chắn muốn xóa tài khoản này khỏi Switcher?\n\n- Email: {email}\n- Tên: {name}",
            icon="warning",
        )
        if confirm:
            ok, msg = remove_account(email)
            if ok:
                messagebox.showinfo("Đã xóa", msg)
                self.refresh_data()
            else:
                messagebox.showerror("Lỗi", msg)

    def _import_cockpit_action(self) -> None:
        """Nhập tài khoản từ Cockpit Tools cũ."""
        count, msg = import_from_cockpit()
        if count > 0:
            messagebox.showinfo("Nhập tài khoản", msg)
            self.refresh_data()
        else:
            messagebox.showwarning("Thông báo", msg)


def launch_gui() -> None:
    """Khởi chạy ứng dụng đồ họa."""
    app = AntigravitySwitcherApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
