import customtkinter as ctk
from datetime import datetime
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
from services.health_service import (
    DISEASE_TYPES, save_health_statistics, get_health_statistics,
    get_health_stats_by_year, get_disease_trend, get_health_summary,
)
from services.social_welfare_service import (
    save_social_welfare_data, get_social_welfare_data,
    get_welfare_stats_by_year, get_welfare_summary,
)

COLORS = {
    "blue": "#1E88E5", "green": "#43A047", "orange": "#FB8C00",
    "red": "#E53935", "purple": "#7B1FA2", "pink": "#E91E63",
    "teal": "#00897B", "yellow": "#FDD835", "grey": "#757575",
}

YEAR_OPTIONS = ["All", "2025", "2024", "2023", "2022", "2021"]
CURRENT_YEAR = datetime.now().year


class HealthView(ctk.CTkFrame):
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
            self, text="Health & Welfare",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_health_statistics_tab()
        self._build_social_welfare_tab()
        self._build_health_overview_tab()
        self._build_high_risk_tab()

    # ── Tab 1: Health Statistics ──────────────────────────────

    def _build_health_statistics_tab(self):
        tab = self._tabview.add("Health Statistics")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._hs_district = LabeledDropdown(controls, label="District", values=["All"] + district_names,
                                            command=self._on_hs_district_change)
        self._hs_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._hs_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._hs_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._hs_year = LabeledDropdown(controls, label="Year", values=YEAR_OPTIONS)
        self._hs_year.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(btn_frame, text="Filter", command=self._filter_health_stats,
                      font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(btn_frame, text="+ Add", command=self._add_health_dialog,
                          font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                          text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        self._hs_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                      text_color=TEXT_SECONDARY)
        self._hs_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "year", "title": "Year", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "dengue_cases", "title": "Dengue", "width": 1},
            {"key": "tuberculosis_cases", "title": "TB", "width": 1},
            {"key": "covid_cases", "title": "COVID", "width": 1},
            {"key": "vaccination_coverage_pct", "title": "Vaccination %", "width": 1},
            {"key": "malnutrition_rate", "title": "Malnutrition %", "width": 1},
        ]
        self._hs_table = DataTable(tab, columns=columns, on_row_click=self._on_health_row_click)
        self._hs_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_hs_district_change(self, district_name: str):
        if district_name == "All":
            self._hs_barangay.set_values(["All"])
            self._hs_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._hs_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._hs_barangay.set("All")

    def _filter_health_stats(self):
        district = self._hs_district.get()
        brgy_name = self._hs_barangay.get()
        year_str = self._hs_year.get()

        district_id = None
        if district != "All":
            district_id = self._district_map.get(district)

        barangay_id = None
        if brgy_name != "All" and district != "All":
            brgy_map = self._load_barangays(district)
            barangay_id = brgy_map.get(brgy_name)

        if year_str == "All":
            # Gather all years and merge results
            all_data = []
            seen_years = set()
            for yr in [2025, 2024, 2023, 2022, 2021]:
                rows = get_health_stats_by_year(yr, district_id=district_id)
                for row in rows:
                    key = (row["barangay_id"], yr)
                    if key not in seen_years:
                        seen_years.add(key)
                        row["year"] = yr
                        all_data.append(row)
            data = all_data
        else:
            year = int(year_str)
            data = get_health_stats_by_year(year, district_id=district_id)
            for row in data:
                row["year"] = year

        # Filter by specific barangay if selected
        if barangay_id:
            data = [r for r in data if r.get("barangay_id") == barangay_id]

        self._hs_table.set_data(data)
        self._hs_count.configure(text=f"Showing {len(data)} record(s)")

    def _add_health_dialog(self):
        self._health_stats_dialog()

    def _on_health_row_click(self, row_data):
        self._health_stats_dialog(row_data)

    def _health_stats_dialog(self, existing: dict | None = None):
        is_edit = existing is not None
        title = "Edit Health Statistics" if is_edit else "Add Health Statistics"

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("500x580")
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
            names = list(brgy_map.keys())
            d_barangay.set_values(names)
            if names:
                d_barangay.set(names[0])

        d_district._dropdown.configure(command=on_district_sel)
        if district_names:
            on_district_sel(district_names[0])

        # Year
        d_year = LabeledNumberEntry(scroll, label="Year *", placeholder=str(CURRENT_YEAR))
        d_year.set(str(CURRENT_YEAR))
        d_year.pack(fill="x", pady=2)

        # Disease counts
        d_dengue = LabeledNumberEntry(scroll, label="Dengue Cases", placeholder="0")
        d_dengue.pack(fill="x", pady=2)

        d_tb = LabeledNumberEntry(scroll, label="Tuberculosis Cases", placeholder="0")
        d_tb.pack(fill="x", pady=2)

        d_covid = LabeledNumberEntry(scroll, label="COVID Cases", placeholder="0")
        d_covid.pack(fill="x", pady=2)

        d_diarrhea = LabeledNumberEntry(scroll, label="Diarrhea Cases", placeholder="0")
        d_diarrhea.pack(fill="x", pady=2)

        d_pneumonia = LabeledNumberEntry(scroll, label="Pneumonia Cases", placeholder="0")
        d_pneumonia.pack(fill="x", pady=2)

        d_hypertension = LabeledNumberEntry(scroll, label="Hypertension Cases", placeholder="0")
        d_hypertension.pack(fill="x", pady=2)

        d_diabetes = LabeledNumberEntry(scroll, label="Diabetes Cases", placeholder="0")
        d_diabetes.pack(fill="x", pady=2)

        d_other = LabeledNumberEntry(scroll, label="Other Disease Cases", placeholder="0")
        d_other.pack(fill="x", pady=2)

        # Percentages
        d_vax = LabeledEntry(scroll, label="Vaccination Coverage (%)", placeholder="0.0")
        d_vax.pack(fill="x", pady=2)

        d_malnutrition = LabeledEntry(scroll, label="Malnutrition Rate (%)", placeholder="0.0")
        d_malnutrition.pack(fill="x", pady=2)

        # Health facilities
        d_hospitals = LabeledNumberEntry(scroll, label="Hospital Count", placeholder="0")
        d_hospitals.pack(fill="x", pady=2)

        d_clinics = LabeledNumberEntry(scroll, label="Clinic Count", placeholder="0")
        d_clinics.pack(fill="x", pady=2)

        d_health_workers = LabeledNumberEntry(scroll, label="Health Worker Count", placeholder="0")
        d_health_workers.pack(fill="x", pady=2)

        # Mortality
        d_maternal = LabeledNumberEntry(scroll, label="Maternal Mortality", placeholder="0")
        d_maternal.pack(fill="x", pady=2)

        d_infant = LabeledNumberEntry(scroll, label="Infant Mortality", placeholder="0")
        d_infant.pack(fill="x", pady=2)

        # Pre-fill for edit
        if is_edit:
            edit_district = existing.get("district_name", "")
            edit_barangay = existing.get("barangay_name", "")
            if edit_district and edit_district in district_names:
                d_district.set(edit_district)
                on_district_sel(edit_district)
                if edit_barangay:
                    d_barangay.set(edit_barangay)
            elif edit_barangay:
                # Try to find the district by loading barangay data
                for dn in district_names:
                    brgy_map = self._load_barangays(dn)
                    if edit_barangay in brgy_map:
                        d_district.set(dn)
                        on_district_sel(dn)
                        d_barangay.set(edit_barangay)
                        break

            d_year.set(str(existing.get("year", CURRENT_YEAR)))
            d_dengue.set(str(existing.get("dengue_cases", 0) or 0))
            d_tb.set(str(existing.get("tuberculosis_cases", 0) or 0))
            d_covid.set(str(existing.get("covid_cases", 0) or 0))
            d_diarrhea.set(str(existing.get("diarrhea_cases", 0) or 0))
            d_pneumonia.set(str(existing.get("pneumonia_cases", 0) or 0))
            d_hypertension.set(str(existing.get("hypertension_cases", 0) or 0))
            d_diabetes.set(str(existing.get("diabetes_cases", 0) or 0))
            d_other.set(str(existing.get("other_disease_cases", 0) or 0))
            d_vax.set(str(existing.get("vaccination_coverage_pct", "") or ""))
            d_malnutrition.set(str(existing.get("malnutrition_rate", "") or ""))
            d_hospitals.set(str(existing.get("hospital_count", 0) or 0))
            d_clinics.set(str(existing.get("clinic_count", 0) or 0))
            d_health_workers.set(str(existing.get("health_worker_count", 0) or 0))
            d_maternal.set(str(existing.get("maternal_mortality", 0) or 0))
            d_infant.set(str(existing.get("infant_mortality", 0) or 0))

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

            year_val = d_year.get_int()
            if not year_val or year_val < 2000 or year_val > 2100:
                error_label.configure(text="Please enter a valid year (2000-2100).")
                return

            try:
                vax = float(d_vax.get()) if d_vax.get() else None
            except ValueError:
                error_label.configure(text="Vaccination coverage must be a number.")
                return

            try:
                malnutrition = float(d_malnutrition.get()) if d_malnutrition.get() else None
            except ValueError:
                error_label.configure(text="Malnutrition rate must be a number.")
                return

            data = {
                "dengue_cases": d_dengue.get_int(0),
                "tuberculosis_cases": d_tb.get_int(0),
                "covid_cases": d_covid.get_int(0),
                "diarrhea_cases": d_diarrhea.get_int(0),
                "pneumonia_cases": d_pneumonia.get_int(0),
                "hypertension_cases": d_hypertension.get_int(0),
                "diabetes_cases": d_diabetes.get_int(0),
                "other_disease_cases": d_other.get_int(0),
                "vaccination_coverage_pct": vax,
                "malnutrition_rate": malnutrition,
                "hospital_count": d_hospitals.get_int(0),
                "clinic_count": d_clinics.get_int(0),
                "health_worker_count": d_health_workers.get_int(0),
                "maternal_mortality": d_maternal.get_int(0),
                "infant_mortality": d_infant.get_int(0),
            }

            success, msg = save_health_statistics(brgy_id, year_val, data, self._get_user_id())
            if success:
                dialog.destroy()
                self._filter_health_stats()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(btn_frame, text="Save", command=do_save,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=COLORS["grey"],
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    # ── Tab 2: Social Welfare ─────────────────────────────────

    def _build_social_welfare_tab(self):
        tab = self._tabview.add("Social Welfare")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._sw_district = LabeledDropdown(controls, label="District", values=["All"] + district_names,
                                            command=self._on_sw_district_change)
        self._sw_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._sw_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._sw_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._sw_year = LabeledDropdown(controls, label="Year", values=YEAR_OPTIONS)
        self._sw_year.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(btn_frame, text="Filter", command=self._filter_welfare,
                      font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(btn_frame, text="+ Add", command=self._add_welfare_dialog,
                          font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                          text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        self._sw_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                      text_color=TEXT_SECONDARY)
        self._sw_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "year", "title": "Year", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "fourps_beneficiaries", "title": "4Ps Beneficiaries", "width": 2},
            {"key": "senior_citizen_count", "title": "Senior Citizens", "width": 1},
            {"key": "pwd_count", "title": "PWD", "width": 1},
            {"key": "solo_parent_count", "title": "Solo Parents", "width": 1},
            {"key": "indigent_families", "title": "Indigent Families", "width": 1},
        ]
        self._sw_table = DataTable(tab, columns=columns, on_row_click=self._on_welfare_row_click)
        self._sw_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_sw_district_change(self, district_name: str):
        if district_name == "All":
            self._sw_barangay.set_values(["All"])
            self._sw_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._sw_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._sw_barangay.set("All")

    def _filter_welfare(self):
        district = self._sw_district.get()
        brgy_name = self._sw_barangay.get()
        year_str = self._sw_year.get()

        district_id = None
        if district != "All":
            district_id = self._district_map.get(district)

        barangay_id = None
        if brgy_name != "All" and district != "All":
            brgy_map = self._load_barangays(district)
            barangay_id = brgy_map.get(brgy_name)

        if year_str == "All":
            all_data = []
            seen = set()
            for yr in [2025, 2024, 2023, 2022, 2021]:
                rows = get_welfare_stats_by_year(yr, district_id=district_id)
                for row in rows:
                    key = (row["barangay_id"], yr)
                    if key not in seen:
                        seen.add(key)
                        row["year"] = yr
                        all_data.append(row)
            data = all_data
        else:
            year = int(year_str)
            data = get_welfare_stats_by_year(year, district_id=district_id)
            for row in data:
                row["year"] = year

        if barangay_id:
            data = [r for r in data if r.get("barangay_id") == barangay_id]

        self._sw_table.set_data(data)
        self._sw_count.configure(text=f"Showing {len(data)} record(s)")

    def _add_welfare_dialog(self):
        self._social_welfare_dialog()

    def _on_welfare_row_click(self, row_data):
        self._social_welfare_dialog(row_data)

    def _social_welfare_dialog(self, existing: dict | None = None):
        is_edit = existing is not None
        title = "Edit Social Welfare Data" if is_edit else "Add Social Welfare Data"

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("480x480")
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
            names = list(brgy_map.keys())
            d_barangay.set_values(names)
            if names:
                d_barangay.set(names[0])

        d_district._dropdown.configure(command=on_district_sel)
        if district_names:
            on_district_sel(district_names[0])

        # Year
        d_year = LabeledNumberEntry(scroll, label="Year *", placeholder=str(CURRENT_YEAR))
        d_year.set(str(CURRENT_YEAR))
        d_year.pack(fill="x", pady=2)

        # Welfare fields
        d_fourps = LabeledNumberEntry(scroll, label="4Ps Beneficiaries", placeholder="0")
        d_fourps.pack(fill="x", pady=2)

        d_seniors = LabeledNumberEntry(scroll, label="Senior Citizen Count", placeholder="0")
        d_seniors.pack(fill="x", pady=2)

        d_pwd = LabeledNumberEntry(scroll, label="PWD Count", placeholder="0")
        d_pwd.pack(fill="x", pady=2)

        d_solo = LabeledNumberEntry(scroll, label="Solo Parent Count", placeholder="0")
        d_solo.pack(fill="x", pady=2)

        d_indigent = LabeledNumberEntry(scroll, label="Indigent Families", placeholder="0")
        d_indigent.pack(fill="x", pady=2)

        d_nutrition = LabeledNumberEntry(scroll, label="Nutrition Program Beneficiaries", placeholder="0")
        d_nutrition.pack(fill="x", pady=2)

        # Pre-fill for edit
        if is_edit:
            edit_district = existing.get("district_name", "")
            edit_barangay = existing.get("barangay_name", "")
            if edit_district and edit_district in district_names:
                d_district.set(edit_district)
                on_district_sel(edit_district)
                if edit_barangay:
                    d_barangay.set(edit_barangay)
            elif edit_barangay:
                for dn in district_names:
                    brgy_map = self._load_barangays(dn)
                    if edit_barangay in brgy_map:
                        d_district.set(dn)
                        on_district_sel(dn)
                        d_barangay.set(edit_barangay)
                        break

            d_year.set(str(existing.get("year", CURRENT_YEAR)))
            d_fourps.set(str(existing.get("fourps_beneficiaries", 0) or 0))
            d_seniors.set(str(existing.get("senior_citizen_count", 0) or 0))
            d_pwd.set(str(existing.get("pwd_count", 0) or 0))
            d_solo.set(str(existing.get("solo_parent_count", 0) or 0))
            d_indigent.set(str(existing.get("indigent_families", 0) or 0))
            d_nutrition.set(str(existing.get("nutrition_program_beneficiaries", 0) or 0))

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

            year_val = d_year.get_int()
            if not year_val or year_val < 2000 or year_val > 2100:
                error_label.configure(text="Please enter a valid year (2000-2100).")
                return

            data = {
                "fourps_beneficiaries": d_fourps.get_int(0),
                "senior_citizen_count": d_seniors.get_int(0),
                "pwd_count": d_pwd.get_int(0),
                "solo_parent_count": d_solo.get_int(0),
                "indigent_families": d_indigent.get_int(0),
                "nutrition_program_beneficiaries": d_nutrition.get_int(0),
            }

            success, msg = save_social_welfare_data(brgy_id, year_val, data, self._get_user_id())
            if success:
                dialog.destroy()
                self._filter_welfare()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(btn_frame, text="Save", command=do_save,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=COLORS["grey"],
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    # ── Tab 3: Health Overview ────────────────────────────────

    def _build_health_overview_tab(self):
        tab = self._tabview.add("Health Overview")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._ho_scope = LabeledDropdown(controls, label="Scope",
                                         values=["City-Wide", "By District", "By Barangay"])
        self._ho_scope.pack(side="left", padx=(0, 8), fill="x", expand=True)

        district_names = [d["name"] for d in self._districts]
        self._ho_district = LabeledDropdown(controls, label="District", values=district_names,
                                            command=self._on_ho_district_change)
        self._ho_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._ho_barangay = LabeledDropdown(controls, label="Barangay", values=[])
        self._ho_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkButton(controls, text="Update", command=self._update_health_overview,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", pady=(18, 0))

        self._ho_chart = ChartWidget(tab, figsize=(9, 5))
        self._ho_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _on_ho_district_change(self, dn):
        brgy_map = self._load_barangays(dn)
        names = list(brgy_map.keys())
        self._ho_barangay.set_values(names)
        if names:
            self._ho_barangay.set(names[0])

    def _update_health_overview(self):
        scope = self._ho_scope.get()
        barangay_id = None
        district_id = None

        if scope == "By District":
            district_id = self._district_map.get(self._ho_district.get())
        elif scope == "By Barangay":
            dn = self._ho_district.get()
            brgy_map = self._load_barangays(dn)
            barangay_id = brgy_map.get(self._ho_barangay.get())

        summary = get_health_summary(barangay_id=barangay_id, district_id=district_id)
        trend = get_disease_trend(barangay_id=barangay_id, district_id=district_id)

        # Gather latest year data per district for overview charts
        year_data = get_health_stats_by_year(CURRENT_YEAR, district_id=district_id)
        if not year_data and not trend:
            year_data = get_health_stats_by_year(CURRENT_YEAR - 1, district_id=district_id)

        if not year_data and not trend and summary["total_disease_cases"] == 0:
            self._ho_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No health data available for this selection.",
                ha="center", va="center", fontsize=12, color="#999999", transform=ax.transAxes))
            return

        def draw(fig):
            # Top-left: Disease breakdown (horizontal bars)
            ax1 = fig.add_subplot(221)
            if trend:
                last = trend[-1]
                diseases = {
                    "Dengue": last["dengue"],
                    "Tuberculosis": last["tb"],
                    "COVID": last["covid"],
                    "Diarrhea": last["diarrhea"],
                    "Pneumonia": last["pneumonia"],
                }
                diseases = {k: v for k, v in diseases.items() if v > 0}
                if diseases:
                    labels = list(diseases.keys())
                    vals = list(diseases.values())
                    bar_colors = [COLORS["red"], COLORS["orange"], COLORS["blue"],
                                  COLORS["green"], COLORS["purple"]][:len(labels)]
                    bars = ax1.barh(labels, vals, color=bar_colors)
                    ax1.set_title(f"Disease Breakdown ({last['year']})", fontsize=10)
                    ax1.set_xlabel("Cases")
                    for bar, val in zip(bars, vals):
                        ax1.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                                 str(val), va="center", fontsize=7)
                else:
                    ax1.text(0.5, 0.5, "No disease data", ha="center", va="center",
                             fontsize=9, color="#999999", transform=ax1.transAxes)
                    ax1.set_title("Disease Breakdown", fontsize=10)
            else:
                ax1.text(0.5, 0.5, "No trend data", ha="center", va="center",
                         fontsize=9, color="#999999", transform=ax1.transAxes)
                ax1.set_title("Disease Breakdown", fontsize=10)

            # Top-right: Vaccination coverage
            ax2 = fig.add_subplot(222)
            if year_data:
                brgy_labels = [r["barangay_name"][:10] for r in year_data[:10]]
                vax_vals = [r["vaccination_coverage_pct"] for r in year_data[:10]]
                ax2.bar(brgy_labels, vax_vals, color=COLORS["teal"])
                ax2.set_title("Vaccination Coverage (%)", fontsize=10)
                ax2.set_ylabel("%")
                ax2.set_ylim(0, 100)
                ax2.tick_params(axis="x", rotation=45, labelsize=6)
            else:
                ax2.text(0.5, 0.5, "No data available", ha="center", va="center",
                         fontsize=9, color="#999999", transform=ax2.transAxes)
                ax2.set_title("Vaccination Coverage (%)", fontsize=10)

            # Bottom-left: Malnutrition rate
            ax3 = fig.add_subplot(223)
            if year_data:
                mal_data = sorted(year_data, key=lambda r: r["malnutrition_rate"], reverse=True)[:10]
                brgy_labels = [r["barangay_name"][:10] for r in mal_data]
                mal_vals = [r["malnutrition_rate"] for r in mal_data]
                ax3.bar(brgy_labels, mal_vals, color=COLORS["orange"])
                ax3.set_title("Malnutrition Rate (%) - Top 10", fontsize=10)
                ax3.set_ylabel("%")
                ax3.tick_params(axis="x", rotation=45, labelsize=6)
            else:
                ax3.text(0.5, 0.5, "No data available", ha="center", va="center",
                         fontsize=9, color="#999999", transform=ax3.transAxes)
                ax3.set_title("Malnutrition Rate (%)", fontsize=10)

            # Bottom-right: Maternal + Infant mortality grouped bar
            ax4 = fig.add_subplot(224)
            if year_data:
                mort_data = [r for r in year_data if r["maternal_mortality"] > 0 or r["infant_mortality"] > 0]
                mort_data = mort_data[:8]
                if mort_data:
                    import numpy as np
                    x = np.arange(len(mort_data))
                    width = 0.35
                    maternal_vals = [r["maternal_mortality"] for r in mort_data]
                    infant_vals = [r["infant_mortality"] for r in mort_data]
                    brgy_labels = [r["barangay_name"][:8] for r in mort_data]
                    ax4.bar(x - width / 2, maternal_vals, width, label="Maternal", color=COLORS["pink"])
                    ax4.bar(x + width / 2, infant_vals, width, label="Infant", color=COLORS["purple"])
                    ax4.set_title("Mortality Summary", fontsize=10)
                    ax4.set_ylabel("Count")
                    ax4.set_xticks(x)
                    ax4.set_xticklabels(brgy_labels, rotation=45, fontsize=6)
                    ax4.legend(fontsize=7)
                else:
                    ax4.text(0.5, 0.5, "No mortality data", ha="center", va="center",
                             fontsize=9, color="#999999", transform=ax4.transAxes)
                    ax4.set_title("Mortality Summary", fontsize=10)
            else:
                ax4.text(0.5, 0.5, "No data available", ha="center", va="center",
                         fontsize=9, color="#999999", transform=ax4.transAxes)
                ax4.set_title("Mortality Summary", fontsize=10)

            fig.subplots_adjust(hspace=0.5, wspace=0.4, top=0.92, bottom=0.12, left=0.1, right=0.97)

        self._ho_chart.update_chart_multi(draw)

    # ── Tab 4: High Risk Areas ────────────────────────────────

    def _build_high_risk_tab(self):
        tab = self._tabview.add("High-Risk Areas")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._hr_year = LabeledDropdown(controls, label="Year",
                                        values=[str(y) for y in [2025, 2024, 2023, 2022, 2021]])
        self._hr_year.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(controls, text="Refresh", command=self._update_high_risk,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", pady=(18, 0))

        self._hr_info = ctk.CTkLabel(
            tab, text="Barangays ranked by composite health risk (malnutrition + total disease cases)",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._hr_info.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 3))

        columns = [
            {"key": "rank", "title": "#", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 3},
            {"key": "dengue_cases", "title": "Dengue", "width": 1},
            {"key": "tuberculosis_cases", "title": "TB", "width": 1},
            {"key": "covid_cases", "title": "COVID", "width": 1},
            {"key": "total_disease_cases", "title": "Total Cases", "width": 1},
            {"key": "malnutrition_rate", "title": "Malnutrition %", "width": 1},
            {"key": "risk_score", "title": "Risk Score", "width": 1},
        ]
        self._hr_table = DataTable(tab, columns=columns)
        self._hr_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _update_high_risk(self):
        year_str = self._hr_year.get()
        year = int(year_str)
        raw = get_health_stats_by_year(year)

        if not raw:
            self._hr_table.set_data([])
            self._hr_info.configure(text=f"No data available for {year}.")
            return

        # Compute composite risk score: normalized disease cases + malnutrition rate
        max_diseases = max(
            (r["dengue_cases"] + r["tuberculosis_cases"] + r["covid_cases"])
            for r in raw
        ) or 1
        max_malnutrition = max(r["malnutrition_rate"] for r in raw) or 1

        ranked = []
        for r in raw:
            total = r["dengue_cases"] + r["tuberculosis_cases"] + r["covid_cases"]
            disease_score = (total / max_diseases) * 50
            malnutrition_score = (r["malnutrition_rate"] / max_malnutrition) * 50
            risk_score = round(disease_score + malnutrition_score, 1)
            ranked.append({
                **r,
                "total_disease_cases": total,
                "risk_score": risk_score,
            })

        ranked.sort(key=lambda r: r["risk_score"], reverse=True)
        for i, r in enumerate(ranked, start=1):
            r["rank"] = i

        self._hr_table.set_data(ranked)
        self._hr_info.configure(
            text=f"Top {len(ranked)} barangays ranked by composite health risk for {year}"
        )

    def refresh(self):
        pass
