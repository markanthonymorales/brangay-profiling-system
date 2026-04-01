import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_LIGHT, PRIMARY_COLOR, ACCENT_COLOR,
    WARNING_COLOR, SUCCESS_COLOR,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.chart_widget import ChartWidget
from services.forecast_service import (
    forecast_population, forecast_utility_demand,
    forecast_infrastructure_needs, get_all_barangays_for_forecast,
)


class ForecastView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._barangays = []
        self._selected_barangay_id = None
        self._build_ui()
        self._load_barangays()

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="Forecasting",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Scope selector
        selector_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=8)
        selector_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            selector_frame, text="Barangay:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(PADDING_NORMAL, 5), pady=PADDING_NORMAL)

        self._brgy_combo = ctk.CTkComboBox(
            selector_frame, values=["Loading..."],
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=250, height=30,
            state="readonly", command=self._on_barangay_change,
        )
        self._brgy_combo.pack(side="left", padx=(0, PADDING_NORMAL), pady=PADDING_NORMAL)

        # Tabview for forecast types
        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        # Population tab
        pop_tab = self._tabview.add("Population")
        self._pop_trend_label = ctk.CTkLabel(
            pop_tab, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._pop_trend_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
        self._pop_chart = ChartWidget(pop_tab, figsize=(7, 3))
        self._pop_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Utilities tab
        util_tab = self._tabview.add("Utilities")
        self._util_trend_label = ctk.CTkLabel(
            util_tab, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._util_trend_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
        self._util_chart = ChartWidget(util_tab, figsize=(7, 3))
        self._util_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Infrastructure tab
        infra_tab = self._tabview.add("Infrastructure")
        self._infra_trend_label = ctk.CTkLabel(
            infra_tab, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._infra_trend_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
        self._infra_chart = ChartWidget(infra_tab, figsize=(7, 3))
        self._infra_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _load_barangays(self):
        self._barangays = get_all_barangays_for_forecast()
        names = [b["name"] for b in self._barangays]
        if names:
            self._brgy_combo.configure(values=names)
            self._brgy_combo.set(names[0])
            self._selected_barangay_id = self._barangays[0]["id"]
        else:
            self._brgy_combo.configure(values=["No barangays"])
            self._brgy_combo.set("No barangays")

    def _on_barangay_change(self, name: str):
        for b in self._barangays:
            if b["name"] == name:
                self._selected_barangay_id = b["id"]
                break
        self._update_forecasts()

    def _update_forecasts(self):
        if not self._selected_barangay_id:
            return

        bid = self._selected_barangay_id

        # Population forecast
        pop_data = forecast_population(bid)
        self._render_forecast_chart(
            self._pop_chart, self._pop_trend_label, pop_data,
            title="Population Forecast", ylabel="Population",
        )

        # Utility forecast
        util_data = forecast_utility_demand(bid)
        self._render_forecast_chart(
            self._util_chart, self._util_trend_label, util_data,
            title="Utility Coverage Forecast", ylabel="Avg Coverage (%)",
        )

        # Infrastructure forecast
        infra_data = forecast_infrastructure_needs(bid)
        facility_count = infra_data.get("facility_count", 0)
        self._render_forecast_chart(
            self._infra_chart, self._infra_trend_label, infra_data,
            title=f"Infrastructure Demand Index (Facilities: {facility_count})",
            ylabel="Demand Index (%)",
        )

    def _render_forecast_chart(self, chart_widget: ChartWidget,
                               trend_label: ctk.CTkLabel,
                               data: dict, title: str, ylabel: str):
        trend = data.get("trend", "stable")
        trend_colors = {
            "increasing": WARNING_COLOR,
            "decreasing": PRIMARY_COLOR,
            "stable": SUCCESS_COLOR,
        }
        trend_label.configure(
            text=f"Trend: {trend.capitalize()}",
            text_color=trend_colors.get(trend, TEXT_SECONDARY),
        )

        historical = data.get("historical", [])
        forecast = data.get("forecast", [])

        if not historical:
            chart_widget.clear()
            return

        def draw(fig, ax):
            # Historical line
            h_years = [p[0] for p in historical]
            h_values = [p[1] for p in historical]
            ax.plot(h_years, h_values, "o-", color=PRIMARY_COLOR, linewidth=2,
                    markersize=6, label="Historical", zorder=3)

            # Forecast line (dashed)
            if forecast:
                # Connect from last historical point
                f_years = [h_years[-1]] + [p[0] for p in forecast]
                f_values = [h_values[-1]] + [p[1] for p in forecast]
                ax.plot(f_years, f_values, "o--", color=ACCENT_COLOR, linewidth=2,
                        markersize=6, label="Projected", zorder=3)

                # Shade forecast area
                ax.axvspan(h_years[-1], f_years[-1], alpha=0.08, color=ACCENT_COLOR)

            ax.set_title(title, fontsize=11)
            ax.set_ylabel(ylabel)
            ax.set_xlabel("Year")
            ax.legend(fontsize=9)

            # Integer x-axis ticks
            all_years = h_years + [p[0] for p in forecast]
            ax.set_xticks(all_years)
            ax.set_xticklabels([str(int(y)) for y in all_years], fontsize=8)

        chart_widget.update_chart(draw)

    def refresh(self):
        self._load_barangays()
        self._update_forecasts()
