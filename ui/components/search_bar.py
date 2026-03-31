import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, PRIMARY_COLOR, PADDING_NORMAL, TEXT_LIGHT,
)


class SearchBar(ctk.CTkFrame):
    def __init__(self, master, on_search, filters: list[dict] | None = None, **kwargs):
        """
        filters: list of dicts with keys: "label", "values", "key"
        on_search: callback(search_text, filter_values_dict)
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_search = on_search
        self._filter_widgets: dict[str, ctk.CTkComboBox] = {}

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        self._search_entry = ctk.CTkEntry(
            row, placeholder_text="Search...",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), height=35, width=300,
        )
        self._search_entry.pack(side="left", padx=(0, 10))
        self._search_entry.bind("<Return>", lambda e: self._do_search())

        if filters:
            for f in filters:
                combo = ctk.CTkComboBox(
                    row, values=["All"] + f["values"],
                    font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                    height=35, width=200, state="readonly",
                    command=lambda val: self._do_search(),
                )
                combo.set("All")
                combo.pack(side="left", padx=(0, 10))
                self._filter_widgets[f["key"]] = combo

        search_btn = ctk.CTkButton(
            row, text="Search", font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT,
            height=35, width=100,
            command=self._do_search,
        )
        search_btn.pack(side="left")

    def _do_search(self):
        search_text = self._search_entry.get().strip()
        filter_values = {}
        for key, widget in self._filter_widgets.items():
            val = widget.get()
            filter_values[key] = None if val == "All" else val
        self._on_search(search_text, filter_values)

    def clear(self):
        self._search_entry.delete(0, "end")
        for widget in self._filter_widgets.values():
            widget.set("All")
