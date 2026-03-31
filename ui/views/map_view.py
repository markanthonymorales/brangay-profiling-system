import customtkinter as ctk
import tkintermapview
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.form_fields import LabeledDropdown
from services.map_service import get_map_markers, get_barangay_map_info

# Davao City center
DAVAO_LAT = 7.0707
DAVAO_LON = 125.6087
DEFAULT_ZOOM = 12

OVERLAY_MODES = ["By District", "By Crime Risk", "By Population", "All Markers"]

# District colors
DISTRICT_COLORS = {
    1: "#1E88E5",  # blue
    2: "#43A047",  # green
    3: "#FB8C00",  # orange
}

# Crime risk color thresholds
def _crime_risk_color(count: int) -> str:
    if count == 0:
        return "#43A047"   # green
    elif count <= 5:
        return "#FDD835"   # yellow
    elif count <= 15:
        return "#FB8C00"   # orange
    else:
        return "#E53935"   # red

# Population color/text
def _population_color(pop: int | None) -> str:
    if pop is None:
        return "#9E9E9E"   # grey
    elif pop < 10000:
        return "#64B5F6"   # light blue
    elif pop < 30000:
        return "#1E88E5"   # blue
    else:
        return "#0D47A1"   # dark blue


class MapView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._markers: list = []
        self._marker_data: list[dict] = []
        self._marker_id_map: dict[int, dict] = {}
        self._build_ui()

    def _build_ui(self):
        # Top toolbar
        toolbar = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=50)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        ctk.CTkLabel(
            toolbar, text="\U0001F5FA  Map",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=PADDING_LARGE)

        # Overlay selector
        self._overlay = ctk.CTkComboBox(
            toolbar, values=OVERLAY_MODES,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=160, height=30,
            state="readonly", command=self._on_overlay_change,
        )
        self._overlay.set(OVERLAY_MODES[0])
        self._overlay.pack(side="left", padx=(20, 10))

        # Search
        self._search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="Search barangay...",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=200, height=30,
        )
        self._search_entry.pack(side="left", padx=(10, 5))
        self._search_entry.bind("<Return>", lambda e: self._search_barangay())

        ctk.CTkButton(
            toolbar, text="Go", command=self._search_barangay,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=50, height=30,
        ).pack(side="left", padx=(0, 10))

        # Legend
        self._legend_label = ctk.CTkLabel(
            toolbar, text="", font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY,
        )
        self._legend_label.pack(side="right", padx=PADDING_LARGE)

        # Main content: map + info panel
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # Map widget
        self._map = tkintermapview.TkinterMapView(content, corner_radius=0)
        self._map.pack(side="left", fill="both", expand=True)
        self._map.set_position(DAVAO_LAT, DAVAO_LON)
        self._map.set_zoom(DEFAULT_ZOOM)

        # Info panel (right side)
        self._info_panel = ctk.CTkFrame(content, fg_color=CARD_BG, width=280, corner_radius=0)
        self._info_panel.pack(side="right", fill="y")
        self._info_panel.pack_propagate(False)

        ctk.CTkLabel(
            self._info_panel, text="Barangay Info",
            font=(FONT_FAMILY, 13, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._info_content = ctk.CTkScrollableFrame(self._info_panel, fg_color="transparent")
        self._info_content.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        self._info_placeholder = ctk.CTkLabel(
            self._info_content, text="Click a marker to view details.",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
            wraplength=240,
        )
        self._info_placeholder.pack(pady=20)

    def _load_markers(self):
        self._marker_data = get_map_markers()
        self._marker_id_map = {m["id"]: m for m in self._marker_data}

    def _clear_markers(self):
        for marker in self._markers:
            marker.delete()
        self._markers.clear()

    def _on_overlay_change(self, mode: str):
        self._render_markers(mode)

    def _render_markers(self, mode: str | None = None):
        if mode is None:
            mode = self._overlay.get()

        self._clear_markers()

        if not self._marker_data:
            self._load_markers()

        legend = ""

        for m in self._marker_data:
            lat, lon = m["lat"], m["lon"]
            name = m["name"]

            if mode == "By District":
                color = DISTRICT_COLORS.get(m["district_id"], "#1E88E5")
                legend = "Blue=1st  Green=2nd  Orange=3rd"
            elif mode == "By Crime Risk":
                color = _crime_risk_color(m["crime_count"])
                legend = "Green=0  Yellow=1-5  Orange=6-15  Red=16+"
            elif mode == "By Population":
                color = _population_color(m["population"])
                legend = "Grey=N/A  Light=<10K  Blue=10-30K  Dark=>30K"
            else:
                color = "#1E88E5"
                legend = "All barangays"

            marker = self._map.set_marker(
                lat, lon, text=name,
                marker_color_circle=color,
                marker_color_outside=color,
                command=lambda marker_obj, m_data=m: self._on_marker_click(m_data),
            )
            self._markers.append(marker)

        self._legend_label.configure(text=legend)

    def _on_marker_click(self, marker_data: dict):
        # Clear info panel
        for w in self._info_content.winfo_children():
            w.destroy()

        # Fetch detailed info
        info = get_barangay_map_info(marker_data["id"])
        if not info:
            ctk.CTkLabel(
                self._info_content, text="Could not load barangay info.",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=DANGER_COLOR,
            ).pack(pady=10)
            return

        # Barangay name header
        ctk.CTkLabel(
            self._info_content, text=f"Brgy. {info['name']}",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY,
            wraplength=240,
        ).pack(anchor="w", pady=(0, 2))

        # District badge
        ctk.CTkLabel(
            self._info_content, text=info["district_name"],
            font=(FONT_FAMILY, 10), text_color=TEXT_LIGHT,
            fg_color=PRIMARY_COLOR, corner_radius=4, padx=6, pady=2,
        ).pack(anchor="w", pady=(0, 5))

        if info["classification"] != "N/A":
            ctk.CTkLabel(
                self._info_content, text=info["classification"].capitalize(),
                font=(FONT_FAMILY, 10), text_color=TEXT_LIGHT,
                fg_color="#757575", corner_radius=4, padx=6, pady=2,
            ).pack(anchor="w", pady=(0, 8))

        # Separator
        ctk.CTkFrame(self._info_content, height=1, fg_color="#E0E0E0").pack(fill="x", pady=5)

        # Info fields
        fields = [
            ("Population", f"{info['population']:,}" if info["population"] else "No data"),
            ("Households", f"{info['households']:,}" if info["households"] else "No data"),
            ("", ""),  # spacer
            ("Crime (12 mo)", str(info["crime_count_12m"])),
            ("Traffic (12 mo)", str(info["traffic_count_12m"])),
            ("Top Crime Type", info["top_crime_type"] or "None"),
            ("", ""),
            ("Avg Income", f"PHP {info['avg_income']:,.2f}" if info["avg_income"] else "No data"),
            ("Water Coverage", f"{info['water_coverage']:.1f}%" if info["water_coverage"] is not None else "No data"),
            ("Power Coverage", f"{info['power_coverage']:.1f}%" if info["power_coverage"] is not None else "No data"),
        ]

        for label, value in fields:
            if label == "" and value == "":
                ctk.CTkFrame(self._info_content, height=1, fg_color="#E0E0E0").pack(fill="x", pady=5)
                continue

            row = ctk.CTkFrame(self._info_content, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(
                row, text=label, font=(FONT_FAMILY, 10, "bold"),
                text_color=TEXT_PRIMARY, anchor="w", width=120,
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=value, font=(FONT_FAMILY, 10),
                text_color=TEXT_SECONDARY, anchor="w",
            ).pack(side="left")

        # Crime risk indicator
        crime_count = info["crime_count_12m"]
        risk_color = _crime_risk_color(crime_count)
        if crime_count == 0:
            risk_text = "LOW RISK"
        elif crime_count <= 5:
            risk_text = "MODERATE RISK"
        elif crime_count <= 15:
            risk_text = "HIGH RISK"
        else:
            risk_text = "CRITICAL RISK"

        ctk.CTkFrame(self._info_content, height=1, fg_color="#E0E0E0").pack(fill="x", pady=8)
        ctk.CTkLabel(
            self._info_content, text=risk_text,
            font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_LIGHT,
            fg_color=risk_color, corner_radius=6, padx=10, pady=4,
        ).pack(anchor="w")

    def _search_barangay(self):
        query = self._search_entry.get().strip().lower()
        if not query:
            return

        if not self._marker_data:
            self._load_markers()

        for m in self._marker_data:
            if query in m["name"].lower():
                self._map.set_position(m["lat"], m["lon"])
                self._map.set_zoom(15)
                self._on_marker_click(m)
                return

        # Not found — check partial matches
        matches = [m for m in self._marker_data if query in m["name"].lower()]
        if matches:
            m = matches[0]
            self._map.set_position(m["lat"], m["lon"])
            self._map.set_zoom(15)
            self._on_marker_click(m)

    def refresh(self):
        self._load_markers()
        self._render_markers()
