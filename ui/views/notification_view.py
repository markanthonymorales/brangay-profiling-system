import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_LIGHT, PRIMARY_COLOR, ACCENT_COLOR,
    WARNING_COLOR, DANGER_COLOR,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from auth.auth_manager import AuthManager
from services.notification_service import (
    get_notifications, mark_read, mark_all_read, get_unread_count
)

SEVERITY_COLORS = {
    "info": PRIMARY_COLOR,
    "warning": WARNING_COLOR,
    "error": DANGER_COLOR,
}

SEVERITY_ICONS = {
    "info": "\u2139\uFE0F",
    "warning": "\u26A0\uFE0F",
    "error": "\u274C",
}


class NotificationView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._build_ui()

    def _build_ui(self):
        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        ctk.CTkLabel(
            header, text="Notifications",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left")

        self._unread_label = ctk.CTkLabel(
            header, text="",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._unread_label.pack(side="left", padx=(15, 0))

        ctk.CTkButton(
            header, text="Mark All Read", command=self._mark_all_read,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT,
            width=120, height=30,
        ).pack(side="right")

        # Filter buttons
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        self._filter_var = ctk.StringVar(value="all")
        for val, label in [("all", "All"), ("unread", "Unread Only")]:
            ctk.CTkRadioButton(
                filter_frame, text=label, variable=self._filter_var, value=val,
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
                command=self._on_filter_change,
            ).pack(side="left", padx=(0, 15))

        # Notifications list
        self._list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

    def _on_filter_change(self):
        self.refresh()

    def refresh(self):
        user = self._auth.get_current_user()
        if not user:
            return

        # Update unread count
        unread = get_unread_count(user.id)
        self._unread_label.configure(text=f"({unread} unread)" if unread > 0 else "")

        # Clear list
        for w in self._list_frame.winfo_children():
            w.destroy()

        # Fetch notifications
        unread_only = self._filter_var.get() == "unread"
        notifications = get_notifications(user.id, unread_only=unread_only)

        if not notifications:
            ctk.CTkLabel(
                self._list_frame, text="No notifications.",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
            ).pack(pady=40)
            return

        for notif in notifications:
            self._render_notification(notif)

    def _render_notification(self, notif: dict):
        severity = notif.get("severity", "info")
        color = SEVERITY_COLORS.get(severity, PRIMARY_COLOR)
        icon = SEVERITY_ICONS.get(severity, "")
        is_read = notif.get("is_read", False)

        card_bg = "#F5F5F5" if is_read else CARD_BG
        card = ctk.CTkFrame(self._list_frame, fg_color=card_bg, corner_radius=8,
                            border_width=1, border_color="#E0E0E0")
        card.pack(fill="x", pady=3)

        # Left color bar
        bar = ctk.CTkFrame(card, fg_color=color, width=4, corner_radius=0)
        bar.pack(side="left", fill="y")

        # Content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=PADDING_NORMAL, pady=8)

        # Title row
        title_row = ctk.CTkFrame(content, fg_color="transparent")
        title_row.pack(fill="x")

        title_text = f"{icon}  {notif['title']}"
        weight = "bold" if not is_read else "normal"
        ctk.CTkLabel(
            title_row, text=title_text,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, weight), text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            title_row, text=notif.get("created_at", ""),
            font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY,
        ).pack(side="right")

        # Message
        if notif.get("message"):
            ctk.CTkLabel(
                content, text=notif["message"],
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
                anchor="w", wraplength=700, justify="left",
            ).pack(anchor="w", pady=(2, 0))

        # Dismiss button (if unread)
        if not is_read:
            ctk.CTkButton(
                card, text="Dismiss", width=60, height=24,
                font=(FONT_FAMILY, 10),
                fg_color="#E0E0E0", text_color=TEXT_PRIMARY,
                hover_color="#BDBDBD",
                command=lambda nid=notif["id"]: self._dismiss(nid),
            ).pack(side="right", padx=PADDING_NORMAL, pady=8)

    def _dismiss(self, notification_id: int):
        mark_read(notification_id)
        self.refresh()

    def _mark_all_read(self):
        user = self._auth.get_current_user()
        if user:
            mark_all_read(user.id)
            self.refresh()
