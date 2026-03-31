import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, TEXT_LIGHT,
    BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.data_table import DataTable
from services.barangay_service import get_barangay_by_id
from services.population_service import get_population_records
from services.resident_service import get_resident_categories
from services.economic_service import get_income_records, get_businesses
from services.infrastructure_service import get_utility_records, get_land_types, get_waste_records
from services.community_service import get_food_sources, get_government_facilities, get_religious_demographics


class BarangayProfileView(ctk.CTkFrame):
    def __init__(self, master, barangay_id: int, on_back=None, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._barangay_id = barangay_id
        self._on_back = on_back
        self._build_ui()

    def _build_ui(self):
        brgy = get_barangay_by_id(self._barangay_id)
        if not brgy:
            ctk.CTkLabel(self, text="Barangay not found.", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(pady=40)
            return

        # Header with back button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        if self._on_back:
            ctk.CTkButton(
                header, text="\u2190 Back to List", command=self._on_back,
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
                fg_color="transparent", text_color=PRIMARY_COLOR,
                hover_color="#E3F2FD", width=120, height=30,
            ).pack(side="left")

        ctk.CTkLabel(
            header, text=f"Brgy. {brgy['name']}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(10, 0))

        # Info badges
        info_frame = ctk.CTkFrame(header, fg_color="transparent")
        info_frame.pack(side="right")

        ctk.CTkLabel(
            info_frame, text=brgy["district_name"],
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_LIGHT,
            fg_color=PRIMARY_COLOR, corner_radius=4, padx=8, pady=2,
        ).pack(side="left", padx=5)

        if brgy["classification"]:
            ctk.CTkLabel(
                info_frame, text=brgy["classification"].capitalize(),
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_LIGHT,
                fg_color="#757575", corner_radius=4, padx=8, pady=2,
            ).pack(side="left")

        # Tabview
        tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        # Overview tab
        tab_overview = tabview.add("Overview")
        self._build_overview(tab_overview, brgy)

        # Population tab
        tab_pop = tabview.add("Population")
        self._build_population(tab_pop)

        # Residents tab
        tab_res = tabview.add("Residents")
        self._build_residents(tab_res)

        # Economic tab
        tab_econ = tabview.add("Economic")
        self._build_economic(tab_econ)

        # Infrastructure tab
        tab_infra = tabview.add("Infrastructure")
        self._build_infrastructure(tab_infra)

        # Community tab
        tab_comm = tabview.add("Community")
        self._build_community(tab_comm)

    def _build_overview(self, parent, brgy):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        fields = [
            ("District", brgy["district_name"]),
            ("Classification", brgy.get("classification", "N/A") or "N/A"),
            ("Latitude", brgy.get("latitude") or "Not set"),
            ("Longitude", brgy.get("longitude") or "Not set"),
            ("Area (sq km)", brgy.get("area_sqkm") or "Not set"),
        ]

        for label, value in fields:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=f"{label}:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                         text_color=TEXT_PRIMARY, width=150, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(value), font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                         text_color=TEXT_SECONDARY).pack(side="left")

    def _build_population(self, parent):
        records = get_population_records(self._barangay_id)
        if not records:
            ctk.CTkLabel(parent, text="No population data recorded yet.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=30)
            return

        columns = [
            {"key": "year", "title": "Year", "width": 1},
            {"key": "total_population", "title": "Total Pop.", "width": 1},
            {"key": "male_count", "title": "Male", "width": 1},
            {"key": "female_count", "title": "Female", "width": 1},
            {"key": "registered_voters", "title": "Voters", "width": 1},
            {"key": "household_count", "title": "Households", "width": 1},
        ]
        table = DataTable(parent, columns=columns)
        table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)
        table.set_data(records)

    def _build_residents(self, parent):
        records = get_resident_categories(self._barangay_id)
        if not records:
            ctk.CTkLabel(parent, text="No resident category data recorded yet.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=30)
            return

        columns = [
            {"key": "year", "title": "Year", "width": 1},
            {"key": "renters_count", "title": "Renters", "width": 1},
            {"key": "homeowners_count", "title": "Homeowners", "width": 1},
            {"key": "squatters_count", "title": "Squatters", "width": 1},
            {"key": "informal_settlers_count", "title": "Informal Settlers", "width": 1},
        ]
        table = DataTable(parent, columns=columns)
        table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=PADDING_NORMAL)
        table.set_data(records)

    def _build_economic(self, parent):
        # Income data
        income_records = get_income_records(self._barangay_id)
        businesses_data = get_businesses(self._barangay_id)

        if not income_records and not businesses_data:
            ctk.CTkLabel(parent, text="No economic data recorded yet.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=30)
            return

        if income_records:
            ctk.CTkLabel(parent, text="Income Data", font=(FONT_FAMILY, 14, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
            columns = [
                {"key": "year", "title": "Year", "width": 1},
                {"key": "average_household_income", "title": "Avg Income (PHP)", "width": 2},
                {"key": "below_poverty_count", "title": "Below Poverty", "width": 1},
                {"key": "low_income_count", "title": "Low", "width": 1},
                {"key": "middle_income_count", "title": "Middle", "width": 1},
                {"key": "high_income_count", "title": "High", "width": 1},
            ]
            table = DataTable(parent, columns=columns)
            table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))
            table.set_data(income_records)

        if businesses_data:
            ctk.CTkLabel(parent, text=f"Businesses ({len(businesses_data)})",
                         font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY).pack(
                anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
            columns = [
                {"key": "name", "title": "Name", "width": 3},
                {"key": "type", "title": "Type", "width": 2},
                {"key": "is_active", "title": "Active", "width": 1},
                {"key": "registered_date", "title": "Registered", "width": 1},
            ]
            table = DataTable(parent, columns=columns)
            table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))
            table.set_data(businesses_data)

    def _build_infrastructure(self, parent):
        utilities = get_utility_records(self._barangay_id)
        land = get_land_types(self._barangay_id)
        waste = get_waste_records(self._barangay_id)

        if not utilities and not land and not waste:
            ctk.CTkLabel(parent, text="No infrastructure data recorded yet.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=30)
            return

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        if utilities:
            ctk.CTkLabel(scroll, text="Utilities", font=(FONT_FAMILY, 14, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
            columns = [
                {"key": "year", "title": "Year", "width": 1},
                {"key": "water_source", "title": "Water Source", "width": 2},
                {"key": "water_coverage_pct", "title": "Water %", "width": 1},
                {"key": "power_provider", "title": "Power", "width": 2},
                {"key": "power_coverage_pct", "title": "Power %", "width": 1},
                {"key": "internet_coverage_pct", "title": "Internet %", "width": 1},
            ]
            table = DataTable(scroll, columns=columns)
            table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 10))
            table.set_data(utilities)

        if land:
            ctk.CTkLabel(scroll, text="Land Types", font=(FONT_FAMILY, 14, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(10, 5))
            columns = [
                {"key": "type", "title": "Type", "width": 2},
                {"key": "area_sqkm", "title": "Area (sq km)", "width": 1},
                {"key": "percentage", "title": "Percentage %", "width": 1},
            ]
            table = DataTable(scroll, columns=columns)
            table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 10))
            table.set_data(land)

        if waste:
            ctk.CTkLabel(scroll, text="Waste Management", font=(FONT_FAMILY, 14, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(10, 5))
            columns = [
                {"key": "year", "title": "Year", "width": 1},
                {"key": "collection_frequency", "title": "Frequency", "width": 2},
                {"key": "disposal_method", "title": "Method", "width": 2},
                {"key": "coverage_pct", "title": "Coverage %", "width": 1},
            ]
            table = DataTable(scroll, columns=columns)
            table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 10))
            table.set_data(waste)

    def _build_community(self, parent):
        food = get_food_sources(self._barangay_id)
        facilities = get_government_facilities(self._barangay_id)
        religion = get_religious_demographics(self._barangay_id)

        if not food and not facilities and not religion:
            ctk.CTkLabel(parent, text="No community data recorded yet.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=30)
            return

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        if food:
            ctk.CTkLabel(scroll, text="Food Sources", font=(FONT_FAMILY, 14, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
            columns = [
                {"key": "type", "title": "Type", "width": 1},
                {"key": "description", "title": "Description", "width": 3},
            ]
            table = DataTable(scroll, columns=columns)
            table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 10))
            table.set_data(food)

        if facilities:
            ctk.CTkLabel(scroll, text="Government Facilities", font=(FONT_FAMILY, 14, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(10, 5))
            columns = [
                {"key": "agency_name", "title": "Agency", "width": 2},
                {"key": "facility_type", "title": "Type", "width": 2},
                {"key": "address", "title": "Address", "width": 3},
            ]
            table = DataTable(scroll, columns=columns)
            table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 10))
            table.set_data(facilities)

        if religion:
            ctk.CTkLabel(scroll, text="Religious Demographics", font=(FONT_FAMILY, 14, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(10, 5))
            columns = [
                {"key": "year", "title": "Year", "width": 1},
                {"key": "religion", "title": "Religion", "width": 2},
                {"key": "count", "title": "Count", "width": 1},
                {"key": "percentage", "title": "Percentage %", "width": 1},
            ]
            table = DataTable(scroll, columns=columns)
            table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 10))
            table.set_data(religion)
