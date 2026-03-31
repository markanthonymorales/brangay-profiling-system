import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
    TABLE_HEADER_BG, TABLE_ROW_HOVER, TABLE_BORDER,
    CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, PADDING_SMALL,
    TEXT_LIGHT,
)


class DataTable(ctk.CTkFrame):
    def __init__(self, master, columns: list[dict], on_row_click=None,
                 show_pagination=True, show_search=True, page_size=20, **kwargs):
        """
        columns: list of dicts with keys: "key", "title", "width" (optional)
        on_row_click: callback(row_data) when a row is clicked
        show_pagination: show pagination controls
        show_search: show search box
        page_size: default rows per page
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self._columns = columns
        self._on_row_click = on_row_click
        self._all_data: list[dict] = []
        self._filtered_data: list[dict] = []
        self._row_frames: list[ctk.CTkFrame] = []
        self._page = 0
        self._page_size = page_size
        self._show_pagination = show_pagination
        self._show_search = show_search

        # Top bar: search + entries per page
        if show_search or show_pagination:
            top_bar = ctk.CTkFrame(self, fg_color="transparent", height=35)
            top_bar.pack(fill="x", pady=(0, 5))

            if show_search:
                self._search_var = ctk.StringVar()
                self._search_var.trace_add("write", lambda *_: self._on_search())
                search = ctk.CTkEntry(
                    top_bar, textvariable=self._search_var,
                    placeholder_text="Search table...",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), height=30, width=220,
                )
                search.pack(side="left", padx=(0, 10))

            if show_pagination:
                ctk.CTkLabel(top_bar, text="Show", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                             text_color=TEXT_SECONDARY).pack(side="left", padx=(10, 3))
                self._page_size_var = ctk.StringVar(value=str(page_size))
                size_menu = ctk.CTkComboBox(
                    top_bar, values=["10", "20", "50", "100"],
                    variable=self._page_size_var, width=70, height=28,
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly",
                    command=lambda _: self._on_page_size_change(),
                )
                size_menu.pack(side="left", padx=(0, 3))
                ctk.CTkLabel(top_bar, text="entries", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                             text_color=TEXT_SECONDARY).pack(side="left")

            self._info_label = ctk.CTkLabel(
                top_bar, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                text_color=TEXT_SECONDARY,
            )
            self._info_label.pack(side="right")

        # Header row
        self._header_frame = ctk.CTkFrame(self, fg_color=TABLE_HEADER_BG, corner_radius=6, height=38)
        self._header_frame.pack(fill="x", pady=(0, 1))
        self._header_frame.pack_propagate(False)
        self._create_header()

        # Body
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True)

        # Pagination bar
        if show_pagination:
            pag_bar = ctk.CTkFrame(self, fg_color="transparent", height=35)
            pag_bar.pack(fill="x", pady=(5, 0))

            self._prev_btn = ctk.CTkButton(
                pag_bar, text="< Prev", command=self._prev_page,
                font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color="#E0E0E0",
                text_color=TEXT_PRIMARY, width=70, height=28, corner_radius=6,
                hover_color="#BDBDBD",
            )
            self._prev_btn.pack(side="left", padx=(0, 5))

            self._page_label = ctk.CTkLabel(
                pag_bar, text="Page 1 of 1",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_PRIMARY,
            )
            self._page_label.pack(side="left", padx=10)

            self._next_btn = ctk.CTkButton(
                pag_bar, text="Next >", command=self._next_page,
                font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color="#E0E0E0",
                text_color=TEXT_PRIMARY, width=70, height=28, corner_radius=6,
                hover_color="#BDBDBD",
            )
            self._next_btn.pack(side="left")

    def _create_header(self):
        for i, col in enumerate(self._columns):
            weight = col.get("width", 1)
            self._header_frame.columnconfigure(i, weight=weight, uniform="col")
            label = ctk.CTkLabel(
                self._header_frame,
                text=col["title"],
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w",
            )
            label.grid(row=0, column=i, padx=10, pady=0, sticky="ew")

    def set_data(self, data: list[dict]):
        self._all_data = data
        self._page = 0
        if self._show_search and hasattr(self, "_search_var"):
            self._search_var.set("")
        self._filtered_data = list(data)
        self._render_page()

    def _on_search(self):
        query = self._search_var.get().strip().lower()
        if not query:
            self._filtered_data = list(self._all_data)
        else:
            self._filtered_data = [
                row for row in self._all_data
                if any(query in str(row.get(col["key"], "")).lower() for col in self._columns)
            ]
        self._page = 0
        self._render_page()

    def _on_page_size_change(self):
        try:
            self._page_size = int(self._page_size_var.get())
        except ValueError:
            self._page_size = 20
        self._page = 0
        self._render_page()

    def _render_page(self):
        # Clear body
        for frame in self._row_frames:
            frame.destroy()
        self._row_frames.clear()

        total = len(self._filtered_data)
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        self._page = min(self._page, total_pages - 1)

        start = self._page * self._page_size
        end = min(start + self._page_size, total)
        page_data = self._filtered_data[start:end]

        for idx, row_data in enumerate(page_data):
            self._add_row(idx, row_data)

        # Update info
        if hasattr(self, "_info_label"):
            if total == 0:
                self._info_label.configure(text="No records")
            else:
                self._info_label.configure(text=f"Showing {start + 1}-{end} of {total}")

        if self._show_pagination and hasattr(self, "_page_label"):
            self._page_label.configure(text=f"Page {self._page + 1} of {total_pages}")
            self._prev_btn.configure(state="normal" if self._page > 0 else "disabled")
            self._next_btn.configure(state="normal" if self._page < total_pages - 1 else "disabled")

    def _add_row(self, idx: int, row_data: dict):
        bg = CARD_BG if idx % 2 == 0 else "#F8F9FA"
        row_frame = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=3, height=34)
        row_frame.pack(fill="x", pady=0)
        row_frame.pack_propagate(False)

        for i, col in enumerate(self._columns):
            weight = col.get("width", 1)
            row_frame.columnconfigure(i, weight=weight, uniform="col")
            value = row_data.get(col["key"], "")
            if value is None:
                value = "-"

            label = ctk.CTkLabel(
                row_frame,
                text=str(value),
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
                text_color=TEXT_PRIMARY,
                anchor="w",
            )
            label.grid(row=0, column=i, padx=10, pady=0, sticky="ew")

            if self._on_row_click:
                label.bind("<Button-1>", lambda e, d=row_data: self._on_row_click(d))

        if self._on_row_click:
            row_frame.bind("<Button-1>", lambda e, d=row_data: self._on_row_click(d))
            row_frame.bind("<Enter>", lambda e, f=row_frame: f.configure(fg_color=TABLE_ROW_HOVER))
            row_frame.bind("<Leave>", lambda e, f=row_frame, b=bg: f.configure(fg_color=b))

        self._row_frames.append(row_frame)

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        total = len(self._filtered_data)
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        if self._page < total_pages - 1:
            self._page += 1
            self._render_page()

    def get_row_count(self) -> int:
        return len(self._all_data)
