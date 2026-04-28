import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_LIGHT, PRIMARY_COLOR, ACCENT_COLOR,
    WARNING_COLOR, SUCCESS_COLOR, DANGER_COLOR,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.chart_widget import ChartWidget
from ui.components.data_table import DataTable
from ui.components.form_fields import LabeledEntry, LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from auth.auth_manager import AuthManager
from services.barangay_service import get_all_districts, get_barangays_by_district, get_all_barangays
from services.urban_planning_service import (
    project_housing, project_infrastructure, project_disaster_resilience,
    save_projection, get_projections,
    save_scenario, get_scenarios, delete_scenario,
)

COLORS = {
    "blue": "#1E88E5", "green": "#43A047", "orange": "#FB8C00",
    "red": "#E53935", "purple": "#7B1FA2", "teal": "#00897B",
}


class UrbanPlanningView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._districts = get_all_districts()
        self._district_map = {d["name"]: d["id"] for d in self._districts}
        self._barangay_maps: dict[str, dict] = {}
        self._all_barangays = []
        self._built_tabs = set()
        self._scenarios = []
        self._build_ui()

    def _get_user_id(self) -> int:
        user = self._auth.get_current_user()
        return user.id if user else 0

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="Urban Development Planning",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Tab view
        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12,
                                         command=self._on_tab_change)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._tabview.add("Housing Projections")
        self._tabview.add("Infrastructure Forecasts")
        self._tabview.add("Disaster Resilience")
        self._tabview.add("Scenario Comparison")
        self._tabview.add("Long-term Trends")

        # Build first tab immediately (lazy build others)
        self._build_housing_tab()
        self._built_tabs.add("Housing Projections")

    def _on_tab_change(self):
        current = self._tabview.get()
        if current in self._built_tabs:
            return
        self._built_tabs.add(current)
        if current == "Infrastructure Forecasts":
            self._build_infrastructure_tab()
        elif current == "Disaster Resilience":
            self._build_disaster_tab()
        elif current == "Scenario Comparison":
            self._build_scenario_tab()
        elif current == "Long-term Trends":
            self._build_trends_tab()

    # ── Tab 1: Housing Projections ────────────────────────────────

    def _build_housing_tab(self):
        tab = self._tabview.tab("Housing Projections")

        # Controls
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkLabel(
            controls, text="District:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 5))

        district_names = [d["name"] for d in self._districts]
        self._housing_district_combo = ctk.CTkComboBox(
            controls, values=district_names,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=180, height=30,
            state="readonly", command=self._on_housing_district_change,
        )
        self._housing_district_combo.pack(side="left", padx=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            controls, text="Barangay:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 5))

        self._housing_brgy_combo = ctk.CTkComboBox(
            controls, values=["Select district first"],
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=220, height=30,
            state="readonly", command=self._on_housing_barangay_change,
        )
        self._housing_brgy_combo.pack(side="left", padx=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            controls, text="Years Ahead:",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 5))

        self._housing_years_entry = ctk.CTkEntry(
            controls, font=(FONT_FAMILY, FONT_SIZE_SMALL), width=60, height=30,
        )
        self._housing_years_entry.insert(0, "10")
        self._housing_years_entry.pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            controls, text="Project", command=self._update_housing,
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            fg_color=PRIMARY_COLOR, hover_color="#1565C0",
            text_color="white", width=100, height=30, corner_radius=6,
        ).pack(side="left", padx=(5, 0))

        # Status label
        self._housing_status = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._housing_status.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 0))

        # Chart
        self._housing_chart = ChartWidget(tab, figsize=(7, 3))
        self._housing_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

        # Table frame
        table_frame = ctk.CTkFrame(tab, fg_color="transparent")
        table_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            table_frame, text="Projected Values",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 5))

        self._housing_table = DataTable(
            table_frame,
            columns=[
                {"key": "year", "title": "Year", "width": 1},
                {"key": "houses", "title": "Projected Houses", "width": 2},
            ],
        )
        self._housing_table.pack(fill="x")

        # Set initial district
        if district_names:
            self._housing_district_combo.set(district_names[0])
            self._on_housing_district_change(district_names[0])

    def _on_housing_district_change(self, district_name: str):
        barangays = self._load_barangays(district_name)
        names = list(barangays.keys())
        self._housing_brgy_combo.configure(values=names)
        if names:
            self._housing_brgy_combo.set(names[0])
            self._on_housing_barangay_change(names[0])

    def _on_housing_barangay_change(self, barangay_name: str):
        pass  # Will be called on "Project" button

    def _update_housing(self):
        district_name = self._housing_district_combo.get()
        barangay_name = self._housing_brgy_combo.get()
        barangays = self._load_barangays(district_name)
        barangay_id = barangays.get(barangay_name)

        if not barangay_id:
            self._housing_status.configure(text="Please select a barangay.", text_color=DANGER_COLOR)
            return

        try:
            years_ahead = int(self._housing_years_entry.get())
        except ValueError:
            years_ahead = 10

        result = project_housing(barangay_id, years_ahead)
        if "error" in result:
            self._housing_status.configure(text=f"Error: {result['error']}", text_color=DANGER_COLOR)
            self._housing_chart.clear()
            return

        projected = result.get("projected_values", {})
        self._housing_status.configure(
            text=f"Methodology: {result.get('methodology', 'N/A')} | Barangay: {barangay_name}",
            text_color=SUCCESS_COLOR,
        )

        # Update table - convert to list of dicts like other views
        table_data = [
            {"year": str(year), "houses": str(int(value))}
            for year, value in sorted(projected.items())
        ]
        self._housing_table.set_data(table_data)

        # Update chart
        def draw(fig, ax):
            years = sorted(projected.keys())
            values = [projected[y] for y in years]
            ax.plot(years, values, "o-", color=COLORS["blue"], linewidth=2,
                    markersize=6, label="Projected Houses", zorder=3)
            ax.set_title("Housing Demand Projection", fontsize=11)
            ax.set_ylabel("Number of Houses")
            ax.set_xlabel("Year")
            ax.legend(fontsize=9)
            ax.set_xticks(years)
            ax.set_xticklabels([str(int(y)) for y in years], fontsize=8)

        self._housing_chart.update_chart(draw)

    def _load_barangays(self, district_name: str) -> dict[str, int]:
        if district_name not in self._barangay_maps:
            did = self._district_map.get(district_name)
            if did:
                brgys = get_barangays_by_district(did)
                self._barangay_maps[district_name] = {b["name"]: b["id"] for b in brgys}
            else:
                self._barangay_maps[district_name] = {}
        return self._barangay_maps[district_name]

    # ── Tab 2: Infrastructure Forecasts ────────────────────────────────

    def _build_infrastructure_tab(self):
        tab = self._tabview.tab("Infrastructure Forecasts")

        # Controls
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkLabel(
            controls, text="Barangay:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 5))

        # Load all barangays for this tab
        if not self._all_barangays:
            self._all_barangays = get_all_barangays()
        barangay_names = [b["name"] for b in self._all_barangays]
        self._infra_brgy_combo = ctk.CTkComboBox(
            controls, values=barangay_names,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=250, height=30,
            state="readonly", command=self._on_infra_barangay_change,
        )
        self._infra_brgy_combo.pack(side="left", padx=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            controls, text="Years:",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 5))

        self._infra_years_entry = ctk.CTkEntry(
            controls, font=(FONT_FAMILY, FONT_SIZE_SMALL), width=60, height=30,
        )
        self._infra_years_entry.insert(0, "10")
        self._infra_years_entry.pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            controls, text="Forecast", command=self._update_infrastructure,
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            fg_color=PRIMARY_COLOR, hover_color="#1565C0",
            text_color="white", width=100, height=30, corner_radius=6,
        ).pack(side="left", padx=(5, 0))

        # Status
        self._infra_status = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._infra_status.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 0))

        # Chart
        self._infra_chart = ChartWidget(tab, figsize=(7, 3))
        self._infra_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

        # Set initial
        if barangay_names:
            self._infra_brgy_combo.set(barangay_names[0])
            self._on_infra_barangay_change(barangay_names[0])

    def _on_infra_barangay_change(self, barangay_name: str):
        pass

    def _update_infrastructure(self):
        barangay_name = self._infra_brgy_combo.get()
        barangay_id = None
        for b in self._all_barangays:
            if b["name"] == barangay_name:
                barangay_id = b["id"]
                break

        if not barangay_id:
            self._infra_status.configure(text="Please select a barangay.", text_color=DANGER_COLOR)
            return

        try:
            years_ahead = int(self._infra_years_entry.get())
        except ValueError:
            years_ahead = 10

        result = project_infrastructure(barangay_id, years_ahead)
        if "error" in result:
            self._infra_status.configure(text=f"Error: {result['error']}", text_color=DANGER_COLOR)
            self._infra_chart.clear()
            return

        projected = result.get("projected_values", {})
        self._infra_status.configure(
            text=f"Methodology: {result.get('methodology', 'N/A')} | {barangay_name}",
            text_color=SUCCESS_COLOR,
        )

        def draw(fig, ax):
            years = sorted(projected.keys())
            water = [projected[y]["water_coverage"] for y in years]
            power = [projected[y]["power_coverage"] for y in years]
            internet = [projected[y]["internet_coverage"] for y in years]

            ax.plot(years, water, "o-", color=COLORS["blue"], linewidth=2,
                    markersize=5, label="Water Coverage (%)", zorder=3)
            ax.plot(years, power, "s--", color=COLORS["orange"], linewidth=2,
                    markersize=5, label="Power Coverage (%)", zorder=3)
            ax.plot(years, internet, "^:", color=COLORS["purple"], linewidth=2,
                    markersize=5, label="Internet Coverage (%)", zorder=3)

            ax.set_title("Infrastructure Coverage Forecast", fontsize=11)
            ax.set_ylabel("Coverage (%)")
            ax.set_xlabel("Year")
            ax.set_ylim(0, 105)
            ax.legend(fontsize=8)
            ax.set_xticks(years)
            ax.set_xticklabels([str(int(y)) for y in years], fontsize=8)

        self._infra_chart.update_chart(draw)

    # ── Tab 3: Disaster Resilience ────────────────────────────────

    def _build_disaster_tab(self):
        tab = self._tabview.tab("Disaster Resilience")

        # Controls
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkLabel(
            controls, text="Barangay:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 5))

        barangay_names = [b["name"] for b in self._all_barangays] if self._all_barangays else []
        self._disaster_brgy_combo = ctk.CTkComboBox(
            controls, values=barangay_names,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=250, height=30,
            state="readonly", command=self._on_disaster_barangay_change,
        )
        self._disaster_brgy_combo.pack(side="left", padx=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            controls, text="Years:",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 5))

        self._disaster_years_entry = ctk.CTkEntry(
            controls, font=(FONT_FAMILY, FONT_SIZE_SMALL), width=60, height=30,
        )
        self._disaster_years_entry.insert(0, "10")
        self._disaster_years_entry.pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            controls, text="Forecast", command=self._update_disaster,
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            fg_color=PRIMARY_COLOR, hover_color="#1565C0",
            text_color="white", width=100, height=30, corner_radius=6,
        ).pack(side="left", padx=(5, 0))

        # Status
        self._disaster_status = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._disaster_status.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 0))

        # Chart
        self._disaster_chart = ChartWidget(tab, figsize=(7, 3))
        self._disaster_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

        # Set initial
        if barangay_names:
            self._disaster_brgy_combo.set(barangay_names[0])
            self._on_disaster_barangay_change(barangay_names[0])

    def _on_disaster_barangay_change(self, barangay_name: str):
        pass

    def _update_disaster(self):
        barangay_name = self._disaster_brgy_combo.get()
        barangay_id = None
        for b in self._all_barangays:
            if b["name"] == barangay_name:
                barangay_id = b["id"]
                break

        if not barangay_id:
            self._disaster_status.configure(text="Please select a barangay.", text_color=DANGER_COLOR)
            return

        try:
            years_ahead = int(self._disaster_years_entry.get())
        except ValueError:
            years_ahead = 10

        result = project_disaster_resilience(barangay_id, years_ahead)
        if "error" in result:
            self._disaster_status.configure(text=f"Error: {result['error']}", text_color=DANGER_COLOR)
            self._disaster_chart.clear()
            return

        projected = result.get("projected_values", {})
        self._disaster_status.configure(
            text=f"Methodology: {result.get('methodology', 'N/A')} | Higher = More Resilient | {barangay_name}",
            text_color=SUCCESS_COLOR,
        )

        def draw(fig, ax):
            years = sorted(projected.keys())
            values = [projected[y] for y in years]

            # Color based on resilience level
            colors = [SUCCESS_COLOR if v >= 70 else WARNING_COLOR if v >= 40 else DANGER_COLOR
                      for v in values]

            ax.plot(years, values, "o-", color=COLORS["teal"], linewidth=2,
                    markersize=6, label="Resilience Index", zorder=3)
            ax.fill_between(years, values, alpha=0.2, color=COLORS["teal"])

            # Threshold lines
            ax.axhline(y=70, color=SUCCESS_COLOR, linestyle="--", alpha=0.5, label="High Resilience")
            ax.axhline(y=40, color=WARNING_COLOR, linestyle="--", alpha=0.5, label="Medium Resilience")

            ax.set_title("Disaster Resilience Evolution", fontsize=11)
            ax.set_ylabel("Resilience Index (0-100)")
            ax.set_xlabel("Year")
            ax.set_ylim(0, 105)
            ax.legend(fontsize=8)
            ax.set_xticks(years)
            ax.set_xticklabels([str(int(y)) for y in years], fontsize=8)

        self._disaster_chart.update_chart(draw)

    # ── Tab 4: Scenario Comparison ────────────────────────────────

    def _build_scenario_tab(self):
        tab = self._tabview.tab("Scenario Comparison")

        # Top frame: scenario list and controls
        top_frame = ctk.CTkFrame(tab, fg_color="transparent")
        top_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkLabel(
            top_frame, text="Saved Scenarios:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 5))

        self._scenario_combo = ctk.CTkComboBox(
            top_frame, values=["Loading..."],
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=250, height=30,
            state="readonly", command=self._on_scenario_select,
        )
        self._scenario_combo.pack(side="left", padx=(0, PADDING_NORMAL))

        ctk.CTkButton(
            top_frame, text="New Scenario", command=self._show_new_scenario_dialog,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg_color=SUCCESS_COLOR, hover_color="#2E7D32",
            text_color="white", width=120, height=30, corner_radius=6,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            top_frame, text="Delete", command=self._delete_selected_scenario,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg_color=DANGER_COLOR, hover_color="#B71C1C",
            text_color="white", width=80, height=30, corner_radius=6,
        ).pack(side="left", padx=5)

        # Scenario Details Frame
        details_frame = ctk.CTkFrame(tab, fg_color=CARD_BG, corner_radius=8)
        details_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

        self._scenario_name_label = ctk.CTkLabel(
            details_frame, text="No scenario selected",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        )
        self._scenario_name_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 2))

        self._scenario_desc_label = ctk.CTkLabel(
            details_frame, text="",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._scenario_desc_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Parameters display
        self._scenario_params_label = ctk.CTkLabel(
            details_frame, text="",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_PRIMARY,
        )
        self._scenario_params_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Run simulation button
        ctk.CTkButton(
            details_frame, text="Run Simulation", command=self._run_simulation,
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            fg_color=PRIMARY_COLOR, hover_color="#1565C0",
            text_color="white", width=150, height=34, corner_radius=6,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Chart for comparison
        self._scenario_chart = ChartWidget(tab, figsize=(7, 3))
        self._scenario_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

        self._load_scenarios()

    def _load_scenarios(self):
        self._scenarios = get_scenarios()
        names = [f"{s['name']} ({s['scenario_type']})" for s in self._scenarios]
        self._scenario_combo.configure(values=names if names else ["No scenarios"])
        if names:
            self._scenario_combo.set(names[0])
            self._on_scenario_select(names[0])
        else:
            self._scenario_combo.set("No scenarios")

    def _on_scenario_select(self, display_name: str):
        for s in self._scenarios:
            name_with_type = f"{s['name']} ({s['scenario_type']})"
            if name_with_type == display_name:
                self._scenario_name_label.configure(text=s["name"])
                self._scenario_desc_label.configure(text=s.get("description", ""))
                params = s.get("parameters", {})
                param_text = " | ".join(f"{k}: {v}" for k, v in params.items()) if params else "No parameters"
                self._scenario_params_label.configure(text=f"Parameters: {param_text}")
                break

    def _show_new_scenario_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("New Scenario")
        dialog.geometry("500x400")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Create New Scenario",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(pady=(20, 10))

        # Form
        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=10)

        name_entry = LabeledEntry(form, "Scenario Name:", placeholder="e.g., High Growth 2030")
        name_entry.pack(fill="x", pady=5)

        desc_entry = LabeledEntry(form, "Description:", placeholder="Optional description")
        desc_entry.pack(fill="x", pady=5)

        type_combo = LabeledDropdown(form, "Scenario Type:", ["housing", "infrastructure", "disaster", "comprehensive"])
        type_combo.pack(fill="x", pady=5)

        # Parameters (simple key-value)
        param_frame = ctk.CTkFrame(form, fg_color="transparent")
        param_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            param_frame, text="Parameters (JSON):",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(anchor="w")

        import json
        default_params = json.dumps({"growth_rate": 0.05, "years": 10}, indent=2)
        param_text = ctk.CTkTextbox(param_frame, height=80, font=(FONT_FAMILY, FONT_SIZE_SMALL))
        param_text.insert("0.0", default_params)
        param_text.pack(fill="x", pady=(5, 0))

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))

        def save():
            try:
                data = {
                    "name": name_entry.get(),
                    "description": desc_entry.get(),
                    "scenario_type": type_combo.get(),
                    "parameters": json.loads(param_text.get("0.0", "end")),
                }
                success, msg = save_scenario(data, self._get_user_id())
                if success:
                    dialog.destroy()
                    self._load_scenarios()
                else:
                    MessageDialog(self, "Error", msg, "error")
            except json.JSONDecodeError:
                MessageDialog(self, "Error", "Invalid JSON in parameters", "error")

        ctk.CTkButton(
            btn_frame, text="Save", command=save,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=SUCCESS_COLOR, hover_color="#2E7D32",
            text_color="white", width=100, height=36, corner_radius=6,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="Cancel", command=dialog.destroy,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color="gray", hover_color="#757575",
            text_color="white", width=100, height=36, corner_radius=6,
        ).pack(side="right", padx=5)

    def _delete_selected_scenario(self):
        display_name = self._scenario_combo.get()
        scenario_id = None
        for s in self._scenarios:
            name_with_type = f"{s['name']} ({s['scenario_type']})"
            if name_with_type == display_name:
                scenario_id = s["id"]
                break

        if not scenario_id:
            return

        success, msg = delete_scenario(scenario_id, self._get_user_id())
        if success:
            self._load_scenarios()
        else:
            MessageDialog(self, "Error", msg, "error")

    def _run_simulation(self):
        display_name = self._scenario_combo.get()
        selected_scenario = None
        for s in self._scenarios:
            name_with_type = f"{s['name']} ({s['scenario_type']})"
            if name_with_type == display_name:
                selected_scenario = s
                break

        if not selected_scenario:
            return

        # Simple simulation: project for each barangay with scenario parameters
        params = selected_scenario.get("parameters", {})
        years = params.get("years", 10)

        # For demo: show a placeholder chart showing the scenario impact
        def draw(fig, ax):
            from datetime import date
            years_list = list(range(date.today().year, date.today().year + years + 1))
            # Simulated trend based on parameters
            growth_rate = params.get("growth_rate", 0.05)
            base = 100
            values = [base * (1 + growth_rate) ** i for i in range(len(years_list))]

            ax.plot(years_list, values, "o-", color=ACCENT_COLOR, linewidth=2,
                    markersize=6, label=f"Scenario: {selected_scenario['name']}", zorder=3)
            ax.fill_between(years_list, values, alpha=0.2, color=ACCENT_COLOR)

            ax.set_title(f"Simulation: {selected_scenario['name']}", fontsize=11)
            ax.set_ylabel("Impact Index")
            ax.set_xlabel("Year")
            ax.legend(fontsize=9)

        self._scenario_chart.update_chart(draw)

    # ── Tab 5: Long-term Trends ────────────────────────────────

    def _build_trends_tab(self):
        tab = self._tabview.tab("Long-term Trends")

        # Controls
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkLabel(
            controls, text="Trend Type:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 5))

        self._trends_type_combo = ctk.CTkComboBox(
            controls, values=["Population Growth", "Housing Demand", "Infrastructure Coverage", "Disaster Resilience"],
            font=(FONT_FAMILY, FONT_SIZE_SMALL), width=220, height=30,
            state="readonly", command=self._update_trends,
        )
        self._trends_type_combo.pack(side="left", padx=(0, PADDING_NORMAL))

        ctk.CTkButton(
            controls, text="Update", command=self._update_trends,
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            fg_color=PRIMARY_COLOR, hover_color="#1565C0",
            text_color="white", width=100, height=30, corner_radius=6,
        ).pack(side="left", padx=(5, 0))

        # Summary stats
        self._trends_summary = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._trends_summary.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 0))

        # Chart
        self._trends_chart = ChartWidget(tab, figsize=(7, 4))
        self._trends_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

        # Initial update
        self._update_trends()

    def _update_trends(self, trend_type: str = ""):
        if not trend_type:
            trend_type = self._trends_type_combo.get()

        # Get all projections for summary
        projections = get_projections()
        housing_proj = [p for p in projections if p["projection_type"] == "housing"]
        infra_proj = [p for p in projections if p["projection_type"] == "infrastructure"]
        disaster_proj = [p for p in projections if p["projection_type"] == "disaster_resilience"]

        summary_text = f"Saved Projections: {len(housing_proj)} Housing | {len(infra_proj)} Infrastructure | {len(disaster_proj)} Disaster Resilience"
        self._trends_summary.configure(text=summary_text)

        # Generate city-wide trend chart based on selected type
        if trend_type == "Population Growth":
            self._draw_population_trend()
        elif trend_type == "Housing Demand":
            self._draw_housing_trend()
        elif trend_type == "Infrastructure Coverage":
            self._draw_infra_trend()
        elif trend_type == "Disaster Resilience":
            self._draw_disaster_trend()

    def _draw_population_trend(self):
        # Aggregate population data from all barangays
        session = None
        try:
            from database.db import get_session
            from database.models import PopulationRecord
            session = get_session()
            records = session.query(PopulationRecord).order_by(PopulationRecord.year).all()

            # Aggregate by year
            year_data = {}
            for r in records:
                if r.year not in year_data:
                    year_data[r.year] = 0
                year_data[r.year] += r.total_population

            years = sorted(year_data.keys())
            values = [year_data[y] for y in years]

            def draw(fig, ax):
                ax.plot(years, values, "o-", color=COLORS["blue"], linewidth=2,
                        markersize=6, label="City Total Population", zorder=3)
                ax.fill_between(years, values, alpha=0.15, color=COLORS["blue"])
                ax.set_title("City-Wide Population Growth Trend", fontsize=11)
                ax.set_ylabel("Total Population")
                ax.set_xlabel("Year")
                ax.legend(fontsize=9)

            self._trends_chart.update_chart(draw)
        finally:
            if session:
                session.close()

    def _draw_housing_trend(self):
        # Show housing projections from saved data
        projections = get_projections(projection_type="housing")

        def draw(fig, ax):
            colors = [COLORS["blue"], COLORS["green"], COLORS["orange"], COLORS["red"], COLORS["purple"]]
            for i, proj in enumerate(projections[:5]):  # Show top 5
                projected = proj.get("projected_values", {})
                years = sorted(projected.keys())
                values = [projected[y] for y in years]
                color = colors[i % len(colors)]
                ax.plot(years, values, "o-", color=color, linewidth=1.5,
                        markersize=4, label=proj.get("barangay_name", f"Barangay {proj['barangay_id']}"),
                        zorder=3)

            ax.set_title("Housing Demand Trends (Saved Projections)", fontsize=11)
            ax.set_ylabel("Projected Houses")
            ax.set_xlabel("Year")
            if projections:
                ax.legend(fontsize=7, ncol=2)

        self._trends_chart.update_chart(draw)

    def _draw_infra_trend(self):
        # Show infrastructure coverage trends
        projections = get_projections(projection_type="infrastructure")

        def draw(fig, ax):
            colors = [COLORS["blue"], COLORS["green"], COLORS["orange"]]
            labels = ["Water", "Power", "Internet"]
            markers = ["o", "s", "^"]

            for i, proj in enumerate(projections[:3]):  # Show top 3
                projected = proj.get("projected_values", {})
                years = sorted(projected.keys())
                # Show average of water coverage for simplicity
                values = [projected[y].get("water_coverage", 0) for y in years]
                color = colors[i % len(colors)]
                ax.plot(years, values, f"{markers[i]}-", color=color, linewidth=1.5,
                        markersize=4, label=f"{labels[i]} Coverage", zorder=3)

            ax.set_title("Infrastructure Coverage Trends (Saved Projections)", fontsize=11)
            ax.set_ylabel("Coverage (%)")
            ax.set_xlabel("Year")
            ax.set_ylim(0, 105)
            if projections:
                ax.legend(fontsize=8)

        self._trends_chart.update_chart(draw)

    def _draw_disaster_trend(self):
        # Show disaster resilience trends
        projections = get_projections(projection_type="disaster_resilience")

        def draw(fig, ax):
            for i, proj in enumerate(projections[:5]):  # Show top 5
                projected = proj.get("projected_values", {})
                years = sorted(projected.keys())
                values = [projected[y] for y in years]

                ax.plot(years, values, "o-", linewidth=1.5,
                        markersize=4, label=proj.get("barangay_name", f"Barangay {proj['barangay_id']}"),
                        zorder=3)

            ax.set_title("Disaster Resilience Trends (Saved Projections)", fontsize=11)
            ax.set_ylabel("Resilience Index (0-100)")
            ax.set_xlabel("Year")
            ax.set_ylim(0, 105)
            if projections:
                ax.legend(fontsize=7, ncol=2)

        self._trends_chart.update_chart(draw)

    def refresh(self):
        # Reload data for visible/built tabs
        if "Scenario Comparison" in self._built_tabs:
            self._load_scenarios()
