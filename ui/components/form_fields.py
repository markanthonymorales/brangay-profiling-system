import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
    TEXT_PRIMARY, TEXT_SECONDARY, DANGER_COLOR, PADDING_SMALL,
)


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label: str, placeholder: str = "",
                 required: bool = False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        label_text = f"{label} *" if required else label
        self._label = ctk.CTkLabel(
            self, text=label_text, font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=TEXT_PRIMARY, anchor="w",
        )
        self._label.pack(fill="x")

        self._entry = ctk.CTkEntry(
            self, placeholder_text=placeholder,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), height=35,
        )
        self._entry.pack(fill="x", pady=(2, 0))

        self._error_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, 10),
            text_color=DANGER_COLOR, anchor="w", height=14,
        )
        self._error_label.pack(fill="x")

    def get(self) -> str:
        return self._entry.get().strip()

    def set(self, value: str):
        self._entry.delete(0, "end")
        if value is not None:
            self._entry.insert(0, str(value))

    def set_error(self, message: str):
        self._error_label.configure(text=message)

    def clear_error(self):
        self._error_label.configure(text="")

    def clear(self):
        self._entry.delete(0, "end")
        self.clear_error()

    def set_state(self, state: str):
        self._entry.configure(state=state)


class LabeledDropdown(ctk.CTkFrame):
    def __init__(self, master, label: str, values: list[str],
                 required: bool = False, command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        label_text = f"{label} *" if required else label
        self._label = ctk.CTkLabel(
            self, text=label_text, font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=TEXT_PRIMARY, anchor="w",
        )
        self._label.pack(fill="x")

        self._dropdown = ctk.CTkComboBox(
            self, values=values, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            height=35, state="readonly", command=command,
        )
        self._dropdown.pack(fill="x", pady=(2, 0))
        if values:
            self._dropdown.set(values[0])

        self._error_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, 10),
            text_color=DANGER_COLOR, anchor="w", height=16,
        )
        self._error_label.pack(fill="x")

    def get(self) -> str:
        return self._dropdown.get()

    def set(self, value: str):
        self._dropdown.set(value)

    def set_values(self, values: list[str]):
        self._dropdown.configure(values=values)

    def set_error(self, message: str):
        self._error_label.configure(text=message)

    def clear_error(self):
        self._error_label.configure(text="")


class LabeledNumberEntry(LabeledEntry):
    def get_int(self, default=None):
        val = self.get()
        if val == "":
            return default
        try:
            return int(val)
        except ValueError:
            return default

    def get_float(self, default=None):
        val = self.get()
        if val == "":
            return default
        try:
            return float(val)
        except ValueError:
            return default
