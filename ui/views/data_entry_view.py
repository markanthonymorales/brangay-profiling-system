import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.form_fields import LabeledEntry, LabeledNumberEntry, LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from ui.dialogs.confirm_dialog import ConfirmDialog
from auth.auth_manager import AuthManager
from services.barangay_service import get_all_barangays, get_all_districts, get_barangays_by_district
from services.population_service import save_population_record
from services.resident_service import save_resident_category
from services.economic_service import save_income_record, save_business
from services.infrastructure_service import save_utility_record, save_waste_record, save_land_type
from services.community_service import save_food_source, save_government_facility, save_religious_demographic
from services.health_service import save_health_statistics
from services.social_welfare_service import save_social_welfare_data
from services.disaster_service import save_disaster_risk_profile
from services.education_service import save_education_statistics
from utils.validators import validate_required, validate_positive_int, validate_percentage, validate_year, parse_int, parse_float
from datetime import datetime


class DataEntryView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._selected_barangay_id = None
        self._build_ui()

    def _build_ui(self):
        # Permission check
        if not self._auth.check_permission("enter_data"):
            ctk.CTkLabel(
                self, text="Data Entry",
                font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))
            ctk.CTkLabel(
                self, text="You do not have permission to enter data. Contact an administrator.",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=DANGER_COLOR,
            ).pack(padx=PADDING_LARGE, pady=PADDING_LARGE)
            return

        # Title
        ctk.CTkLabel(
            self, text="Data Entry",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Selection row
        select_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        select_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        inner = ctk.CTkFrame(select_frame, fg_color="transparent")
        inner.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        # District selector
        districts = get_all_districts()
        district_names = [d["name"] for d in districts]
        self._district_map = {d["name"]: d["id"] for d in districts}

        self._district_dropdown = LabeledDropdown(
            inner, label="District", values=district_names,
            required=True, command=self._on_district_change,
        )
        self._district_dropdown.pack(side="left", padx=(0, 15), fill="x", expand=True)

        # Barangay selector
        self._barangay_dropdown = LabeledDropdown(
            inner, label="Barangay", values=[], required=True,
            command=self._on_barangay_change,
        )
        self._barangay_dropdown.pack(side="left", padx=(0, 15), fill="x", expand=True)

        # Year
        current_year = str(datetime.now().year)
        self._year_entry = LabeledEntry(inner, label="Year", placeholder=current_year, required=True)
        self._year_entry.set(current_year)
        self._year_entry.pack(side="left", fill="x", expand=True)

        # Barangay data maps
        self._barangay_map = {}

        # Tab view for data categories
        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12,
                                        command=self._on_tab_change)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._built_tabs = set()

        self._tabview.add("Population")
        self._tabview.add("Residents")
        self._tabview.add("Economic")
        self._tabview.add("Infrastructure")
        self._tabview.add("Community")
        self._tabview.add("Health")
        self._tabview.add("Social Welfare")
        self._tabview.add("Disaster Risk")
        self._tabview.add("Education")

        self._build_population_tab()
        self._built_tabs.add("Population")

    def _on_tab_change(self):
        current = self._tabview.get()
        if current in self._built_tabs:
            return
        self._built_tabs.add(current)
        if current == "Residents":
            self._build_residents_tab()
        elif current == "Economic":
            self._build_economic_tab()
        elif current == "Infrastructure":
            self._build_infrastructure_tab()
        elif current == "Community":
            self._build_community_tab()
        elif current == "Health":
            self._build_health_tab()
        elif current == "Social Welfare":
            self._build_social_welfare_tab()
        elif current == "Disaster Risk":
            self._build_disaster_risk_tab()
        elif current == "Education":
            self._build_education_tab()

        # Trigger initial load
        if district_names:
            self._on_district_change(district_names[0])

    def _on_district_change(self, district_name: str):
        district_id = self._district_map.get(district_name)
        if district_id is None:
            return
        barangays = get_barangays_by_district(district_id)
        self._barangay_map = {b["name"]: b["id"] for b in barangays}
        names = list(self._barangay_map.keys())
        self._barangay_dropdown.set_values(names)
        if names:
            self._barangay_dropdown.set(names[0])
            self._on_barangay_change(names[0])

    def _on_barangay_change(self, barangay_name: str):
        self._selected_barangay_id = self._barangay_map.get(barangay_name)

    def _get_user_id(self) -> int:
        user = self._auth.get_current_user()
        return user.id if user else 0

    def _get_year(self) -> int | None:
        valid, msg = validate_year(self._year_entry.get())
        if not valid:
            MessageDialog(self, title="Validation Error", message=msg, dialog_type="error")
            return None
        return int(self._year_entry.get())

    # ── Population Tab ────────────────────────────────────────

    def _build_population_tab(self):
        tab = self._tabview.tab("Population")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        fields_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        fields_frame.pack(fill="x")

        self._pop_fields = {}
        field_defs = [
            ("total_population", "Total Population"),
            ("male_count", "Male Count"),
            ("female_count", "Female Count"),
            ("registered_voters", "Registered Voters"),
            ("non_registered_residents", "Non-Registered Residents"),
            ("foreign_residents", "Foreign Residents"),
            ("household_count", "Household Count"),
        ]

        for i, (key, label) in enumerate(field_defs):
            field = LabeledNumberEntry(fields_frame, label=label, placeholder="0")
            row, col = divmod(i, 3)
            field.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            fields_frame.columnconfigure(col, weight=1)
            self._pop_fields[key] = field

        ctk.CTkButton(
            scroll, text="Save Population Data", command=self._save_population,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_LARGE, 0))

    def _save_population(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        errors = []
        for key, field in self._pop_fields.items():
            valid, msg = validate_positive_int(field.get(), key)
            if not valid:
                errors.append(msg)
                field.set_error(msg)
            else:
                field.clear_error()

        if errors:
            return

        data = {key: field.get_int() for key, field in self._pop_fields.items()}
        success, msg = save_population_record(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Population Data", message=msg, dialog_type=dialog_type)

    # ── Residents Tab ─────────────────────────────────────────

    def _build_residents_tab(self):
        tab = self._tabview.tab("Residents")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        fields_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        fields_frame.pack(fill="x")

        self._res_fields = {}
        field_defs = [
            ("renters_count", "Renters"),
            ("homeowners_count", "Homeowners"),
            ("squatters_count", "Squatters"),
            ("informal_settlers_count", "Informal Settlers"),
        ]

        for i, (key, label) in enumerate(field_defs):
            field = LabeledNumberEntry(fields_frame, label=label, placeholder="0")
            row, col = divmod(i, 2)
            field.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            fields_frame.columnconfigure(col, weight=1)
            self._res_fields[key] = field

        ctk.CTkButton(
            scroll, text="Save Resident Data", command=self._save_residents,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_LARGE, 0))

    def _save_residents(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        data = {key: field.get_int() for key, field in self._res_fields.items()}
        success, msg = save_resident_category(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Resident Data", message=msg, dialog_type=dialog_type)

    # ── Economic Tab ──────────────────────────────────────────

    def _build_economic_tab(self):
        tab = self._tabview.tab("Economic")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        ctk.CTkLabel(scroll, text="Income Data", font=(FONT_FAMILY, 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))

        fields_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        fields_frame.pack(fill="x")

        self._income_fields = {}
        field_defs = [
            ("average_household_income", "Avg Household Income (PHP)"),
            ("below_poverty_count", "Below Poverty Line"),
            ("low_income_count", "Low Income"),
            ("middle_income_count", "Middle Income"),
            ("high_income_count", "High Income"),
        ]

        for i, (key, label) in enumerate(field_defs):
            field = LabeledNumberEntry(fields_frame, label=label, placeholder="0")
            row, col = divmod(i, 3)
            field.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            fields_frame.columnconfigure(col, weight=1)
            self._income_fields[key] = field

        ctk.CTkButton(
            scroll, text="Save Income Data", command=self._save_income,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_LARGE, PADDING_LARGE))

        # Business entry
        ctk.CTkLabel(scroll, text="Add Business", font=(FONT_FAMILY, 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))

        biz_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        biz_frame.pack(fill="x")
        biz_frame.columnconfigure(0, weight=2)
        biz_frame.columnconfigure(1, weight=1)
        biz_frame.columnconfigure(2, weight=1)

        self._biz_name = LabeledEntry(biz_frame, label="Business Name", required=True)
        self._biz_name.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self._biz_type = LabeledDropdown(
            biz_frame, label="Type",
            values=["retail", "food", "services", "manufacturing", "agriculture", "other"],
        )
        self._biz_type.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self._biz_date = LabeledEntry(biz_frame, label="Registered Date (YYYY-MM-DD)",
                                      placeholder=datetime.now().strftime("%Y-%m-%d"))
        self._biz_date.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(
            scroll, text="Save Business", command=self._save_business,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(5, 0))

    def _save_business(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        name = self._biz_name.get()
        if not name:
            MessageDialog(self, title="Error", message="Business name is required.", dialog_type="error")
            return

        from datetime import date
        date_val = None
        date_str = self._biz_date.get()
        if date_str:
            try:
                date_val = date.fromisoformat(date_str)
            except ValueError:
                MessageDialog(self, title="Error", message="Invalid date format. Use YYYY-MM-DD.", dialog_type="error")
                return

        data = {
            "name": name,
            "type": self._biz_type.get(),
            "is_active": True,
            "registered_date": date_val,
        }
        success, msg = save_business(self._selected_barangay_id, data, self._get_user_id())
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Business", message=msg, dialog_type=dialog_type)
        if success:
            self._biz_name.clear()
            self._biz_date.clear()

    def _save_income(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        data = {}
        for key, field in self._income_fields.items():
            if key == "average_household_income":
                data[key] = field.get_float()
            else:
                data[key] = field.get_int()

        success, msg = save_income_record(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Income Data", message=msg, dialog_type=dialog_type)

    # ── Infrastructure Tab ────────────────────────────────────

    def _build_infrastructure_tab(self):
        tab = self._tabview.tab("Infrastructure")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        ctk.CTkLabel(scroll, text="Utilities", font=(FONT_FAMILY, 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))

        util_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        util_frame.pack(fill="x")

        self._util_fields = {}
        util_defs = [
            ("water_source", "Water Source", "entry"),
            ("water_coverage_pct", "Water Coverage %", "number"),
            ("power_provider", "Power Provider", "entry"),
            ("power_coverage_pct", "Power Coverage %", "number"),
            ("internet_coverage_pct", "Internet Coverage %", "number"),
        ]

        for i, (key, label, ftype) in enumerate(util_defs):
            if ftype == "number":
                field = LabeledNumberEntry(util_frame, label=label, placeholder="0-100")
            else:
                field = LabeledEntry(util_frame, label=label)
            row, col = divmod(i, 3)
            field.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            util_frame.columnconfigure(col, weight=1)
            self._util_fields[key] = field

        ctk.CTkButton(
            scroll, text="Save Utility Data", command=self._save_utility,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_NORMAL, PADDING_LARGE))

        # Waste management
        ctk.CTkLabel(scroll, text="Waste Management", font=(FONT_FAMILY, 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))

        waste_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        waste_frame.pack(fill="x")

        self._waste_fields = {}
        self._waste_fields["collection_frequency"] = LabeledDropdown(
            waste_frame, label="Collection Frequency",
            values=["daily", "weekly", "bi-weekly", "monthly"],
        )
        self._waste_fields["collection_frequency"].grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self._waste_fields["disposal_method"] = LabeledDropdown(
            waste_frame, label="Disposal Method",
            values=["landfill", "recycling", "composting", "incineration", "mixed"],
        )
        self._waste_fields["disposal_method"].grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self._waste_fields["coverage_pct"] = LabeledNumberEntry(
            waste_frame, label="Coverage %", placeholder="0-100",
        )
        self._waste_fields["coverage_pct"].grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        waste_frame.columnconfigure(0, weight=1)
        waste_frame.columnconfigure(1, weight=1)
        waste_frame.columnconfigure(2, weight=1)

        ctk.CTkButton(
            scroll, text="Save Waste Data", command=self._save_waste,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_NORMAL, 0))

    def _save_utility(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        # Validate percentages
        for key in ("water_coverage_pct", "power_coverage_pct", "internet_coverage_pct"):
            field = self._util_fields[key]
            valid, msg = validate_percentage(field.get(), key)
            if not valid:
                MessageDialog(self, title="Validation Error", message=msg, dialog_type="error")
                return

        data = {
            "water_source": self._util_fields["water_source"].get() or None,
            "water_coverage_pct": parse_float(self._util_fields["water_coverage_pct"].get()),
            "power_provider": self._util_fields["power_provider"].get() or None,
            "power_coverage_pct": parse_float(self._util_fields["power_coverage_pct"].get()),
            "internet_coverage_pct": parse_float(self._util_fields["internet_coverage_pct"].get()),
        }

        success, msg = save_utility_record(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Utility Data", message=msg, dialog_type=dialog_type)

    def _save_waste(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        data = {
            "collection_frequency": self._waste_fields["collection_frequency"].get(),
            "disposal_method": self._waste_fields["disposal_method"].get(),
            "coverage_pct": parse_float(self._waste_fields["coverage_pct"].get()),
        }

        success, msg = save_waste_record(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Waste Management", message=msg, dialog_type=dialog_type)

    # ── Community Tab ─────────────────────────────────────────

    def _build_community_tab(self):
        tab = self._tabview.tab("Community")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        # Food source
        ctk.CTkLabel(scroll, text="Add Food Source", font=(FONT_FAMILY, 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))

        food_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        food_frame.pack(fill="x")
        food_frame.columnconfigure(0, weight=1)
        food_frame.columnconfigure(1, weight=2)

        self._food_type = LabeledDropdown(
            food_frame, label="Type",
            values=["market", "farm", "fishing", "imported"],
        )
        self._food_type.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self._food_desc = LabeledEntry(food_frame, label="Description")
        self._food_desc.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(
            scroll, text="Save Food Source", command=self._save_food,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(5, PADDING_LARGE))

        # Government facility
        ctk.CTkLabel(scroll, text="Add Government Facility", font=(FONT_FAMILY, 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))

        fac_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        fac_frame.pack(fill="x")
        fac_frame.columnconfigure(0, weight=1)
        fac_frame.columnconfigure(1, weight=1)
        fac_frame.columnconfigure(2, weight=2)

        self._fac_agency = LabeledEntry(fac_frame, label="Agency Name", required=True)
        self._fac_agency.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self._fac_type = LabeledDropdown(
            fac_frame, label="Facility Type",
            values=["police station", "fire station", "health center", "school",
                    "barangay hall", "court", "post office", "other"],
        )
        self._fac_type.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self._fac_address = LabeledEntry(fac_frame, label="Address")
        self._fac_address.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(
            scroll, text="Save Facility", command=self._save_facility,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(5, PADDING_LARGE))

        # Religious demographic
        ctk.CTkLabel(scroll, text="Add Religious Demographic", font=(FONT_FAMILY, 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 5))

        rel_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        rel_frame.pack(fill="x")
        rel_frame.columnconfigure(0, weight=1)
        rel_frame.columnconfigure(1, weight=1)
        rel_frame.columnconfigure(2, weight=1)

        self._rel_religion = LabeledEntry(rel_frame, label="Religion", required=True)
        self._rel_religion.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self._rel_count = LabeledNumberEntry(rel_frame, label="Count")
        self._rel_count.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self._rel_pct = LabeledNumberEntry(rel_frame, label="Percentage %")
        self._rel_pct.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(
            scroll, text="Save Religious Data", command=self._save_religion,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(5, 0))

    def _save_food(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return

        data = {
            "type": self._food_type.get(),
            "description": self._food_desc.get() or None,
        }
        success, msg = save_food_source(self._selected_barangay_id, data, self._get_user_id())
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Food Source", message=msg, dialog_type=dialog_type)
        if success:
            self._food_desc.clear()

    def _save_facility(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return

        agency = self._fac_agency.get()
        if not agency:
            MessageDialog(self, title="Error", message="Agency name is required.", dialog_type="error")
            return

        data = {
            "agency_name": agency,
            "facility_type": self._fac_type.get(),
            "address": self._fac_address.get() or None,
        }
        success, msg = save_government_facility(self._selected_barangay_id, data, self._get_user_id())
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Facility", message=msg, dialog_type=dialog_type)
        if success:
            self._fac_agency.clear()
            self._fac_address.clear()

    def _save_religion(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        religion = self._rel_religion.get()
        if not religion:
            MessageDialog(self, title="Error", message="Religion is required.", dialog_type="error")
            return

        data = {
            "year": year,
            "religion": religion,
            "count": self._rel_count.get_int(),
            "percentage": self._rel_pct.get_float(),
        }
        success, msg = save_religious_demographic(self._selected_barangay_id, data, self._get_user_id())
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Religious Data", message=msg, dialog_type=dialog_type)
        if success:
            self._rel_religion.clear()
            self._rel_count.clear()
            self._rel_pct.clear()

    # ── Health Tab ────────────────────────────────────────────

    def _build_health_tab(self):
        tab = self._tabview.tab("Health")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        fields_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        fields_frame.pack(fill="x")

        self._health_fields = {}
        field_defs = [
            ("dengue_cases", "Dengue Cases", "number"),
            ("tuberculosis_cases", "Tuberculosis Cases", "number"),
            ("covid_cases", "COVID Cases", "number"),
            ("diarrhea_cases", "Diarrhea Cases", "number"),
            ("pneumonia_cases", "Pneumonia Cases", "number"),
            ("hypertension_cases", "Hypertension Cases", "number"),
            ("diabetes_cases", "Diabetes Cases", "number"),
            ("other_disease_cases", "Other Disease Cases", "number"),
            ("vaccination_coverage_pct", "Vaccination Coverage %", "entry"),
            ("malnutrition_rate", "Malnutrition Rate %", "entry"),
            ("hospital_count", "Hospital Count", "number"),
            ("clinic_count", "Clinic Count", "number"),
            ("health_worker_count", "Health Worker Count", "number"),
            ("maternal_mortality", "Maternal Mortality", "number"),
            ("infant_mortality", "Infant Mortality", "number"),
        ]

        for i, (key, label, ftype) in enumerate(field_defs):
            if ftype == "number":
                field = LabeledNumberEntry(fields_frame, label=label, placeholder="0")
            else:
                field = LabeledEntry(fields_frame, label=label, placeholder="0.0")
            row, col = divmod(i, 3)
            field.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            fields_frame.columnconfigure(col, weight=1)
            self._health_fields[key] = field

        ctk.CTkButton(
            scroll, text="Save Health Statistics", command=self._save_health,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_LARGE, 0))

    def _save_health(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        data = {}
        for key, field in self._health_fields.items():
            if key in ("vaccination_coverage_pct", "malnutrition_rate"):
                data[key] = parse_float(field.get())
            else:
                data[key] = field.get_int() if hasattr(field, "get_int") else parse_int(field.get())

        success, msg = save_health_statistics(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Health Statistics", message=msg, dialog_type=dialog_type)

    # ── Social Welfare Tab ────────────────────────────────────

    def _build_social_welfare_tab(self):
        tab = self._tabview.tab("Social Welfare")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        fields_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        fields_frame.pack(fill="x")

        self._sw_fields = {}
        field_defs = [
            ("fourps_beneficiaries", "4Ps Beneficiaries"),
            ("senior_citizen_count", "Senior Citizen Count"),
            ("pwd_count", "PWD Count"),
            ("solo_parent_count", "Solo Parent Count"),
            ("indigent_families", "Indigent Families"),
            ("nutrition_program_beneficiaries", "Nutrition Program Beneficiaries"),
        ]

        for i, (key, label) in enumerate(field_defs):
            field = LabeledNumberEntry(fields_frame, label=label, placeholder="0")
            row, col = divmod(i, 3)
            field.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            fields_frame.columnconfigure(col, weight=1)
            self._sw_fields[key] = field

        ctk.CTkButton(
            scroll, text="Save Social Welfare Data", command=self._save_social_welfare,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_LARGE, 0))

    def _save_social_welfare(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        data = {key: field.get_int() for key, field in self._sw_fields.items()}
        success, msg = save_social_welfare_data(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Social Welfare Data", message=msg, dialog_type=dialog_type)

    # ── Disaster Risk Tab ─────────────────────────────────────

    def _build_disaster_risk_tab(self):
        tab = self._tabview.tab("Disaster Risk")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        fields_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        fields_frame.pack(fill="x")

        self._dr_fields = {}

        # Checkboxes row
        check_frame = ctk.CTkFrame(fields_frame, fg_color="transparent")
        check_frame.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        self._dr_flood_prone = ctk.CTkCheckBox(check_frame, text="Flood Prone")
        self._dr_flood_prone.pack(side="left", padx=(0, 20))

        self._dr_landslide_prone = ctk.CTkCheckBox(check_frame, text="Landslide Prone")
        self._dr_landslide_prone.pack(side="left")

        # Dropdowns
        risk_defs = [
            ("fire_risk_level", "Fire Risk Level"),
            ("earthquake_risk", "Earthquake Risk"),
            ("storm_surge_risk", "Storm Surge Risk"),
        ]
        for i, (key, label) in enumerate(risk_defs):
            field = LabeledDropdown(fields_frame, label=label, values=["low", "medium", "high"])
            field.grid(row=1, column=i, padx=5, pady=5, sticky="ew")
            fields_frame.columnconfigure(i, weight=1)
            self._dr_fields[key] = field

        # Number entries
        num_defs = [
            ("evacuation_center_count", "Evacuation Center Count"),
            ("evacuation_capacity", "Evacuation Capacity"),
        ]
        for i, (key, label) in enumerate(num_defs):
            field = LabeledNumberEntry(fields_frame, label=label, placeholder="0")
            field.grid(row=2, column=i, padx=5, pady=5, sticky="ew")
            self._dr_fields[key] = field

        ctk.CTkButton(
            scroll, text="Save Disaster Risk Profile", command=self._save_disaster_risk,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_LARGE, 0))

    def _save_disaster_risk(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        data = {
            "flood_prone": bool(self._dr_flood_prone.get()),
            "landslide_prone": bool(self._dr_landslide_prone.get()),
            "fire_risk_level": self._dr_fields["fire_risk_level"].get(),
            "earthquake_risk": self._dr_fields["earthquake_risk"].get(),
            "storm_surge_risk": self._dr_fields["storm_surge_risk"].get(),
            "evacuation_center_count": self._dr_fields["evacuation_center_count"].get_int(),
            "evacuation_capacity": self._dr_fields["evacuation_capacity"].get_int(),
        }
        success, msg = save_disaster_risk_profile(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Disaster Risk Profile", message=msg, dialog_type=dialog_type)

    # ── Education Tab ─────────────────────────────────────────

    def _build_education_tab(self):
        tab = self._tabview.tab("Education")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        fields_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        fields_frame.pack(fill="x")

        self._edu_fields = {}
        field_defs = [
            ("total_enrollees", "Total Enrollees", "number"),
            ("elementary_count", "Elementary Count", "number"),
            ("highschool_count", "High School Count", "number"),
            ("college_count", "College Count", "number"),
            ("out_of_school_youth", "Out-of-School Youth", "number"),
            ("school_count", "School Count", "number"),
            ("teacher_count", "Teacher Count", "number"),
            ("classroom_count", "Classroom Count", "number"),
            ("literacy_rate", "Literacy Rate %", "entry"),
            ("dropout_rate", "Dropout Rate %", "entry"),
        ]

        for i, (key, label, ftype) in enumerate(field_defs):
            if ftype == "number":
                field = LabeledNumberEntry(fields_frame, label=label, placeholder="0")
            else:
                field = LabeledEntry(fields_frame, label=label, placeholder="0.0")
            row, col = divmod(i, 3)
            field.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            fields_frame.columnconfigure(col, weight=1)
            self._edu_fields[key] = field

        ctk.CTkButton(
            scroll, text="Save Education Statistics", command=self._save_education,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, height=40,
        ).pack(pady=(PADDING_LARGE, 0))

    def _save_education(self):
        if not self._selected_barangay_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return
        year = self._get_year()
        if year is None:
            return

        data = {}
        for key, field in self._edu_fields.items():
            if key in ("literacy_rate", "dropout_rate"):
                data[key] = parse_float(field.get())
            else:
                data[key] = field.get_int() if hasattr(field, "get_int") else parse_int(field.get())

        success, msg = save_education_statistics(
            self._selected_barangay_id, year, data, self._get_user_id()
        )
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Education Statistics", message=msg, dialog_type=dialog_type)

    def refresh(self):
        pass
