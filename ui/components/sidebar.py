import customtkinter as ctk
from ui.theme import (
    SIDEBAR_BG, SIDEBAR_TEXT, SIDEBAR_HOVER, SIDEBAR_ACTIVE,
    SIDEBAR_WIDTH, FONT_FAMILY, FONT_SIZE_NORMAL, PADDING_NORMAL, TEXT_LIGHT,
    PRIMARY_COLOR
)


class SidebarItem(ctk.CTkButton):
    def __init__(self, master, text, icon="", command=None, **kwargs):
        super().__init__(
            master,
            text=f"  {icon}  {text}",
            command=command,
            anchor="w",
            height=40,
            corner_radius=8,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color="transparent",
            text_color=SIDEBAR_TEXT,
            hover_color=SIDEBAR_HOVER,
            **kwargs,
        )
        self._is_active = False

    def set_active(self, active: bool):
        self._is_active = active
        if active:
            self.configure(fg_color=SIDEBAR_ACTIVE, text_color=TEXT_LIGHT)
        else:
            self.configure(fg_color="transparent", text_color=SIDEBAR_TEXT)


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, user_role="viewer", **kwargs):
        super().__init__(master, width=SIDEBAR_WIDTH, corner_radius=0,
                         fg_color=SIDEBAR_BG, **kwargs)
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._items: dict[str, SidebarItem] = {}
        self._user_role = user_role

        # Logo + title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(15, 5))

        try:
            from utils.logo_generator import get_logo_small_path
            from PIL import Image
            logo_img = ctk.CTkImage(Image.open(get_logo_small_path()), size=(36, 36))
            logo_row = ctk.CTkFrame(title_frame, fg_color="transparent")
            logo_row.pack(anchor="w")
            ctk.CTkLabel(logo_row, image=logo_img, text="").pack(side="left", padx=(0, 8))
            text_col = ctk.CTkFrame(logo_row, fg_color="transparent")
            text_col.pack(side="left")
            ctk.CTkLabel(text_col, text="Davao City", font=(FONT_FAMILY, 10),
                         text_color="#DAA520").pack(anchor="w")
            ctk.CTkLabel(text_col, text="Barangay Profiling", font=(FONT_FAMILY, 13, "bold"),
                         text_color=TEXT_LIGHT).pack(anchor="w")
        except Exception:
            ctk.CTkLabel(title_frame, text="Davao City", font=(FONT_FAMILY, 10),
                         text_color="#DAA520").pack(anchor="w")
            ctk.CTkLabel(title_frame, text="Barangay Profiling", font=(FONT_FAMILY, 13, "bold"),
                         text_color=TEXT_LIGHT).pack(anchor="w")

        # Gold separator
        ctk.CTkFrame(self, height=2, fg_color="#DAA520").pack(
            fill="x", padx=PADDING_NORMAL, pady=(12, 10)
        )

        # Navigation items
        nav_items = [
            ("dashboard", "Dashboard", "\U0001F4CA"),
            ("barangays", "Barangays", "\U0001F3D8"),
            ("data_entry", "Data Entry", "\U0001F4DD"),
            ("submissions", "Submissions", "\U0001F4E5"),
            ("reports", "Reports", "\U0001F4C4"),
            ("analytics", "Analytics", "\U0001F4C8"),
            ("forecasting", "Forecasting", "\U0001F52E"),
            ("crime", "Crime & Safety", "\U0001F6E1"),
            ("action_plans", "Action Plans", "\U0001F4CB"),
            ("map", "Map", "\U0001F5FA"),
            ("notifications", "Notifications", "\U0001F514"),
        ]

        admin_items = [
            ("users", "User Management", "\U0001F465"),
            ("audit_log", "Audit Log", "\U0001F4DC"),
            ("system", "System", "\u2699"),
        ]

        for key, text, icon in nav_items:
            self._add_item(key, text, icon)

        if user_role == "admin":
            # Admin separator
            ctk.CTkFrame(self, height=1, fg_color=SIDEBAR_HOVER).pack(
                fill="x", padx=PADDING_NORMAL, pady=10
            )
            ctk.CTkLabel(
                self, text="  ADMIN", font=(FONT_FAMILY, 10),
                text_color=SIDEBAR_TEXT, anchor="w",
            ).pack(fill="x", padx=PADDING_NORMAL)

            for key, text, icon in admin_items:
                self._add_item(key, text, icon)

    def _add_item(self, key: str, text: str, icon: str):
        item = SidebarItem(
            self, text=text, icon=icon,
            command=lambda k=key: self._handle_click(k),
        )
        item.pack(fill="x", padx=PADDING_NORMAL, pady=2)
        self._items[key] = item

    def _handle_click(self, key: str):
        for k, item in self._items.items():
            item.set_active(k == key)
        self._on_navigate(key)

    def set_active(self, key: str):
        for k, item in self._items.items():
            item.set_active(k == key)
