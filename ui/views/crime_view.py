import customtkinter as ctk
import numpy as np
from datetime import datetime, date
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.data_table import DataTable
from ui.components.chart_widget import ChartWidget
from ui.components.form_fields import LabeledEntry, LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from ui.dialogs.confirm_dialog import ConfirmDialog
from auth.auth_manager import AuthManager
from services.barangay_service import get_all_districts, get_barangays_by_district
from services.crime_service import (
    CRIME_TYPES, TRAFFIC_TYPES, SEVERITY_LEVELS, INCIDENT_STATUSES,
    save_crime_incident, delete_crime_incident, get_crime_incidents,
    save_traffic_incident, delete_traffic_incident, get_traffic_incidents,
    get_crime_stats, get_traffic_stats, get_crime_trend, get_traffic_trend,
    get_high_risk_barangays, get_crime_forecast,
)

COLORS = {
    "blue": "#1E88E5", "green": "#43A047", "orange": "#FB8C00",
    "red": "#E53935", "purple": "#7B1FA2", "pink": "#E91E63",
    "teal": "#00897B", "yellow": "#FDD835", "grey": "#757575",
}

SEVERITY_COLORS = {"low": COLORS["green"], "medium": COLORS["yellow"],
                   "high": COLORS["orange"], "critical": COLORS["red"]}


class CrimeView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._districts = get_all_districts()
        self._district_map = {d["name"]: d["id"] for d in self._districts}
        self._barangay_maps: dict[str, dict] = {}
        self._build_ui()

    def _get_user_id(self) -> int:
        user = self._auth.get_current_user()
        return user.id if user else 0

    def _load_barangays(self, district_name: str) -> dict[str, int]:
        if district_name not in self._barangay_maps:
            did = self._district_map.get(district_name)
            if did:
                brgys = get_barangays_by_district(did)
                self._barangay_maps[district_name] = {b["name"]: b["id"] for b in brgys}
            else:
                self._barangay_maps[district_name] = {}
        return self._barangay_maps[district_name]

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Crime & Safety",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_crime_incidents_tab()
        self._build_traffic_incidents_tab()
        self._build_crime_overview_tab()
        self._build_high_risk_tab()
        self._build_forecast_tab()

    # ── Tab 1: Crime Incidents ────────────────────────────────

    def _build_crime_incidents_tab(self):
        tab = self._tabview.add("Crime Incidents")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._ci_district = LabeledDropdown(controls, label="District", values=["All"] + district_names,
                                            command=self._on_ci_district_change)
        self._ci_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._ci_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._ci_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._ci_type = LabeledDropdown(controls, label="Type", values=["All"] + CRIME_TYPES)
        self._ci_type.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._ci_severity = LabeledDropdown(controls, label="Severity", values=["All"] + SEVERITY_LEVELS)
        self._ci_severity.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(btn_frame, text="Filter", command=self._filter_crime,
                      font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(btn_frame, text="+ Add", command=self._add_crime_dialog,
                          font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                          text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        self._ci_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                      text_color=TEXT_SECONDARY)
        self._ci_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "date_occurred", "title": "Date", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "crime_type", "title": "Type", "width": 1},
            {"key": "severity", "title": "Severity", "width": 1},
            {"key": "status", "title": "Status", "width": 1},
            {"key": "description", "title": "Description", "width": 3},
        ]
        self._ci_table = DataTable(tab, columns=columns, on_row_click=self._on_crime_row_click)
        self._ci_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_ci_district_change(self, district_name: str):
        if district_name == "All":
            self._ci_barangay.set_values(["All"])
            self._ci_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._ci_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._ci_barangay.set("All")

    def _filter_crime(self):
        district = self._ci_district.get()
        brgy_name = self._ci_barangay.get()
        c_type = self._ci_type.get()
        sev = self._ci_severity.get()

        barangay_id = None
        if brgy_name != "All" and district != "All":
            brgy_map = self._load_barangays(district)
            barangay_id = brgy_map.get(brgy_name)

        data = get_crime_incidents(
            barangay_id=barangay_id,
            crime_type=c_type if c_type != "All" else None,
            severity=sev if sev != "All" else None,
        )
        self._ci_table.set_data(data)
        self._ci_count.configure(text=f"Showing {len(data)} incident(s)")

    def _add_crime_dialog(self):
        self._incident_dialog("crime")

    def _on_crime_row_click(self, row_data):
        self._incident_dialog("crime", row_data)

    # ── Tab 2: Traffic Incidents ──────────────────────────────

    def _build_traffic_incidents_tab(self):
        tab = self._tabview.add("Traffic Incidents")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._ti_district = LabeledDropdown(controls, label="District", values=["All"] + district_names,
                                            command=self._on_ti_district_change)
        self._ti_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._ti_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._ti_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._ti_type = LabeledDropdown(controls, label="Type", values=["All"] + TRAFFIC_TYPES)
        self._ti_type.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._ti_severity = LabeledDropdown(controls, label="Severity", values=["All"] + SEVERITY_LEVELS)
        self._ti_severity.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left")

        ctk.CTkButton(btn_frame, text="Filter", command=self._filter_traffic,
                      font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(btn_frame, text="+ Add", command=self._add_traffic_dialog,
                          font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                          text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        self._ti_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                      text_color=TEXT_SECONDARY)
        self._ti_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "date_occurred", "title": "Date", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "incident_type", "title": "Type", "width": 1},
            {"key": "severity", "title": "Severity", "width": 1},
            {"key": "status", "title": "Status", "width": 1},
            {"key": "description", "title": "Description", "width": 3},
        ]
        self._ti_table = DataTable(tab, columns=columns, on_row_click=self._on_traffic_row_click)
        self._ti_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_ti_district_change(self, district_name: str):
        if district_name == "All":
            self._ti_barangay.set_values(["All"])
            self._ti_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._ti_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._ti_barangay.set("All")

    def _filter_traffic(self):
        district = self._ti_district.get()
        brgy_name = self._ti_barangay.get()
        t_type = self._ti_type.get()
        sev = self._ti_severity.get()

        barangay_id = None
        if brgy_name != "All" and district != "All":
            brgy_map = self._load_barangays(district)
            barangay_id = brgy_map.get(brgy_name)

        data = get_traffic_incidents(
            barangay_id=barangay_id,
            incident_type=t_type if t_type != "All" else None,
            severity=sev if sev != "All" else None,
        )
        self._ti_table.set_data(data)
        self._ti_count.configure(text=f"Showing {len(data)} incident(s)")

    def _add_traffic_dialog(self):
        self._incident_dialog("traffic")

    def _on_traffic_row_click(self, row_data):
        self._incident_dialog("traffic", row_data)

    # ── Shared Incident Dialog ────────────────────────────────

    def _incident_dialog(self, kind: str, existing: dict | None = None):
        is_edit = existing is not None
        title = f"{'Edit' if is_edit else 'Add'} {'Crime' if kind == 'crime' else 'Traffic'} Incident"
        types = CRIME_TYPES if kind == "crime" else TRAFFIC_TYPES
        type_label = "Crime Type" if kind == "crime" else "Incident Type"
        type_key = "crime_type" if kind == "crime" else "incident_type"

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("480x500")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=title, font=(FONT_FAMILY, 16, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(15, 10))

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20)

        # District / Barangay
        district_names = [d["name"] for d in self._districts]
        d_district = LabeledDropdown(scroll, label="District", values=district_names, required=True)
        d_district.pack(fill="x", pady=2)

        d_barangay = LabeledDropdown(scroll, label="Barangay", values=[], required=True)
        d_barangay.pack(fill="x", pady=2)

        def on_district_sel(dn):
            brgy_map = self._load_barangays(dn)
            d_barangay.set_values(list(brgy_map.keys()))
            names = list(brgy_map.keys())
            if names:
                d_barangay.set(names[0])

        d_district.set_values(district_names)
        d_district._dropdown.configure(command=on_district_sel)
        if district_names:
            on_district_sel(district_names[0])

        # Type
        d_type = LabeledDropdown(scroll, label=type_label, values=types, required=True)
        d_type.pack(fill="x", pady=2)

        # Severity
        d_severity = LabeledDropdown(scroll, label="Severity", values=SEVERITY_LEVELS)
        d_severity.pack(fill="x", pady=2)

        # Date
        d_date = LabeledEntry(scroll, label="Date (YYYY-MM-DD)", required=True,
                              placeholder=date.today().strftime("%Y-%m-%d"))
        d_date.set(date.today().strftime("%Y-%m-%d"))
        d_date.pack(fill="x", pady=2)

        # Status
        d_status = LabeledDropdown(scroll, label="Status", values=INCIDENT_STATUSES)
        d_status.pack(fill="x", pady=2)

        # Description
        d_desc = LabeledEntry(scroll, label="Description")
        d_desc.pack(fill="x", pady=2)

        # Pre-fill for edit
        if is_edit:
            d_type.set(existing.get(type_key, ""))
            d_severity.set(existing.get("severity", "low"))
            d_date.set(existing.get("date_occurred", ""))
            d_status.set(existing.get("status", "reported"))
            d_desc.set(existing.get("description", ""))

        error_label = ctk.CTkLabel(dialog, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                   text_color=DANGER_COLOR)
        error_label.pack(pady=3)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def do_save():
            brgy_name = d_barangay.get()
            district_name = d_district.get()
            brgy_map = self._load_barangays(district_name)
            brgy_id = brgy_map.get(brgy_name)
            if not brgy_id:
                error_label.configure(text="Please select a barangay.")
                return

            try:
                date_val = date.fromisoformat(d_date.get())
            except ValueError:
                error_label.configure(text="Invalid date format. Use YYYY-MM-DD.")
                return

            data = {
                type_key: d_type.get(),
                "severity": d_severity.get(),
                "date_occurred": date_val,
                "status": d_status.get(),
                "description": d_desc.get() or None,
            }
            if is_edit:
                data["id"] = existing["id"]

            if kind == "crime":
                success, msg = save_crime_incident(brgy_id, data, self._get_user_id())
            else:
                success, msg = save_traffic_incident(brgy_id, data, self._get_user_id())

            if success:
                dialog.destroy()
                if kind == "crime":
                    self._filter_crime()
                else:
                    self._filter_traffic()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(btn_frame, text="Save", command=do_save,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        if is_edit and self._auth.check_permission("delete_data"):
            def do_delete():
                if kind == "crime":
                    success, msg = delete_crime_incident(existing["id"], self._get_user_id())
                else:
                    success, msg = delete_traffic_incident(existing["id"], self._get_user_id())
                dialog.destroy()
                if kind == "crime":
                    self._filter_crime()
                else:
                    self._filter_traffic()
                dt = "success" if success else "error"
                MessageDialog(self, title="Delete", message=msg, dialog_type=dt)

            ctk.CTkButton(btn_frame, text="Delete", command=do_delete,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=DANGER_COLOR,
                          text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    # ── Tab 3: Crime Overview ─────────────────────────────────

    def _build_crime_overview_tab(self):
        tab = self._tabview.add("Crime Overview")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._co_scope = LabeledDropdown(controls, label="Scope",
                                         values=["City-Wide", "By District", "By Barangay"])
        self._co_scope.pack(side="left", padx=(0, 8), fill="x", expand=True)

        district_names = [d["name"] for d in self._districts]
        self._co_district = LabeledDropdown(controls, label="District", values=district_names,
                                            command=self._on_co_district_change)
        self._co_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._co_barangay = LabeledDropdown(controls, label="Barangay", values=[])
        self._co_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkButton(controls, text="Update", command=self._update_crime_overview,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", pady=(18, 0))

        self._co_chart = ChartWidget(tab, figsize=(9, 5))
        self._co_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _on_co_district_change(self, dn):
        brgy_map = self._load_barangays(dn)
        self._co_barangay.set_values(list(brgy_map.keys()))
        names = list(brgy_map.keys())
        if names:
            self._co_barangay.set(names[0])

    def _update_crime_overview(self):
        scope = self._co_scope.get()
        barangay_id = None
        district_id = None

        if scope == "By District":
            district_id = self._district_map.get(self._co_district.get())
        elif scope == "By Barangay":
            dn = self._co_district.get()
            brgy_map = self._load_barangays(dn)
            barangay_id = brgy_map.get(self._co_barangay.get())

        stats = get_crime_stats(barangay_id=barangay_id, district_id=district_id)
        trend = get_crime_trend(barangay_id=barangay_id, district_id=district_id)

        if stats["total"] == 0 and not trend:
            self._co_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No crime data available for this selection.",
                ha="center", va="center", fontsize=12, color="#999999", transform=ax.transAxes))
            return

        def draw(fig):
            # Top-left: by type
            ax1 = fig.add_subplot(221)
            by_type = stats["by_type"]
            if by_type:
                types = list(by_type.keys())
                counts = list(by_type.values())
                bars = ax1.barh(types, counts, color=COLORS["blue"])
                ax1.set_title("By Crime Type", fontsize=10)
                ax1.set_xlabel("Count")
                for bar, val in zip(bars, counts):
                    ax1.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                             str(val), va="center", fontsize=7)

            # Top-right: severity pie
            ax2 = fig.add_subplot(222)
            by_sev = stats["by_severity"]
            if by_sev:
                labels = list(by_sev.keys())
                values = list(by_sev.values())
                colors_list = [SEVERITY_COLORS.get(l, COLORS["grey"]) for l in labels]
                ax2.pie(values, labels=labels, colors=colors_list, autopct="%1.0f%%",
                        wedgeprops=dict(width=0.4))
                ax2.set_title("By Severity", fontsize=10)

            # Bottom: trend
            ax3 = fig.add_subplot(212)
            if trend:
                labels = [f"{d['year']}-{d['month']:02d}" for d in trend]
                counts = [d["count"] for d in trend]
                ax3.plot(labels, counts, marker="o", color=COLORS["red"], linewidth=2)
                ax3.set_title("Monthly Crime Trend", fontsize=10)
                ax3.set_ylabel("Incidents")
                if len(labels) > 6:
                    ax3.set_xticks(range(0, len(labels), max(1, len(labels) // 6)))
                ax3.tick_params(axis="x", rotation=45, labelsize=7)

            fig.subplots_adjust(hspace=0.4, wspace=0.4, top=0.92, bottom=0.12, left=0.12, right=0.95)

        self._co_chart.update_chart_multi(draw)

    # ── Tab 4: High-Risk Areas ────────────────────────────────

    def _build_high_risk_tab(self):
        tab = self._tabview.add("High-Risk Areas")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._hr_type = LabeledDropdown(controls, label="Risk Type", values=["crime", "traffic"])
        self._hr_type.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(controls, text="Refresh", command=self._update_high_risk,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", pady=(18, 0))

        self._hr_info = ctk.CTkLabel(tab, text="Top barangays by incident count (last 12 months)",
                                     font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY)
        self._hr_info.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 3))

        columns = [
            {"key": "rank", "title": "#", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 3},
            {"key": "district_name", "title": "District", "width": 3},
            {"key": "incident_count", "title": "Incidents", "width": 1},
            {"key": "common_type", "title": "Most Common", "width": 2},
            {"key": "dominant_severity", "title": "Severity", "width": 1},
        ]
        self._hr_table = DataTable(tab, columns=columns)
        self._hr_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _update_high_risk(self):
        risk_type = self._hr_type.get()
        data = get_high_risk_barangays(risk_type=risk_type, limit=20)
        self._hr_table.set_data(data)
        label = "crime" if risk_type == "crime" else "traffic"
        self._hr_info.configure(text=f"Top {len(data)} barangays by {label} incidents (last 12 months)")

    # ── Tab 5: Forecast ───────────────────────────────────────

    def _build_forecast_tab(self):
        tab = self._tabview.add("Forecast")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._fc_scope = LabeledDropdown(controls, label="Scope", values=["City-Wide", "By District", "By Barangay"])
        self._fc_scope.pack(side="left", padx=(0, 8), fill="x", expand=True)

        district_names = [d["name"] for d in self._districts]
        self._fc_district = LabeledDropdown(controls, label="District", values=district_names,
                                            command=self._on_fc_district_change)
        self._fc_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._fc_barangay = LabeledDropdown(controls, label="Barangay", values=[])
        self._fc_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkButton(controls, text="Generate Forecast", command=self._update_forecast,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=150, height=35).pack(side="left", pady=(18, 0))

        self._fc_label = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                                      text_color=TEXT_PRIMARY)
        self._fc_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 0))

        self._fc_chart = ChartWidget(tab, figsize=(9, 4))
        self._fc_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _on_fc_district_change(self, dn):
        brgy_map = self._load_barangays(dn)
        self._fc_barangay.set_values(list(brgy_map.keys()))
        names = list(brgy_map.keys())
        if names:
            self._fc_barangay.set(names[0])

    def _update_forecast(self):
        scope = self._fc_scope.get()
        barangay_id = None
        district_id = None

        if scope == "By District":
            district_id = self._district_map.get(self._fc_district.get())
        elif scope == "By Barangay":
            dn = self._fc_district.get()
            brgy_map = self._load_barangays(dn)
            barangay_id = brgy_map.get(self._fc_barangay.get())

        result = get_crime_forecast(barangay_id=barangay_id, district_id=district_id, months_ahead=6)

        trend_text = {
            "increasing": "Trend: INCREASING",
            "decreasing": "Trend: DECREASING",
            "stable": "Trend: STABLE",
            "insufficient_data": "Insufficient data (need 3+ months)",
        }
        trend_colors = {
            "increasing": DANGER_COLOR, "decreasing": ACCENT_COLOR,
            "stable": PRIMARY_COLOR, "insufficient_data": TEXT_SECONDARY,
        }
        self._fc_label.configure(
            text=trend_text.get(result["trend"], ""),
            text_color=trend_colors.get(result["trend"], TEXT_PRIMARY),
        )

        historical = result["historical"]
        forecast = result["forecast"]

        if not historical:
            self._fc_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No crime data available for forecasting.",
                ha="center", va="center", fontsize=12, color="#999999", transform=ax.transAxes))
            return

        if result["trend"] == "insufficient_data":
            def draw_insufficient(fig, ax):
                labels = [f"{d['year']}-{d['month']:02d}" for d in historical]
                counts = [d["count"] for d in historical]
                ax.bar(labels, counts, color=COLORS["blue"])
                ax.set_title("Crime Data (Need 3+ months for forecast)")
                ax.set_ylabel("Incidents")
            self._fc_chart.update_chart(draw_insufficient)
            return

        def draw(fig, ax):
            h_labels = [f"{d['year']}-{d['month']:02d}" for d in historical]
            h_counts = [d["count"] for d in historical]
            f_labels = [f"{d['year']}-{d['month']:02d}" for d in forecast]
            f_counts = [d["count"] for d in forecast]

            all_labels = h_labels + f_labels
            x_h = list(range(len(h_labels)))
            x_f = list(range(len(h_labels) - 1, len(all_labels)))

            ax.plot(x_h, h_counts, marker="o", color=COLORS["blue"], linewidth=2, label="Historical")

            # Connect last historical to first forecast
            f_line = [h_counts[-1]] + f_counts
            ax.plot(x_f, f_line, marker="s", color=COLORS["red"], linewidth=2,
                    linestyle="--", label="Forecast")

            ax.axvline(x=len(h_labels) - 1, color=COLORS["grey"], linestyle=":", alpha=0.5)
            ax.set_xticks(range(len(all_labels)))
            ax.set_xticklabels(all_labels, rotation=45, fontsize=7)
            ax.set_title("Crime Trend Forecast (6 Months)")
            ax.set_ylabel("Incidents")
            ax.legend(fontsize=9)

        self._fc_chart.update_chart(draw)

    def refresh(self):
        pass
