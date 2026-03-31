import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.search_bar import SearchBar
from ui.components.data_table import DataTable
from services.barangay_service import search_barangays, get_all_districts


class BarangayListView(ctk.CTkFrame):
    def __init__(self, master, on_open_profile, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._on_open_profile = on_open_profile
        self._build_ui()

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="Barangays",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Search bar
        districts = get_all_districts()
        district_names = [d["name"] for d in districts]
        self._district_map = {d["name"]: d["id"] for d in districts}

        self._search_bar = SearchBar(
            self, on_search=self._do_search,
            filters=[
                {"label": "District", "values": district_names, "key": "district"},
                {"label": "Classification", "values": ["urban", "rural"], "key": "classification"},
            ],
        )
        self._search_bar.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        # Count label
        self._count_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._count_label.pack(anchor="w", padx=PADDING_LARGE, pady=(0, 5))

        # Table
        columns = [
            {"key": "name", "title": "Barangay Name", "width": 3},
            {"key": "district_name", "title": "District", "width": 3},
            {"key": "population", "title": "Population", "width": 1},
            {"key": "classification", "title": "Classification", "width": 1},
            {"key": "updated_at", "title": "Last Updated", "width": 1},
        ]
        self._table = DataTable(self, columns=columns, on_row_click=self._on_row_click)
        self._table.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

    def _do_search(self, search_text: str, filters: dict):
        district_name = filters.get("district")
        district_id = self._district_map.get(district_name) if district_name else None
        classification = filters.get("classification")

        data = search_barangays(search_text, district_id=district_id, classification=classification)
        self._table.set_data(data)
        self._count_label.configure(text=f"Showing {len(data)} barangay(s)")

    def _on_row_click(self, row_data: dict):
        self._on_open_profile(row_data)

    def refresh(self):
        self._do_search("", {})
