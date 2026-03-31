import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_LARGE,
    PRIMARY_COLOR, DANGER_COLOR, TEXT_LIGHT, TEXT_PRIMARY, PADDING_LARGE,
)


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str = "Confirm", message: str = "Are you sure?",
                 on_confirm=None, confirm_text: str = "Yes", cancel_text: str = "No"):
        super().__init__(master)
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._result = False
        self._on_confirm = on_confirm

        ctk.CTkLabel(
            self, text=message, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            text_color=TEXT_PRIMARY, wraplength=350,
        ).pack(pady=(PADDING_LARGE, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=PADDING_LARGE)

        ctk.CTkButton(
            btn_frame, text=cancel_text, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color="gray", text_color=TEXT_LIGHT, width=120,
            command=self._cancel,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text=confirm_text, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=120,
            command=self._confirm,
        ).pack(side="left", padx=10)

        self.after(100, self.focus_force)

    def _confirm(self):
        self._result = True
        if self._on_confirm:
            self._on_confirm()
        self.destroy()

    def _cancel(self):
        self._result = False
        self.destroy()
