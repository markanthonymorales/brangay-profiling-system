import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL,
    PRIMARY_COLOR, DANGER_COLOR, ACCENT_COLOR, WARNING_COLOR,
    TEXT_LIGHT, TEXT_PRIMARY, PADDING_LARGE,
)

DIALOG_TYPES = {
    "info": {"color": PRIMARY_COLOR, "icon": "\u2139\ufe0f"},
    "success": {"color": ACCENT_COLOR, "icon": "\u2705"},
    "error": {"color": DANGER_COLOR, "icon": "\u274c"},
    "warning": {"color": WARNING_COLOR, "icon": "\u26a0\ufe0f"},
}


class MessageDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str = "Message", message: str = "",
                 dialog_type: str = "info"):
        super().__init__(master)
        self.title(title)
        self.geometry("400x160")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        config = DIALOG_TYPES.get(dialog_type, DIALOG_TYPES["info"])

        ctk.CTkLabel(
            self, text=config["icon"],
            font=(FONT_FAMILY, 32),
        ).pack(pady=(PADDING_LARGE, 5))

        ctk.CTkLabel(
            self, text=message, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            text_color=TEXT_PRIMARY, wraplength=350,
        ).pack(pady=(0, 10))

        ctk.CTkButton(
            self, text="OK", font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color=config["color"], text_color=TEXT_LIGHT, width=100,
            command=self.destroy,
        ).pack(pady=(0, PADDING_LARGE))

        self.after(100, self.focus_force)
