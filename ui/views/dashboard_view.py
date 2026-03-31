import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, WARNING_COLOR,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.stat_card import StatCard
from ui.components.chart_widget import ChartWidget
from services.report_service import get_dashboard_stats, get_district_overview
from services.analytics_service import get_population_by_district
from services.audit_service import get_recent_activity


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._build_ui()

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="Dashboard",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Stat cards row
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        self._stat_cards = {}
        card_configs = [
            ("total_barangays", "Total Barangays", "\U0001F3D8", PRIMARY_COLOR),
            ("total_population", "Total Population", "\U0001F465", ACCENT_COLOR),
            ("total_households", "Total Households", "\U0001F3E0", WARNING_COLOR),
            ("active_users", "Active Users", "\U0001F464", "#7B1FA2"),
        ]

        for i, (key, title, icon, color) in enumerate(card_configs):
            card = StatCard(cards_frame, title=title, icon=icon, color=color)
            card.pack(side="left", expand=True, fill="x", padx=(0 if i == 0 else 10, 0))
            self._stat_cards[key] = card

        # Population by district chart
        self._pop_chart = ChartWidget(self, figsize=(7, 2.5))
        self._pop_chart.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        # Bottom row: District overview + Recent activity
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)
        bottom_frame.rowconfigure(0, weight=1)

        # District overview
        district_card = ctk.CTkFrame(bottom_frame, fg_color=CARD_BG, corner_radius=12)
        district_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(
            district_card, text="District Overview",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._district_frame = ctk.CTkFrame(district_card, fg_color="transparent")
        self._district_frame.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Recent activity
        activity_card = ctk.CTkFrame(bottom_frame, fg_color=CARD_BG, corner_radius=12)
        activity_card.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            activity_card, text="Recent Activity",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._activity_frame = ctk.CTkScrollableFrame(activity_card, fg_color="transparent")
        self._activity_frame.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def refresh(self):
        stats = get_dashboard_stats()
        for key, card in self._stat_cards.items():
            value = stats.get(key, 0)
            if isinstance(value, int) and value >= 1000:
                card.set_value(f"{value:,}")
            else:
                card.set_value(str(value))

        # Population chart
        pop_data = get_population_by_district()
        if pop_data and any(d["total_population"] > 0 for d in pop_data):
            def draw_pop(fig, ax):
                names = [d["district_name"].replace("Congressional ", "").replace("District", "Dist.") for d in pop_data]
                values = [d["total_population"] for d in pop_data]
                colors = ["#1E88E5", "#43A047", "#FB8C00"]
                bars = ax.bar(names, values, color=colors[:len(names)], width=0.5)
                ax.set_title("Population by District", fontsize=11)
                ax.set_ylabel("Population")
                for bar, val in zip(bars, values):
                    if val > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                                f"{val:,}", ha="center", va="bottom", fontsize=8)
            self._pop_chart.update_chart(draw_pop)

        # District overview
        for widget in self._district_frame.winfo_children():
            widget.destroy()

        districts = get_district_overview()
        for d in districts:
            row = ctk.CTkFrame(self._district_frame, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(
                row, text=d["name"],
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=PADDING_NORMAL, pady=(8, 0))

            info = f"{d['barangay_count']} barangays  |  Population: {d['total_population']:,}" if d['total_population'] else f"{d['barangay_count']} barangays  |  No population data"
            ctk.CTkLabel(
                row, text=info,
                font=(FONT_FAMILY, 11), text_color=TEXT_SECONDARY,
            ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 8))

        # Recent activity
        for widget in self._activity_frame.winfo_children():
            widget.destroy()

        activities = get_recent_activity(limit=15)
        if not activities:
            ctk.CTkLabel(
                self._activity_frame, text="No recent activity.",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
            ).pack(pady=20)
        else:
            for a in activities:
                row = ctk.CTkFrame(self._activity_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)

                action_colors = {"CREATE": ACCENT_COLOR, "UPDATE": WARNING_COLOR, "DELETE": "#E53935"}
                color = action_colors.get(a["action"], TEXT_SECONDARY)

                ctk.CTkLabel(
                    row, text=f"[{a['action']}]",
                    font=(FONT_FAMILY, 10, "bold"), text_color=color,
                ).pack(side="left", padx=(0, 5))

                ctk.CTkLabel(
                    row, text=f"{a['username']} - {a['table_name']}",
                    font=(FONT_FAMILY, 10), text_color=TEXT_PRIMARY,
                ).pack(side="left")

                ctk.CTkLabel(
                    row, text=a["timestamp"],
                    font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY,
                ).pack(side="right")
