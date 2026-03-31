import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_SMALL, FONT_SIZE_TITLE, FONT_SIZE_LARGE,
    CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, PADDING_NORMAL,
)


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: str = "0",
                 icon: str = "", color: str = PRIMARY_COLOR, **kwargs):
        super().__init__(master, fg_color=CARD_BG, corner_radius=12, **kwargs)
        self.configure(border_width=1, border_color="#E0E0E0")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        if icon:
            ctk.CTkLabel(
                inner, text=icon, font=(FONT_FAMILY, 28),
                text_color=color,
            ).pack(anchor="w")

        self._value_label = ctk.CTkLabel(
            inner, text=str(value),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            text_color=TEXT_PRIMARY,
        )
        self._value_label.pack(anchor="w", pady=(5, 0))

        ctk.CTkLabel(
            inner, text=title,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w")

    def set_value(self, value):
        self._value_label.configure(text=str(value))
