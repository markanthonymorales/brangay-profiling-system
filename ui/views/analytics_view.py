import customtkinter as ctk
import numpy as np
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.chart_widget import ChartWidget
from ui.components.form_fields import LabeledDropdown
from services.analytics_service import (
    get_population_trend, get_district_comparison,
    get_income_distribution, get_utility_coverage_by_district,
)
from services.barangay_service import get_all_districts, get_barangays_by_district


# Chart colors
COLORS = {
    "blue": "#1E88E5",
    "green": "#43A047",
    "orange": "#FB8C00",
    "red": "#E53935",
    "purple": "#7B1FA2",
    "pink": "#E91E63",
    "teal": "#00897B",
    "yellow": "#FDD835",
}


class AnalyticsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._districts = get_all_districts()
        self._district_map = {d["name"]: d["id"] for d in self._districts}
        self._barangay_map: dict[str, int] = {}
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Analytics",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_population_trends_tab()
        self._build_district_comparison_tab()
        self._build_income_distribution_tab()
        self._build_utility_coverage_tab()

    # ── Tab 1: Population Trends ──────────────────────────────

    def _build_population_trends_tab(self):
        tab = self._tabview.add("Population Trends")

        # Controls
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._pop_scope = LabeledDropdown(
            controls, label="Scope",
            values=["City-Wide", "By District", "By Barangay"],
            command=self._on_pop_scope_change,
        )
        self._pop_scope.pack(side="left", padx=(0, 10), fill="x", expand=True)

        district_names = [d["name"] for d in self._districts]
        self._pop_district = LabeledDropdown(
            controls, label="District", values=district_names,
            command=self._on_pop_district_change,
        )
        self._pop_district.pack(side="left", padx=(0, 10), fill="x", expand=True)

        self._pop_barangay = LabeledDropdown(
            controls, label="Barangay", values=[],
        )
        self._pop_barangay.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            controls, text="Update Chart", command=self._update_population_chart,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=130, height=35,
        ).pack(side="left", pady=(18, 0))

        # Chart
        self._pop_chart = ChartWidget(tab, figsize=(8, 4))
        self._pop_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

        # Initial state
        self._on_pop_scope_change("City-Wide")

    def _on_pop_scope_change(self, scope: str):
        if scope == "City-Wide":
            self._pop_district.pack_forget()
            self._pop_barangay.pack_forget()
        elif scope == "By District":
            self._pop_district.pack(side="left", padx=(0, 10), fill="x", expand=True,
                                     before=self._pop_barangay.master.winfo_children()[-1]
                                     if self._pop_barangay.winfo_ismapped() else None)
            # Re-pack in correct order
            self._repack_pop_controls(show_district=True, show_barangay=False)
        elif scope == "By Barangay":
            self._repack_pop_controls(show_district=True, show_barangay=True)
            district_names = [d["name"] for d in self._districts]
            if district_names:
                self._on_pop_district_change(district_names[0])

    def _repack_pop_controls(self, show_district: bool, show_barangay: bool):
        self._pop_district.pack_forget()
        self._pop_barangay.pack_forget()
        # Get the button (last child)
        parent = self._pop_scope.master
        btn = parent.winfo_children()[-1]
        btn.pack_forget()

        if show_district:
            self._pop_district.pack(side="left", padx=(0, 10), fill="x", expand=True)
        if show_barangay:
            self._pop_barangay.pack(side="left", padx=(0, 10), fill="x", expand=True)
        btn.pack(side="left", pady=(18, 0))

    def _on_pop_district_change(self, district_name: str):
        district_id = self._district_map.get(district_name)
        if not district_id:
            return
        barangays = get_barangays_by_district(district_id)
        self._barangay_map = {b["name"]: b["id"] for b in barangays}
        names = list(self._barangay_map.keys())
        self._pop_barangay.set_values(names)
        if names:
            self._pop_barangay.set(names[0])

    def _update_population_chart(self):
        scope = self._pop_scope.get()
        barangay_id = None
        district_id = None

        if scope == "By District":
            district_name = self._pop_district.get()
            district_id = self._district_map.get(district_name)
        elif scope == "By Barangay":
            brgy_name = self._pop_barangay.get()
            barangay_id = self._barangay_map.get(brgy_name)

        data = get_population_trend(barangay_id=barangay_id, district_id=district_id)

        if not data:
            self._pop_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No population data available.",
                ha="center", va="center", fontsize=12, color="#999999",
                transform=ax.transAxes,
            ))
            return

        def draw(fig, ax):
            years = [d["year"] for d in data]
            total = [d["total_population"] for d in data]
            male = [d["male_count"] for d in data]
            female = [d["female_count"] for d in data]

            ax.plot(years, total, marker="o", color=COLORS["blue"], linewidth=2, label="Total", markersize=6)
            ax.plot(years, male, marker="s", color=COLORS["teal"], linewidth=1.5, label="Male", markersize=5)
            ax.plot(years, female, marker="^", color=COLORS["pink"], linewidth=1.5, label="Female", markersize=5)

            title = f"Population Trend — {scope}"
            if scope == "By District":
                title += f": {self._pop_district.get()}"
            elif scope == "By Barangay":
                title += f": {self._pop_barangay.get()}"

            ax.set_title(title)
            ax.set_xlabel("Year")
            ax.set_ylabel("Population")
            ax.legend(loc="upper left", fontsize=8)

            if len(years) > 1:
                ax.set_xticks(years)
            for y_val, x_val in zip(total, years):
                ax.annotate(f"{y_val:,}", (x_val, y_val), textcoords="offset points",
                            xytext=(0, 8), ha="center", fontsize=7, color=COLORS["blue"])

        self._pop_chart.update_chart(draw)

    # ── Tab 2: District Comparison ────────────────────────────

    def _build_district_comparison_tab(self):
        tab = self._tabview.add("District Comparison")

        ctk.CTkButton(
            tab, text="Refresh Charts", command=self._update_district_comparison,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=130, height=35,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._district_chart = ChartWidget(tab, figsize=(9, 5))
        self._district_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _update_district_comparison(self):
        data = get_district_comparison()
        if not data:
            self._district_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No data available for comparison.",
                ha="center", va="center", fontsize=12, color="#999999",
                transform=ax.transAxes,
            ))
            return

        def draw(fig):
            names = [d["district_name"].replace("Congressional ", "") for d in data]
            x = np.arange(len(names))
            width = 0.35

            # Top subplot: Population & Businesses
            ax1 = fig.add_subplot(211)
            pop = [d["total_population"] for d in data]
            biz = [d["active_businesses"] for d in data]

            bars1 = ax1.bar(x - width / 2, pop, width, label="Population", color=COLORS["blue"])
            ax1.set_ylabel("Population", color=COLORS["blue"])
            ax1.set_title("District Comparison — Population & Businesses")
            ax1.set_xticks(x)
            ax1.set_xticklabels(names, fontsize=8)

            ax2 = ax1.twinx()
            bars2 = ax2.bar(x + width / 2, biz, width, label="Active Businesses", color=COLORS["orange"])
            ax2.set_ylabel("Businesses", color=COLORS["orange"])

            ax1.legend(loc="upper left", fontsize=8)
            ax2.legend(loc="upper right", fontsize=8)

            for bar, val in zip(bars1, pop):
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                         f"{val:,}", ha="center", va="bottom", fontsize=7)

            # Bottom subplot: Utility Coverage
            ax3 = fig.add_subplot(212)
            water = [d["avg_water_coverage"] for d in data]
            power = [d["avg_power_coverage"] for d in data]
            internet = [d["avg_internet_coverage"] for d in data]

            w = 0.25
            ax3.bar(x - w, water, w, label="Water %", color=COLORS["blue"])
            ax3.bar(x, power, w, label="Power %", color=COLORS["yellow"])
            ax3.bar(x + w, internet, w, label="Internet %", color=COLORS["green"])

            ax3.set_title("Utility Coverage (%)")
            ax3.set_ylabel("Coverage %")
            ax3.set_ylim(0, 110)
            ax3.set_xticks(x)
            ax3.set_xticklabels(names, fontsize=8)
            ax3.legend(fontsize=8)

        self._district_chart.update_chart_multi(draw)

    # ── Tab 3: Income Distribution ────────────────────────────

    def _build_income_distribution_tab(self):
        tab = self._tabview.add("Income Distribution")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._inc_district = LabeledDropdown(
            controls, label="District", values=district_names,
            command=self._on_inc_district_change,
        )
        self._inc_district.pack(side="left", padx=(0, 10), fill="x", expand=True)

        self._inc_barangay = LabeledDropdown(
            controls, label="Barangay", values=[],
        )
        self._inc_barangay.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            controls, text="Update Chart", command=self._update_income_chart,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=130, height=35,
        ).pack(side="left", pady=(18, 0))

        self._income_chart = ChartWidget(tab, figsize=(6, 5))
        self._income_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

        if district_names:
            self._on_inc_district_change(district_names[0])

    def _on_inc_district_change(self, district_name: str):
        district_id = self._district_map.get(district_name)
        if not district_id:
            return
        barangays = get_barangays_by_district(district_id)
        brgy_map = {b["name"]: b["id"] for b in barangays}
        self._inc_brgy_map = brgy_map
        names = list(brgy_map.keys())
        self._inc_barangay.set_values(names)
        if names:
            self._inc_barangay.set(names[0])

    def _update_income_chart(self):
        brgy_name = self._inc_barangay.get()
        brgy_id = getattr(self, "_inc_brgy_map", {}).get(brgy_name)
        if not brgy_id:
            return

        data = get_income_distribution(brgy_id)
        if not data or all(data[k] == 0 for k in ["below_poverty", "low_income", "middle_income", "high_income"]):
            self._income_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, f"No income data for {brgy_name}.",
                ha="center", va="center", fontsize=12, color="#999999",
                transform=ax.transAxes,
            ))
            return

        def draw(fig, ax):
            labels = ["Below Poverty", "Low Income", "Middle Income", "High Income"]
            values = [data["below_poverty"], data["low_income"],
                      data["middle_income"], data["high_income"]]
            colors = [COLORS["red"], COLORS["orange"], COLORS["blue"], COLORS["green"]]

            # Filter out zero values
            filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
            if not filtered:
                ax.text(0.5, 0.5, "All values are zero.", ha="center", va="center",
                        fontsize=12, color="#999999", transform=ax.transAxes)
                return

            f_labels, f_values, f_colors = zip(*filtered)

            wedges, texts, autotexts = ax.pie(
                f_values, labels=f_labels, colors=f_colors,
                autopct="%1.1f%%", startangle=90, pctdistance=0.75,
                wedgeprops=dict(width=0.4),
            )

            for t in texts:
                t.set_fontsize(9)
            for t in autotexts:
                t.set_fontsize(8)

            ax.set_title(f"Income Distribution — {data['barangay_name']} ({data['year']})")

        self._income_chart.update_chart(draw)

    # ── Tab 4: Utility Coverage ───────────────────────────────

    def _build_utility_coverage_tab(self):
        tab = self._tabview.add("Utility Coverage")

        ctk.CTkButton(
            tab, text="Refresh Chart", command=self._update_utility_chart,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=130, height=35,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._utility_chart = ChartWidget(tab, figsize=(8, 5))
        self._utility_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _update_utility_chart(self):
        data = get_utility_coverage_by_district()
        if not data:
            self._utility_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No utility data available.",
                ha="center", va="center", fontsize=12, color="#999999",
                transform=ax.transAxes,
            ))
            return

        def draw(fig, ax):
            names = [d["district_name"].replace("Congressional ", "") for d in data]
            x = np.arange(len(names))
            width = 0.25

            water = [d["water_coverage"] for d in data]
            power = [d["power_coverage"] for d in data]
            internet = [d["internet_coverage"] for d in data]

            bars_w = ax.bar(x - width, water, width, label="Water", color=COLORS["blue"])
            bars_p = ax.bar(x, power, width, label="Power", color=COLORS["yellow"])
            bars_i = ax.bar(x + width, internet, width, label="Internet", color=COLORS["green"])

            ax.set_title("Utility Coverage by District")
            ax.set_ylabel("Coverage %")
            ax.set_ylim(0, 110)
            ax.set_xticks(x)
            ax.set_xticklabels(names)
            ax.legend()

            # Value labels
            for bars in [bars_w, bars_p, bars_i]:
                for bar in bars:
                    h = bar.get_height()
                    if h > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2, h,
                                f"{h:.0f}%", ha="center", va="bottom", fontsize=7)

        self._utility_chart.update_chart(draw)

    def refresh(self):
        pass
