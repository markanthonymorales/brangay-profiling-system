import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, WARNING_COLOR,
    SUCCESS_COLOR, DANGER_COLOR, TEXT_LIGHT,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.chart_widget import ChartWidget
from services.comparison_service import (
    compare_barangays, compare_districts, year_over_year,
    get_available_years, ALL_METRICS,
)
from services.history_service import get_record_history, get_barangay_history, TABLE_MODEL_MAP
from services.barangay_service import get_all_districts, get_barangays_by_district
from database.db import get_session
from database.models import Barangay

METRIC_LABELS = {
    "population": "Population",
    "income": "Avg Household Income",
    "water_coverage": "Water Coverage %",
    "power_coverage": "Power Coverage %",
    "internet_coverage": "Internet Coverage %",
    "crime_count": "Crime Count",
    "waste_collection_rate": "Waste Collection %",
}

TABLE_LABELS = {
    "population_records": "Population",
    "income_data": "Income",
    "utilities": "Utilities",
    "waste_management": "Waste Management",
    "crime_incidents": "Crime Incidents",
    "traffic_incidents": "Traffic Incidents",
    "food_sources": "Food Sources",
    "government_facilities": "Government Facilities",
    "religious_demographics": "Religious Demographics",
    "businesses": "Businesses",
    "land_types": "Land Types",
    "resident_categories": "Resident Categories",
}


class ComparisonView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._districts = get_all_districts()
        self._all_barangays = self._load_all_barangays()
        self._available_years = get_available_years()
        self._build_ui()

    def _load_all_barangays(self):
        session = get_session()
        try:
            return [
                {"id": b.id, "name": b.name}
                for b in session.query(Barangay).order_by(Barangay.name).all()
            ]
        finally:
            session.close()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Comparisons",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_brgy_vs_brgy_tab(self._tabview.add("Barangay vs Barangay"))
        self._build_district_tab(self._tabview.add("District vs District"))
        self._build_yoy_tab(self._tabview.add("Year over Year"))
        self._build_history_tab(self._tabview.add("Change History"))

    # ── Tab 1: Barangay vs Barangay ──────────────────────────

    def _build_brgy_vs_brgy_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        brgy_names = [b["name"] for b in self._all_barangays]

        ctk.CTkLabel(ctrl, text="Select Barangays (2-4):", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 5))

        self._brgy_combos = []
        for i in range(4):
            combo = ctk.CTkComboBox(ctrl, values=["(none)"] + brgy_names, width=180,
                                    font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly")
            combo.set("(none)")
            combo.grid(row=1, column=i, padx=(0, 5))
            self._brgy_combos.append(combo)

        # Metric checkboxes
        ctk.CTkLabel(ctrl, text="Metrics:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 5))

        self._metric_vars = {}
        for i, metric in enumerate(ALL_METRICS):
            var = ctk.BooleanVar(value=(metric == "population"))
            cb = ctk.CTkCheckBox(ctrl, text=METRIC_LABELS[metric], variable=var,
                                 font=(FONT_FAMILY, FONT_SIZE_SMALL))
            cb.grid(row=3 + i // 4, column=i % 4, sticky="w", padx=(0, 5), pady=2)
            self._metric_vars[metric] = var

        ctk.CTkButton(ctrl, text="Compare", command=self._run_brgy_compare,
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=120, height=34,
                       ).grid(row=6, column=0, pady=(10, 0), sticky="w")

        self._brgy_chart = ChartWidget(tab, figsize=(7, 3.5))
        self._brgy_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _run_brgy_compare(self):
        selected_ids = []
        for combo in self._brgy_combos:
            name = combo.get()
            if name != "(none)":
                for b in self._all_barangays:
                    if b["name"] == name:
                        selected_ids.append(b["id"])
                        break

        if len(selected_ids) < 2:
            return

        metrics = [m for m, var in self._metric_vars.items() if var.get()]
        if not metrics:
            metrics = ["population"]

        years = self._available_years if self._available_years else [2024, 2025]
        data = compare_barangays(selected_ids, metrics, years)

        if "error" in data:
            return

        def draw(fig, ax):
            barangays = data["barangays"]
            if not barangays or not metrics:
                return

            metric = metrics[0]  # Chart shows first metric
            colors = ["#1E88E5", "#43A047", "#FB8C00", "#E53935"]

            for i, brgy in enumerate(barangays):
                metric_data = brgy["metrics"].get(metric, {})
                yrs = sorted(metric_data.keys())
                vals = [metric_data[y] for y in yrs if metric_data[y] is not None]
                valid_yrs = [y for y in yrs if metric_data[y] is not None]
                if valid_yrs:
                    ax.plot(valid_yrs, vals, "o-", color=colors[i % len(colors)],
                            linewidth=2, markersize=6, label=brgy["name"])

            ax.set_title(f"Comparison: {METRIC_LABELS.get(metric, metric)}", fontsize=11)
            ax.set_ylabel(METRIC_LABELS.get(metric, metric))
            ax.set_xlabel("Year")
            ax.legend(fontsize=8)

        self._brgy_chart.update_chart(draw)

    # ── Tab 2: District vs District ──────────────────────────

    def _build_district_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        ctk.CTkLabel(ctrl, text="Metric:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(0, 5))

        metric_labels = [METRIC_LABELS[m] for m in ALL_METRICS]
        self._dist_metric_combo = ctk.CTkComboBox(ctrl, values=metric_labels, width=200,
                                                   font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly")
        self._dist_metric_combo.set(metric_labels[0])
        self._dist_metric_combo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Compare Districts", command=self._run_district_compare,
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=140, height=34,
                       ).pack(side="left")

        self._dist_chart = ChartWidget(tab, figsize=(7, 3.5))
        self._dist_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _run_district_compare(self):
        label = self._dist_metric_combo.get()
        metric = None
        for key, lbl in METRIC_LABELS.items():
            if lbl == label:
                metric = key
                break
        if not metric:
            return

        years = self._available_years if self._available_years else [2024, 2025]
        data = compare_districts([metric], years)

        def draw(fig, ax):
            districts = data.get("districts", [])
            if not districts:
                return
            colors = ["#1E88E5", "#43A047", "#FB8C00"]
            for i, dist in enumerate(districts):
                metric_data = dist["metrics"].get(metric, {})
                yrs = sorted(metric_data.keys())
                vals = [metric_data[y] for y in yrs if metric_data[y] is not None]
                valid_yrs = [y for y in yrs if metric_data[y] is not None]
                if valid_yrs:
                    short_name = dist["name"].replace("Congressional ", "").replace("District", "Dist.")
                    ax.plot(valid_yrs, vals, "o-", color=colors[i % len(colors)],
                            linewidth=2, markersize=6, label=short_name)

            ax.set_title(f"District Comparison: {METRIC_LABELS.get(metric, metric)}", fontsize=11)
            ax.set_ylabel(METRIC_LABELS.get(metric, metric))
            ax.set_xlabel("Year")
            ax.legend(fontsize=8)

        self._dist_chart.update_chart(draw)

    # ── Tab 3: Year over Year ────────────────────────────────

    def _build_yoy_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        brgy_names = [b["name"] for b in self._all_barangays]

        ctk.CTkLabel(ctrl, text="Barangay:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(0, 5))

        self._yoy_combo = ctk.CTkComboBox(ctrl, values=brgy_names, width=250,
                                           font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly")
        if brgy_names:
            self._yoy_combo.set(brgy_names[0])
        self._yoy_combo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Analyze", command=self._run_yoy,
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=100, height=34,
                       ).pack(side="left")

        self._yoy_results = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._yoy_results.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _run_yoy(self):
        name = self._yoy_combo.get()
        brgy_id = None
        for b in self._all_barangays:
            if b["name"] == name:
                brgy_id = b["id"]
                break
        if not brgy_id:
            return

        years = self._available_years if self._available_years else [2024, 2025]
        data = year_over_year(brgy_id, years)

        for w in self._yoy_results.winfo_children():
            w.destroy()

        if "error" in data:
            ctk.CTkLabel(self._yoy_results, text=data["error"],
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=DANGER_COLOR).pack(pady=20)
            return

        ctk.CTkLabel(
            self._yoy_results,
            text=f"{data['barangay_name']} — {data['district_name']}",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 10))

        sorted_years = sorted(years)
        for metric_key, metric_data in data["metrics"].items():
            row = ctk.CTkFrame(self._yoy_results, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=3)

            # Metric name + trend
            trend = metric_data["trend"]
            trend_icon = {"increasing": "\u2191", "decreasing": "\u2193", "stable": "\u2192"}
            trend_color = {"increasing": WARNING_COLOR, "decreasing": DANGER_COLOR, "stable": SUCCESS_COLOR}

            header = ctk.CTkFrame(row, fg_color="transparent")
            header.pack(fill="x", padx=PADDING_NORMAL, pady=(8, 2))

            ctk.CTkLabel(
                header, text=METRIC_LABELS.get(metric_key, metric_key),
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(side="left")

            ctk.CTkLabel(
                header, text=f"  {trend_icon.get(trend, '')} {trend.capitalize()}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=trend_color.get(trend, TEXT_SECONDARY),
            ).pack(side="left")

            # Values row
            vals_frame = ctk.CTkFrame(row, fg_color="transparent")
            vals_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 8))

            for yr in sorted_years:
                val = metric_data["values"].get(yr)
                growth = metric_data["growth_pct"].get(yr)
                val_text = f"{val:,.1f}" if val is not None else "N/A"
                growth_text = ""
                growth_color = TEXT_SECONDARY
                if growth is not None:
                    growth_text = f" ({growth:+.1f}%)"
                    growth_color = SUCCESS_COLOR if growth >= 0 else DANGER_COLOR

                cell = ctk.CTkFrame(vals_frame, fg_color="transparent")
                cell.pack(side="left", expand=True, fill="x")

                ctk.CTkLabel(cell, text=str(yr), font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY).pack()
                ctk.CTkLabel(cell, text=val_text, font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                             text_color=TEXT_PRIMARY).pack()
                if growth_text:
                    ctk.CTkLabel(cell, text=growth_text, font=(FONT_FAMILY, 10),
                                 text_color=growth_color).pack()

    # ── Tab 4: Change History ────────────────────────────────

    def _build_history_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        brgy_names = [b["name"] for b in self._all_barangays]

        ctk.CTkLabel(ctrl, text="Barangay:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(0, 5))

        self._hist_brgy_combo = ctk.CTkComboBox(ctrl, values=brgy_names, width=200,
                                                 font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly")
        if brgy_names:
            self._hist_brgy_combo.set(brgy_names[0])
        self._hist_brgy_combo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Load History", command=self._load_history,
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=120, height=34,
                       ).pack(side="left")

        self._hist_results = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._hist_results.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _load_history(self):
        name = self._hist_brgy_combo.get()
        brgy_id = None
        for b in self._all_barangays:
            if b["name"] == name:
                brgy_id = b["id"]
                break
        if not brgy_id:
            return

        history = get_barangay_history(brgy_id, limit=50)

        for w in self._hist_results.winfo_children():
            w.destroy()

        if not history:
            ctk.CTkLabel(self._hist_results, text="No change history found for this barangay.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=20)
            return

        for entry in history:
            row = ctk.CTkFrame(self._hist_results, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=2)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(fill="x", padx=PADDING_NORMAL, pady=8)

            table_label = TABLE_LABELS.get(entry["table_name"], entry["table_name"])
            ctk.CTkLabel(
                left, text=f"{table_label} — {entry['field_name']}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w")

            ctk.CTkLabel(
                left,
                text=f"{entry['old_value'] or '(empty)'} \u2192 {entry['new_value'] or '(empty)'}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=ACCENT_COLOR,
            ).pack(anchor="w")

            ctk.CTkLabel(
                left,
                text=f"by {entry['changed_by_name']} on {entry['changed_at']}",
                font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY,
            ).pack(anchor="w")

    def refresh(self):
        self._available_years = get_available_years()
        self._all_barangays = self._load_all_barangays()
