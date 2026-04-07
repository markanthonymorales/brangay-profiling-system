import customtkinter as ctk
from datetime import datetime, date
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.data_table import DataTable
from ui.components.chart_widget import ChartWidget
from ui.components.form_fields import LabeledEntry, LabeledNumberEntry, LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from auth.auth_manager import AuthManager
from services.barangay_service import get_all_districts, get_barangays_by_district
from services.disaster_service import (
    DISASTER_TYPES, RISK_LEVELS, DISASTER_SEVERITY, DISASTER_STATUSES,
    RESOURCE_TYPES, RESOURCE_UNITS,
    save_disaster_risk_profile, get_disaster_risk_profiles,
    save_disaster_incident, delete_disaster_incident, get_disaster_incidents,
    save_emergency_resource, delete_emergency_resource, get_emergency_resources,
    get_disaster_stats, get_disaster_trend, get_high_risk_barangays_disaster,
    get_expiring_resources,
)

COLORS = {
    "blue": "#1E88E5", "green": "#43A047", "orange": "#FB8C00",
    "red": "#E53935", "purple": "#7B1FA2", "pink": "#E91E63",
    "teal": "#00897B", "yellow": "#FDD835", "grey": "#757575",
    "cyan": "#00ACC1", "lime": "#C0CA33",
}

SEVERITY_COLORS = {
    "low": COLORS["green"], "medium": COLORS["yellow"],
    "high": COLORS["orange"], "critical": COLORS["red"],
}

TYPE_COLORS = {
    "flood": COLORS["blue"], "fire": COLORS["red"], "earthquake": COLORS["orange"],
    "typhoon": COLORS["purple"], "landslide": COLORS["teal"], "storm_surge": COLORS["cyan"],
}


class DisasterView(ctk.CTkFrame):
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
            self, text="Disaster & Safety",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12,
                                        command=self._on_tab_change)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._built_tabs = set()

        self._tabview.add("Risk Profiles")
        self._tabview.add("Disaster Incidents")
        self._tabview.add("Emergency Resources")
        self._tabview.add("Disaster Overview")
        self._tabview.add("Resource Status")

        self._build_risk_profiles_tab()
        self._built_tabs.add("Risk Profiles")

    def _on_tab_change(self):
        current = self._tabview.get()
        if current in self._built_tabs:
            return
        self._built_tabs.add(current)
        if current == "Disaster Incidents":
            self._build_disaster_incidents_tab()
        elif current == "Emergency Resources":
            self._build_emergency_resources_tab()
        elif current == "Disaster Overview":
            self._build_disaster_overview_tab()
        elif current == "Resource Status":
            self._build_resource_status_tab()

    # ── Tab 1: Risk Profiles ──────────────────────────────────

    def _build_risk_profiles_tab(self):
        tab = self._tabview.tab("Risk Profiles")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._rp_district = LabeledDropdown(controls, label="District", values=["All"] + district_names,
                                            command=self._on_rp_district_change)
        self._rp_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._rp_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._rp_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        years = [str(y) for y in range(date.today().year, date.today().year - 6, -1)]
        self._rp_year = LabeledDropdown(controls, label="Year", values=["All"] + years)
        self._rp_year.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(btn_frame, text="Filter", command=self._filter_risk_profiles,
                      font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(btn_frame, text="+ Add", command=self._add_risk_profile_dialog,
                          font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                          text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        self._rp_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                      text_color=TEXT_SECONDARY)
        self._rp_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "year", "title": "Year", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "flood_prone", "title": "Flood Prone", "width": 1},
            {"key": "landslide_prone", "title": "Landslide", "width": 1},
            {"key": "fire_risk_level", "title": "Fire Risk", "width": 1},
            {"key": "earthquake_risk", "title": "Earthquake Risk", "width": 1},
            {"key": "storm_surge_risk", "title": "Storm Surge", "width": 1},
            {"key": "evacuation_center_count", "title": "Evac Centers", "width": 1},
        ]
        self._rp_table = DataTable(tab, columns=columns, on_row_click=self._on_rp_row_click)
        self._rp_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_rp_district_change(self, district_name: str):
        if district_name == "All":
            self._rp_barangay.set_values(["All"])
            self._rp_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._rp_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._rp_barangay.set("All")

    def _filter_risk_profiles(self):
        district = self._rp_district.get()
        brgy_name = self._rp_barangay.get()
        year_str = self._rp_year.get()

        year_filter = int(year_str) if year_str != "All" else None

        # Determine which barangays to query
        if brgy_name != "All" and district != "All":
            brgy_map = self._load_barangays(district)
            barangay_id = brgy_map.get(brgy_name)
            if barangay_id:
                rows = get_disaster_risk_profiles(barangay_id)
                # Attach barangay_name
                for r in rows:
                    r["barangay_name"] = brgy_name
            else:
                rows = []
        elif district != "All":
            brgy_map = self._load_barangays(district)
            rows = []
            for bname, bid in brgy_map.items():
                for r in get_disaster_risk_profiles(bid):
                    r["barangay_name"] = bname
                    rows.append(r)
        else:
            # All districts — iterate all
            rows = []
            for dname, did in self._district_map.items():
                brgy_map = self._load_barangays(dname)
                for bname, bid in brgy_map.items():
                    for r in get_disaster_risk_profiles(bid):
                        r["barangay_name"] = bname
                        rows.append(r)

        # Apply year filter
        if year_filter is not None:
            rows = [r for r in rows if r["year"] == year_filter]

        # Format boolean display
        display_rows = []
        for r in rows:
            display_rows.append({
                **r,
                "flood_prone": "Yes" if r.get("flood_prone") else "No",
                "landslide_prone": "Yes" if r.get("landslide_prone") else "No",
            })

        self._rp_table.set_data(display_rows)
        self._rp_count.configure(text=f"Showing {len(display_rows)} record(s)")

    def _add_risk_profile_dialog(self):
        self._risk_profile_dialog()

    def _on_rp_row_click(self, row_data):
        self._risk_profile_dialog(row_data)

    def _risk_profile_dialog(self, existing: dict | None = None):
        is_edit = existing is not None
        title = "Edit Risk Profile" if is_edit else "Add Risk Profile"

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("480x560")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=title, font=(FONT_FAMILY, 16, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(15, 10))

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20)

        district_names = [d["name"] for d in self._districts]
        d_district = LabeledDropdown(scroll, label="District", values=district_names, required=True)
        d_district.pack(fill="x", pady=2)

        d_barangay = LabeledDropdown(scroll, label="Barangay", values=[], required=True)
        d_barangay.pack(fill="x", pady=2)

        def on_district_sel(dn):
            brgy_map = self._load_barangays(dn)
            names = list(brgy_map.keys())
            d_barangay.set_values(names)
            if names:
                d_barangay.set(names[0])

        d_district._dropdown.configure(command=on_district_sel)
        if district_names:
            on_district_sel(district_names[0])

        years = [str(y) for y in range(date.today().year, date.today().year - 10, -1)]
        d_year = LabeledDropdown(scroll, label="Year", values=years, required=True)
        d_year.pack(fill="x", pady=2)

        # Boolean checkboxes
        flood_var = ctk.BooleanVar(value=False)
        flood_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        flood_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(flood_frame, text="Flood Prone", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                     text_color=TEXT_PRIMARY, width=120, anchor="w").pack(side="left")
        ctk.CTkCheckBox(flood_frame, text="", variable=flood_var, width=30).pack(side="left")

        landslide_var = ctk.BooleanVar(value=False)
        ls_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ls_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(ls_frame, text="Landslide Prone", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                     text_color=TEXT_PRIMARY, width=120, anchor="w").pack(side="left")
        ctk.CTkCheckBox(ls_frame, text="", variable=landslide_var, width=30).pack(side="left")

        d_fire_risk = LabeledDropdown(scroll, label="Fire Risk Level", values=RISK_LEVELS)
        d_fire_risk.pack(fill="x", pady=2)

        d_earthquake = LabeledDropdown(scroll, label="Earthquake Risk", values=RISK_LEVELS)
        d_earthquake.pack(fill="x", pady=2)

        d_storm = LabeledDropdown(scroll, label="Storm Surge Risk", values=RISK_LEVELS)
        d_storm.pack(fill="x", pady=2)

        d_evac_count = LabeledNumberEntry(scroll, label="Evacuation Center Count")
        d_evac_count.pack(fill="x", pady=2)

        d_evac_cap = LabeledNumberEntry(scroll, label="Evacuation Capacity")
        d_evac_cap.pack(fill="x", pady=2)

        # Pre-fill for edit
        if is_edit:
            edit_district = existing.get("district_name", "")
            edit_barangay = existing.get("barangay_name", "")
            # Map display "Yes/No" back to bool
            flood_val = existing.get("flood_prone") in (True, "Yes")
            ls_val = existing.get("landslide_prone") in (True, "Yes")
            flood_var.set(flood_val)
            landslide_var.set(ls_val)

            if edit_district and edit_district in district_names:
                d_district.set(edit_district)
                on_district_sel(edit_district)
                if edit_barangay:
                    d_barangay.set(edit_barangay)
            d_year.set(str(existing.get("year", date.today().year)))
            d_fire_risk.set(existing.get("fire_risk_level") or RISK_LEVELS[0])
            d_earthquake.set(existing.get("earthquake_risk") or RISK_LEVELS[0])
            d_storm.set(existing.get("storm_surge_risk") or RISK_LEVELS[0])
            if existing.get("evacuation_center_count"):
                d_evac_count.set(str(existing["evacuation_center_count"]))
            if existing.get("evacuation_capacity"):
                d_evac_cap.set(str(existing["evacuation_capacity"]))

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
                year = int(d_year.get())
            except (ValueError, TypeError):
                error_label.configure(text="Invalid year.")
                return

            data = {
                "flood_prone": flood_var.get(),
                "landslide_prone": landslide_var.get(),
                "fire_risk_level": d_fire_risk.get(),
                "earthquake_risk": d_earthquake.get(),
                "storm_surge_risk": d_storm.get(),
                "evacuation_center_count": d_evac_count.get_int(default=0),
                "evacuation_capacity": d_evac_cap.get_int(default=0),
            }

            success, msg = save_disaster_risk_profile(brgy_id, year, data, self._get_user_id())
            if success:
                dialog.destroy()
                self._filter_risk_profiles()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(btn_frame, text="Save", command=do_save,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    # ── Tab 2: Disaster Incidents ─────────────────────────────

    def _build_disaster_incidents_tab(self):
        tab = self._tabview.tab("Disaster Incidents")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._di_district = LabeledDropdown(controls, label="District", values=["All"] + district_names,
                                            command=self._on_di_district_change)
        self._di_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._di_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._di_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._di_type = LabeledDropdown(controls, label="Type", values=["All"] + DISASTER_TYPES)
        self._di_type.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._di_severity = LabeledDropdown(controls, label="Severity", values=["All"] + DISASTER_SEVERITY)
        self._di_severity.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(btn_frame, text="Filter", command=self._filter_disaster_incidents,
                      font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(btn_frame, text="+ Add", command=self._add_disaster_incident_dialog,
                          font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                          text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        self._di_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                      text_color=TEXT_SECONDARY)
        self._di_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "date_occurred", "title": "Date", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "disaster_type", "title": "Type", "width": 1},
            {"key": "severity", "title": "Severity", "width": 1},
            {"key": "affected_families", "title": "Families", "width": 1},
            {"key": "casualties", "title": "Casualties", "width": 1},
            {"key": "status", "title": "Status", "width": 1},
        ]
        self._di_table = DataTable(tab, columns=columns, on_row_click=self._on_di_row_click)
        self._di_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_di_district_change(self, district_name: str):
        if district_name == "All":
            self._di_barangay.set_values(["All"])
            self._di_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._di_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._di_barangay.set("All")

    def _filter_disaster_incidents(self):
        district = self._di_district.get()
        brgy_name = self._di_barangay.get()
        d_type = self._di_type.get()
        sev = self._di_severity.get()

        barangay_id = None
        if brgy_name != "All" and district != "All":
            brgy_map = self._load_barangays(district)
            barangay_id = brgy_map.get(brgy_name)

        data = get_disaster_incidents(
            barangay_id=barangay_id,
            disaster_type=d_type if d_type != "All" else None,
            severity=sev if sev != "All" else None,
        )
        self._di_table.set_data(data)
        self._di_count.configure(text=f"Showing {len(data)} incident(s)")

    def _add_disaster_incident_dialog(self):
        self._disaster_incident_dialog()

    def _on_di_row_click(self, row_data):
        self._disaster_incident_dialog(row_data)

    def _disaster_incident_dialog(self, existing: dict | None = None):
        is_edit = existing is not None
        title = "Edit Disaster Incident" if is_edit else "Add Disaster Incident"

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("480x580")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=title, font=(FONT_FAMILY, 16, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(15, 10))

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20)

        district_names = [d["name"] for d in self._districts]
        d_district = LabeledDropdown(scroll, label="District", values=district_names, required=True)
        d_district.pack(fill="x", pady=2)

        d_barangay = LabeledDropdown(scroll, label="Barangay", values=[], required=True)
        d_barangay.pack(fill="x", pady=2)

        def on_district_sel(dn):
            brgy_map = self._load_barangays(dn)
            names = list(brgy_map.keys())
            d_barangay.set_values(names)
            if names:
                d_barangay.set(names[0])

        d_district._dropdown.configure(command=on_district_sel)
        if district_names:
            on_district_sel(district_names[0])

        d_type = LabeledDropdown(scroll, label="Disaster Type", values=DISASTER_TYPES, required=True)
        d_type.pack(fill="x", pady=2)

        d_severity = LabeledDropdown(scroll, label="Severity", values=DISASTER_SEVERITY)
        d_severity.pack(fill="x", pady=2)

        d_date = LabeledEntry(scroll, label="Date (YYYY-MM-DD)", required=True,
                              placeholder=date.today().strftime("%Y-%m-%d"))
        d_date.set(date.today().strftime("%Y-%m-%d"))
        d_date.pack(fill="x", pady=2)

        d_affected = LabeledNumberEntry(scroll, label="Affected Families")
        d_affected.pack(fill="x", pady=2)

        d_casualties = LabeledNumberEntry(scroll, label="Casualties")
        d_casualties.pack(fill="x", pady=2)

        d_damages = LabeledEntry(scroll, label="Damages Estimated (PHP)")
        d_damages.pack(fill="x", pady=2)

        d_response = LabeledEntry(scroll, label="Response Team")
        d_response.pack(fill="x", pady=2)

        d_status = LabeledDropdown(scroll, label="Status", values=DISASTER_STATUSES)
        d_status.pack(fill="x", pady=2)

        d_desc = LabeledEntry(scroll, label="Description")
        d_desc.pack(fill="x", pady=2)

        if is_edit:
            edit_district = existing.get("district_name", "")
            edit_barangay = existing.get("barangay_name", "")
            if edit_district and edit_district in district_names:
                d_district.set(edit_district)
                on_district_sel(edit_district)
                if edit_barangay:
                    d_barangay.set(edit_barangay)
            d_type.set(existing.get("disaster_type", DISASTER_TYPES[0]))
            d_severity.set(existing.get("severity", "low"))
            d_date.set(existing.get("date_occurred", ""))
            d_status.set(existing.get("status", "reported"))
            if existing.get("affected_families"):
                d_affected.set(str(existing["affected_families"]))
            if existing.get("casualties"):
                d_casualties.set(str(existing["casualties"]))
            if existing.get("damages_estimated"):
                d_damages.set(str(existing["damages_estimated"]))
            d_response.set(existing.get("response_team", ""))
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

            try:
                damages_raw = d_damages.get().strip()
                damages_val = float(damages_raw) if damages_raw else None
            except ValueError:
                error_label.configure(text="Damages must be a number.")
                return

            data = {
                "disaster_type": d_type.get(),
                "severity": d_severity.get(),
                "date_occurred": date_val,
                "affected_families": d_affected.get_int(default=0),
                "casualties": d_casualties.get_int(default=0),
                "damages_estimated": damages_val,
                "response_team": d_response.get() or None,
                "status": d_status.get(),
                "description": d_desc.get() or None,
            }
            if is_edit:
                data["id"] = existing["id"]

            success, msg = save_disaster_incident(brgy_id, data, self._get_user_id())
            if success:
                dialog.destroy()
                self._filter_disaster_incidents()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(btn_frame, text="Save", command=do_save,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        if is_edit and self._auth.check_permission("delete_data"):
            def do_delete():
                success, msg = delete_disaster_incident(existing["id"], self._get_user_id())
                dialog.destroy()
                self._filter_disaster_incidents()
                dt = "success" if success else "error"
                MessageDialog(self, title="Delete", message=msg, dialog_type=dt)

            ctk.CTkButton(btn_frame, text="Delete", command=do_delete,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=DANGER_COLOR,
                          text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    # ── Tab 3: Emergency Resources ────────────────────────────

    def _build_emergency_resources_tab(self):
        tab = self._tabview.tab("Emergency Resources")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._er_district = LabeledDropdown(controls, label="District", values=["All"] + district_names,
                                            command=self._on_er_district_change)
        self._er_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._er_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._er_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._er_type = LabeledDropdown(controls, label="Type", values=["All"] + RESOURCE_TYPES)
        self._er_type.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(btn_frame, text="Filter", command=self._filter_emergency_resources,
                      font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(btn_frame, text="+ Add", command=self._add_resource_dialog,
                          font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                          text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        self._er_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                      text_color=TEXT_SECONDARY)
        self._er_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "resource_type", "title": "Type", "width": 1},
            {"key": "name", "title": "Name", "width": 2},
            {"key": "quantity", "title": "Qty", "width": 1},
            {"key": "unit", "title": "Unit", "width": 1},
            {"key": "last_restocked", "title": "Last Restocked", "width": 1},
            {"key": "expiry_date", "title": "Expiry Date", "width": 1},
        ]
        self._er_table = DataTable(tab, columns=columns, on_row_click=self._on_er_row_click)
        self._er_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_er_district_change(self, district_name: str):
        if district_name == "All":
            self._er_barangay.set_values(["All"])
            self._er_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._er_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._er_barangay.set("All")

    def _filter_emergency_resources(self):
        district = self._er_district.get()
        brgy_name = self._er_barangay.get()
        r_type = self._er_type.get()

        barangay_id = None
        if brgy_name != "All" and district != "All":
            brgy_map = self._load_barangays(district)
            barangay_id = brgy_map.get(brgy_name)

        data = get_emergency_resources(
            barangay_id=barangay_id,
            resource_type=r_type if r_type != "All" else None,
        )
        self._er_table.set_data(data)
        self._er_count.configure(text=f"Showing {len(data)} resource(s)")

    def _add_resource_dialog(self):
        self._resource_dialog()

    def _on_er_row_click(self, row_data):
        self._resource_dialog(row_data)

    def _resource_dialog(self, existing: dict | None = None):
        is_edit = existing is not None
        title = "Edit Emergency Resource" if is_edit else "Add Emergency Resource"

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("480x560")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=title, font=(FONT_FAMILY, 16, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(15, 10))

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20)

        district_names = [d["name"] for d in self._districts]
        d_district = LabeledDropdown(scroll, label="District", values=district_names, required=True)
        d_district.pack(fill="x", pady=2)

        d_barangay = LabeledDropdown(scroll, label="Barangay", values=[], required=True)
        d_barangay.pack(fill="x", pady=2)

        def on_district_sel(dn):
            brgy_map = self._load_barangays(dn)
            names = list(brgy_map.keys())
            d_barangay.set_values(names)
            if names:
                d_barangay.set(names[0])

        d_district._dropdown.configure(command=on_district_sel)
        if district_names:
            on_district_sel(district_names[0])

        d_rtype = LabeledDropdown(scroll, label="Resource Type", values=RESOURCE_TYPES, required=True)
        d_rtype.pack(fill="x", pady=2)

        d_name = LabeledEntry(scroll, label="Name", required=True)
        d_name.pack(fill="x", pady=2)

        d_quantity = LabeledNumberEntry(scroll, label="Quantity")
        d_quantity.pack(fill="x", pady=2)

        d_unit = LabeledDropdown(scroll, label="Unit", values=RESOURCE_UNITS)
        d_unit.pack(fill="x", pady=2)

        d_location = LabeledEntry(scroll, label="Location Description")
        d_location.pack(fill="x", pady=2)

        d_restocked = LabeledEntry(scroll, label="Last Restocked (YYYY-MM-DD)")
        d_restocked.pack(fill="x", pady=2)

        d_expiry = LabeledEntry(scroll, label="Expiry Date (YYYY-MM-DD)")
        d_expiry.pack(fill="x", pady=2)

        if is_edit:
            edit_district = existing.get("district_name", "")
            edit_barangay = existing.get("barangay_name", "")
            if edit_district and edit_district in district_names:
                d_district.set(edit_district)
                on_district_sel(edit_district)
                if edit_barangay:
                    d_barangay.set(edit_barangay)
            d_rtype.set(existing.get("resource_type", RESOURCE_TYPES[0]))
            d_name.set(existing.get("name", ""))
            if existing.get("quantity") is not None:
                d_quantity.set(str(existing["quantity"]))
            d_unit.set(existing.get("unit") or RESOURCE_UNITS[0])
            d_location.set(existing.get("location_description", ""))
            d_restocked.set(existing.get("last_restocked", ""))
            d_expiry.set(existing.get("expiry_date", ""))

        error_label = ctk.CTkLabel(dialog, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                   text_color=DANGER_COLOR)
        error_label.pack(pady=3)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def _parse_date_optional(s: str):
            s = s.strip()
            if not s:
                return None
            try:
                return date.fromisoformat(s)
            except ValueError:
                return None

        def do_save():
            brgy_name = d_barangay.get()
            district_name = d_district.get()
            brgy_map = self._load_barangays(district_name)
            brgy_id = brgy_map.get(brgy_name)
            if not brgy_id:
                error_label.configure(text="Please select a barangay.")
                return

            name_val = d_name.get().strip()
            if not name_val:
                error_label.configure(text="Name is required.")
                return

            restocked_str = d_restocked.get().strip()
            expiry_str = d_expiry.get().strip()

            if restocked_str:
                restocked_val = _parse_date_optional(restocked_str)
                if restocked_val is None:
                    error_label.configure(text="Invalid Last Restocked date format. Use YYYY-MM-DD.")
                    return
            else:
                restocked_val = None

            if expiry_str:
                expiry_val = _parse_date_optional(expiry_str)
                if expiry_val is None:
                    error_label.configure(text="Invalid Expiry Date format. Use YYYY-MM-DD.")
                    return
            else:
                expiry_val = None

            data = {
                "resource_type": d_rtype.get(),
                "name": name_val,
                "quantity": d_quantity.get_int(default=0),
                "unit": d_unit.get() or None,
                "location_description": d_location.get() or None,
                "last_restocked": restocked_val,
                "expiry_date": expiry_val,
            }
            if is_edit:
                data["id"] = existing["id"]

            success, msg = save_emergency_resource(brgy_id, data, self._get_user_id())
            if success:
                dialog.destroy()
                self._filter_emergency_resources()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(btn_frame, text="Save", command=do_save,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        if is_edit and self._auth.check_permission("delete_data"):
            def do_delete():
                success, msg = delete_emergency_resource(existing["id"], self._get_user_id())
                dialog.destroy()
                self._filter_emergency_resources()
                dt = "success" if success else "error"
                MessageDialog(self, title="Delete", message=msg, dialog_type=dt)

            ctk.CTkButton(btn_frame, text="Delete", command=do_delete,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=DANGER_COLOR,
                          text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    # ── Tab 4: Disaster Overview ──────────────────────────────

    def _build_disaster_overview_tab(self):
        tab = self._tabview.tab("Disaster Overview")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._do_scope = LabeledDropdown(controls, label="Scope",
                                         values=["City-Wide", "By District", "By Barangay"])
        self._do_scope.pack(side="left", padx=(0, 8), fill="x", expand=True)

        district_names = [d["name"] for d in self._districts]
        self._do_district = LabeledDropdown(controls, label="District", values=district_names,
                                            command=self._on_do_district_change)
        self._do_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._do_barangay = LabeledDropdown(controls, label="Barangay", values=[])
        self._do_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkButton(controls, text="Update", command=self._update_disaster_overview,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", pady=(18, 0))

        self._do_chart = ChartWidget(tab, figsize=(9, 5))
        self._do_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _on_do_district_change(self, dn):
        brgy_map = self._load_barangays(dn)
        names = list(brgy_map.keys())
        self._do_barangay.set_values(names)
        if names:
            self._do_barangay.set(names[0])

    def _update_disaster_overview(self):
        scope = self._do_scope.get()
        barangay_id = None
        district_id = None

        if scope == "By District":
            district_id = self._district_map.get(self._do_district.get())
        elif scope == "By Barangay":
            dn = self._do_district.get()
            brgy_map = self._load_barangays(dn)
            barangay_id = brgy_map.get(self._do_barangay.get())

        stats = get_disaster_stats(barangay_id=barangay_id, district_id=district_id)
        trend = get_disaster_trend(barangay_id=barangay_id, district_id=district_id)

        if stats["total"] == 0 and not trend:
            self._do_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No disaster data available for this selection.",
                ha="center", va="center", fontsize=12, color="#999999", transform=ax.transAxes))
            return

        def draw(fig):
            # Top-left: incidents by type (pie)
            ax1 = fig.add_subplot(221)
            by_type = stats["by_type"]
            if by_type:
                labels = list(by_type.keys())
                values = list(by_type.values())
                colors_list = [TYPE_COLORS.get(l, COLORS["grey"]) for l in labels]
                ax1.pie(values, labels=labels, colors=colors_list, autopct="%1.0f%%",
                        wedgeprops=dict(width=0.5), textprops={"fontsize": 7})
                ax1.set_title("Incidents by Type", fontsize=10)

            # Top-right: affected families by type (bar)
            ax2 = fig.add_subplot(222)
            # Use type breakdown for families if available; fall back to severity
            by_sev = stats["by_severity"]
            if by_sev:
                labels = list(by_sev.keys())
                values = list(by_sev.values())
                colors_list = [SEVERITY_COLORS.get(l, COLORS["grey"]) for l in labels]
                ax2.bar(labels, values, color=colors_list)
                ax2.set_title("By Severity", fontsize=10)
                ax2.set_ylabel("Count")
                ax2.tick_params(axis="x", labelsize=7)

            # Bottom: monthly trend (line)
            ax3 = fig.add_subplot(212)
            if trend:
                labels = [f"{d['year']}-{d['month']:02d}" for d in trend]
                counts = [d["count"] for d in trend]
                ax3.plot(labels, counts, marker="o", color=COLORS["blue"], linewidth=2)
                ax3.fill_between(range(len(labels)), counts, alpha=0.15, color=COLORS["blue"])
                ax3.set_title("Monthly Disaster Trend", fontsize=10)
                ax3.set_ylabel("Incidents")
                ax3.set_xticks(range(len(labels)))
                ax3.set_xticklabels(labels, rotation=45, fontsize=7)
                if len(labels) > 8:
                    step = max(1, len(labels) // 8)
                    ax3.set_xticks(range(0, len(labels), step))
                    ax3.set_xticklabels([labels[i] for i in range(0, len(labels), step)], rotation=45, fontsize=7)

            fig.subplots_adjust(hspace=0.45, wspace=0.4, top=0.92, bottom=0.12, left=0.12, right=0.95)

        self._do_chart.update_chart_multi(draw)

    # ── Tab 5: Resource Status ────────────────────────────────

    def _build_resource_status_tab(self):
        tab = self._tabview.tab("Resource Status")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._rs_days = LabeledDropdown(controls, label="Expiry Window",
                                        values=["30 days", "60 days", "90 days", "180 days"])
        self._rs_days.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkButton(controls, text="Refresh", command=self._update_resource_status,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", pady=(18, 0))

        self._rs_info = ctk.CTkLabel(tab, text="Resources expiring within selected window",
                                     font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY)
        self._rs_info.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 3))

        self._rs_chart = ChartWidget(tab, figsize=(9, 4))
        self._rs_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _update_resource_status(self):
        days_str = self._rs_days.get()
        days = int(days_str.split()[0])

        expiring = get_expiring_resources(days_ahead=days)
        all_resources = get_emergency_resources(limit=500)

        # Count by resource type for all resources
        type_counts: dict[str, int] = {}
        for r in all_resources:
            rt = r["resource_type"]
            type_counts[rt] = type_counts.get(rt, 0) + 1

        self._rs_info.configure(text=f"{len(expiring)} resource(s) expiring within {days} days")

        if not expiring and not type_counts:
            self._rs_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No resource data available.",
                ha="center", va="center", fontsize=12, color="#999999", transform=ax.transAxes))
            return

        def draw(fig):
            # Left: expiring resources by type (bar)
            ax1 = fig.add_subplot(121)
            if expiring:
                exp_by_type: dict[str, int] = {}
                for r in expiring:
                    rt = r["resource_type"]
                    exp_by_type[rt] = exp_by_type.get(rt, 0) + 1
                labels = list(exp_by_type.keys())
                values = list(exp_by_type.values())
                expired_counts = [sum(1 for r in expiring if r["resource_type"] == l and r.get("is_expired")) for l in labels]
                bar_colors = [COLORS["red"] if e > 0 else COLORS["orange"] for e in expired_counts]
                bars = ax1.bar(labels, values, color=bar_colors)
                ax1.set_title(f"Expiring ({days}d) by Type", fontsize=10)
                ax1.set_ylabel("Count")
                ax1.tick_params(axis="x", rotation=30, labelsize=7)
                for bar, val in zip(bars, values):
                    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                             str(val), ha="center", va="bottom", fontsize=8)
            else:
                ax1.text(0.5, 0.5, "No expiring resources", ha="center", va="center",
                         fontsize=10, color="#999999", transform=ax1.transAxes)
                ax1.set_title(f"Expiring ({days}d) by Type", fontsize=10)

            # Right: all resources count by type (pie)
            ax2 = fig.add_subplot(122)
            if type_counts:
                type_colors_list = [
                    COLORS.get(["blue", "green", "orange", "red", "purple"][i % 5], COLORS["grey"])
                    for i in range(len(type_counts))
                ]
                ax2.pie(list(type_counts.values()), labels=list(type_counts.keys()),
                        colors=type_colors_list, autopct="%1.0f%%",
                        wedgeprops=dict(width=0.5), textprops={"fontsize": 7})
                ax2.set_title("All Resources by Type", fontsize=10)

            fig.subplots_adjust(hspace=0.3, wspace=0.4, top=0.9, bottom=0.15, left=0.1, right=0.95)

        self._rs_chart.update_chart_multi(draw)

    def refresh(self):
        pass
