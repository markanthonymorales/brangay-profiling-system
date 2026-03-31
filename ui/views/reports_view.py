import os
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.data_table import DataTable
from ui.components.form_fields import LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from services.barangay_service import get_all_districts, get_barangays_by_district
from services.report_service import (
    get_barangay_full_profile, get_district_report,
    get_citywide_report, get_comparative_report,
)
from utils.export import export_report_to_csv
from utils.pdf_builder import build_pdf
from config import BASE_DIR


REPORT_TYPES = [
    "Barangay Profile",
    "District Summary",
    "City-Wide Summary",
    "Comparative",
]


class ReportsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._report_data = None
        self._report_type_key = None
        self._selected_barangay_ids: list[int] = []
        self._checkboxes: list[tuple[ctk.CTkCheckBox, int]] = []
        self._build_ui()

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="Reports",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Report type selector
        type_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        type_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        type_inner = ctk.CTkFrame(type_frame, fg_color="transparent")
        type_inner.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        self._type_dropdown = LabeledDropdown(
            type_inner, label="Report Type", values=REPORT_TYPES,
            command=self._on_type_change,
        )
        self._type_dropdown.pack(side="left", padx=(0, 15), fill="x", expand=True)

        # Dynamic selectors frame
        self._selectors_frame = ctk.CTkFrame(type_inner, fg_color="transparent")
        self._selectors_frame.pack(side="left", fill="x", expand=True)

        # Generate button
        self._generate_btn = ctk.CTkButton(
            type_inner, text="Generate Preview", command=self._generate_preview,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=150, height=38,
        )
        self._generate_btn.pack(side="right", pady=(18, 0))

        # Preview area
        self._preview_frame = ctk.CTkScrollableFrame(self, fg_color=CARD_BG, corner_radius=12)
        self._preview_frame.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        # Placeholder
        self._placeholder = ctk.CTkLabel(
            self._preview_frame, text="Select a report type and click 'Generate Preview'",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._placeholder.pack(pady=40)

        # Export buttons
        export_frame = ctk.CTkFrame(self, fg_color="transparent")
        export_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._pdf_btn = ctk.CTkButton(
            export_frame, text="Export PDF", command=self._export_pdf,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, width=140, height=38,
            state="disabled",
        )
        self._pdf_btn.pack(side="left", padx=(0, 10))

        self._csv_btn = ctk.CTkButton(
            export_frame, text="Export CSV", command=self._export_csv,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=140, height=38,
            state="disabled",
        )
        self._csv_btn.pack(side="left")

        # Load districts
        self._districts = get_all_districts()
        self._district_map = {d["name"]: d["id"] for d in self._districts}
        self._barangay_map: dict[str, int] = {}

        # Initialize selectors for default type
        self._on_type_change(REPORT_TYPES[0])

    def _clear_selectors(self):
        for w in self._selectors_frame.winfo_children():
            w.destroy()
        self._checkboxes.clear()

    def _on_type_change(self, report_type: str):
        self._clear_selectors()
        self._report_data = None
        self._pdf_btn.configure(state="disabled")
        self._csv_btn.configure(state="disabled")

        district_names = [d["name"] for d in self._districts]

        if report_type == "Barangay Profile":
            self._district_selector = LabeledDropdown(
                self._selectors_frame, label="District", values=district_names,
                command=self._on_district_change_for_barangay,
            )
            self._district_selector.pack(side="left", padx=(0, 10), fill="x", expand=True)

            self._barangay_selector = LabeledDropdown(
                self._selectors_frame, label="Barangay", values=[],
            )
            self._barangay_selector.pack(side="left", fill="x", expand=True)

            if district_names:
                self._on_district_change_for_barangay(district_names[0])

        elif report_type == "District Summary":
            self._district_selector = LabeledDropdown(
                self._selectors_frame, label="District", values=district_names,
            )
            self._district_selector.pack(side="left", fill="x", expand=True)

        elif report_type == "City-Wide Summary":
            ctk.CTkLabel(
                self._selectors_frame, text="No additional selection needed.",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
            ).pack(side="left", pady=(18, 0))

        elif report_type == "Comparative":
            self._comp_district_selector = LabeledDropdown(
                self._selectors_frame, label="Filter by District", values=["All"] + district_names,
                command=self._on_district_change_for_comparative,
            )
            self._comp_district_selector.pack(side="left", padx=(0, 10), fill="x", expand=True)

            self._comp_list_frame = ctk.CTkScrollableFrame(
                self._selectors_frame, fg_color="transparent", width=300, height=120,
            )
            self._comp_list_frame.pack(side="left", fill="both", expand=True)

            self._on_district_change_for_comparative("All")

    def _on_district_change_for_barangay(self, district_name: str):
        district_id = self._district_map.get(district_name)
        if district_id is None:
            return
        barangays = get_barangays_by_district(district_id)
        self._barangay_map = {b["name"]: b["id"] for b in barangays}
        names = list(self._barangay_map.keys())
        self._barangay_selector.set_values(names)
        if names:
            self._barangay_selector.set(names[0])

    def _on_district_change_for_comparative(self, district_name: str):
        for w in self._comp_list_frame.winfo_children():
            w.destroy()
        self._checkboxes.clear()

        if district_name == "All":
            for d in self._districts:
                barangays = get_barangays_by_district(d["id"])
                for b in barangays:
                    self._add_checkbox(b["name"], b["id"])
        else:
            district_id = self._district_map.get(district_name)
            if district_id:
                barangays = get_barangays_by_district(district_id)
                for b in barangays:
                    self._add_checkbox(b["name"], b["id"])

    def _add_checkbox(self, name: str, brgy_id: int):
        var = ctk.BooleanVar(value=False)
        cb = ctk.CTkCheckBox(
            self._comp_list_frame, text=name,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            variable=var,
        )
        cb.pack(anchor="w", pady=1)
        self._checkboxes.append((cb, brgy_id))

    def _get_selected_comparative_ids(self) -> list[int]:
        ids = []
        for cb, brgy_id in self._checkboxes:
            if cb.cget("variable") and ctk.BooleanVar(master=cb).get() is not None:
                try:
                    # Access the variable directly
                    var_name = cb.cget("variable")
                    if self._comp_list_frame.getvar(var_name):
                        ids.append(brgy_id)
                except Exception:
                    pass
        return ids

    def _generate_preview(self):
        report_type = self._type_dropdown.get()

        # Clear preview
        for w in self._preview_frame.winfo_children():
            w.destroy()

        try:
            if report_type == "Barangay Profile":
                brgy_name = self._barangay_selector.get()
                brgy_id = self._barangay_map.get(brgy_name)
                if not brgy_id:
                    MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
                    return
                self._report_data = get_barangay_full_profile(brgy_id)
                self._report_type_key = "barangay_profile"
                self._preview_barangay_profile()

            elif report_type == "District Summary":
                district_name = self._district_selector.get()
                district_id = self._district_map.get(district_name)
                if not district_id:
                    MessageDialog(self, title="Error", message="Please select a district.", dialog_type="error")
                    return
                self._report_data = get_district_report(district_id)
                self._report_type_key = "district_summary"
                self._preview_district_summary()

            elif report_type == "City-Wide Summary":
                self._report_data = get_citywide_report()
                self._report_type_key = "citywide"
                self._preview_citywide()

            elif report_type == "Comparative":
                selected_ids = self._get_selected_comparative_ids()
                if len(selected_ids) < 2:
                    MessageDialog(self, title="Error",
                                  message="Please select at least 2 barangays for comparison.",
                                  dialog_type="error")
                    return
                if len(selected_ids) > 5:
                    MessageDialog(self, title="Error",
                                  message="Please select at most 5 barangays for comparison.",
                                  dialog_type="error")
                    return
                self._report_data = get_comparative_report(selected_ids)
                self._report_type_key = "comparative"
                self._preview_comparative()

            # Enable export buttons
            if self._report_data:
                self._pdf_btn.configure(state="normal")
                self._csv_btn.configure(state="normal")

        except Exception as e:
            ctk.CTkLabel(
                self._preview_frame, text=f"Error generating preview: {e}",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=DANGER_COLOR,
            ).pack(pady=20)

    def _preview_barangay_profile(self):
        data = self._report_data
        if not data:
            return

        brgy = data.get("barangay", {})
        ctk.CTkLabel(
            self._preview_frame, text=f"Barangay Profile: {brgy.get('name', '')}",
            font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkLabel(
            self._preview_frame,
            text=f"{brgy.get('district_name', '')} | {brgy.get('classification', 'N/A')}",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 10))

        sections = [
            ("Population", "population", ["year", "total_population", "male_count", "female_count", "household_count"]),
            ("Income", "income", ["year", "average_household_income", "below_poverty_count"]),
            ("Utilities", "utilities", ["year", "water_source", "water_coverage_pct", "power_coverage_pct", "internet_coverage_pct"]),
        ]

        for title, key, cols in sections:
            records = data.get(key, [])
            if records:
                ctk.CTkLabel(
                    self._preview_frame, text=title,
                    font=(FONT_FAMILY, 13, "bold"), text_color=TEXT_PRIMARY,
                ).pack(anchor="w", padx=PADDING_NORMAL, pady=(10, 3))

                columns = [{"key": c, "title": c.replace("_", " ").title(), "width": 1} for c in cols]
                table = DataTable(self._preview_frame, columns=columns)
                table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 5))
                table.set_data(records)

        # Show counts for other sections
        other = [
            ("Businesses", len(data.get("businesses", []))),
            ("Food Sources", len(data.get("food_sources", []))),
            ("Government Facilities", len(data.get("government_facilities", []))),
            ("Religious Demographics", len(data.get("religious_demographics", []))),
        ]
        for name, count in other:
            if count > 0:
                ctk.CTkLabel(
                    self._preview_frame, text=f"{name}: {count} record(s)",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
                ).pack(anchor="w", padx=PADDING_NORMAL, pady=2)

        if not any(data.get(k) for k in ["population", "income", "utilities", "businesses"]):
            ctk.CTkLabel(
                self._preview_frame, text="No data recorded for this barangay yet.",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
            ).pack(pady=20)

    def _preview_district_summary(self):
        data = self._report_data
        if not data:
            return

        district = data.get("district", {})
        ctk.CTkLabel(
            self._preview_frame, text=f"District Summary: {district.get('name', '')}",
            font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._preview_summary_tables(data)

        brgy_list = data.get("barangay_list", [])
        if brgy_list:
            ctk.CTkLabel(
                self._preview_frame, text=f"Barangays ({len(brgy_list)})",
                font=(FONT_FAMILY, 13, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=PADDING_NORMAL, pady=(10, 3))
            columns = [
                {"key": "name", "title": "Barangay", "width": 3},
                {"key": "population", "title": "Population", "width": 1},
                {"key": "classification", "title": "Classification", "width": 1},
            ]
            table = DataTable(self._preview_frame, columns=columns)
            table.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 10))
            table.set_data(brgy_list)

    def _preview_citywide(self):
        data = self._report_data
        if not data:
            return

        city = data.get("city", {})
        ctk.CTkLabel(
            self._preview_frame, text="Davao City - City-Wide Summary",
            font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkLabel(
            self._preview_frame,
            text=f"{city.get('total_barangays', 0)} Barangays | {city.get('total_districts', 0)} Districts",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 10))

        self._preview_summary_tables(data)

        # District breakdown
        for dr in data.get("districts", []):
            d_info = dr.get("district", {})
            ctk.CTkLabel(
                self._preview_frame,
                text=f"{d_info.get('name', '')} - {d_info.get('barangay_count', 0)} Barangays",
                font=(FONT_FAMILY, 12, "bold"), text_color=PRIMARY_COLOR,
            ).pack(anchor="w", padx=PADDING_NORMAL, pady=(10, 3))

            d_pop = dr.get("population", {})
            text = f"Pop: {d_pop.get('total_population', 0):,} | Households: {d_pop.get('total_households', 0):,}"
            ctk.CTkLabel(
                self._preview_frame, text=text,
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
            ).pack(anchor="w", padx=PADDING_NORMAL)

    def _preview_comparative(self):
        data = self._report_data
        if not data:
            return

        barangays = data.get("barangays", [])
        ctk.CTkLabel(
            self._preview_frame, text="Comparative Report",
            font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        if not barangays:
            ctk.CTkLabel(
                self._preview_frame, text="No data available.",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
            ).pack(pady=20)
            return

        columns = [
            {"key": "name", "title": "Barangay", "width": 2},
            {"key": "district_name", "title": "District", "width": 2},
            {"key": "population", "title": "Population", "width": 1},
            {"key": "household_count", "title": "Households", "width": 1},
            {"key": "avg_income", "title": "Avg Income", "width": 1},
            {"key": "water_coverage", "title": "Water %", "width": 1},
            {"key": "power_coverage", "title": "Power %", "width": 1},
            {"key": "internet_coverage", "title": "Internet %", "width": 1},
            {"key": "business_count", "title": "Businesses", "width": 1},
        ]
        table = DataTable(self._preview_frame, columns=columns)
        table.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)
        table.set_data(barangays)

    def _preview_summary_tables(self, data: dict):
        pop = data.get("population", {})
        inc = data.get("income", {})
        util = data.get("utilities", {})
        biz = data.get("businesses", {})

        summary_items = [
            ("Population", [
                ("Total Population", f"{pop.get('total_population', 0):,}"),
                ("Male", f"{pop.get('total_male', 0):,}"),
                ("Female", f"{pop.get('total_female', 0):,}"),
                ("Households", f"{pop.get('total_households', 0):,}"),
                ("Voters", f"{pop.get('total_voters', 0):,}"),
            ]),
            ("Income", [
                ("Avg Household Income (PHP)", f"{inc.get('average_household_income', 0):,.2f}"),
                ("Below Poverty Line", f"{inc.get('total_below_poverty', 0):,}"),
            ]),
            ("Utilities (Avg %)", [
                ("Water Coverage", f"{util.get('avg_water_coverage', 0):.1f}%"),
                ("Power Coverage", f"{util.get('avg_power_coverage', 0):.1f}%"),
                ("Internet Coverage", f"{util.get('avg_internet_coverage', 0):.1f}%"),
            ]),
            ("Businesses", [
                ("Active", f"{biz.get('total_active', 0):,}"),
                ("Inactive", f"{biz.get('total_inactive', 0):,}"),
            ]),
        ]

        for section_title, items in summary_items:
            ctk.CTkLabel(
                self._preview_frame, text=section_title,
                font=(FONT_FAMILY, 13, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=PADDING_NORMAL, pady=(10, 3))

            for label, value in items:
                row = ctk.CTkFrame(self._preview_frame, fg_color="transparent")
                row.pack(fill="x", padx=PADDING_NORMAL, pady=1)
                ctk.CTkLabel(row, text=f"{label}:", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                             text_color=TEXT_PRIMARY, width=250, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=value, font=(FONT_FAMILY, FONT_SIZE_SMALL),
                             text_color=TEXT_SECONDARY).pack(side="left")

    def _get_default_filename(self, ext: str) -> str:
        report_type = self._type_dropdown.get()
        date_str = datetime.now().strftime("%Y%m%d")

        if report_type == "Barangay Profile":
            brgy_name = self._barangay_selector.get().replace(" ", "_")
            return f"Barangay_Profile_{brgy_name}_{date_str}.{ext}"
        elif report_type == "District Summary":
            dist_name = self._district_selector.get().replace(" ", "_")
            return f"District_Summary_{dist_name}_{date_str}.{ext}"
        elif report_type == "City-Wide Summary":
            return f"Citywide_Summary_{date_str}.{ext}"
        elif report_type == "Comparative":
            return f"Comparative_Report_{date_str}.{ext}"
        return f"Report_{date_str}.{ext}"

    def _export_pdf(self):
        if not self._report_data or not self._report_type_key:
            return

        default_dir = os.path.join(BASE_DIR, "data", "reports")
        os.makedirs(default_dir, exist_ok=True)

        filepath = filedialog.asksaveasfilename(
            initialdir=default_dir,
            initialfile=self._get_default_filename("pdf"),
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
        )
        if not filepath:
            return

        success, msg = build_pdf(self._report_type_key, self._report_data, filepath)
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Export PDF", message=msg, dialog_type=dialog_type)

    def _export_csv(self):
        if not self._report_data or not self._report_type_key:
            return

        default_dir = os.path.join(BASE_DIR, "data", "reports")
        os.makedirs(default_dir, exist_ok=True)

        filepath = filedialog.asksaveasfilename(
            initialdir=default_dir,
            initialfile=self._get_default_filename("csv"),
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not filepath:
            return

        success, msg = export_report_to_csv(self._report_type_key, self._report_data, filepath)
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Export CSV", message=msg, dialog_type=dialog_type)

    def refresh(self):
        pass
