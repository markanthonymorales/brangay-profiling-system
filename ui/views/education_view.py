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
from services.education_service import (
    save_education_statistics, get_education_statistics,
    get_education_stats_by_year, get_education_summary, get_education_trend,
)

COLORS = {
    "blue": "#1E88E5", "green": "#43A047", "orange": "#FB8C00",
    "red": "#E53935", "purple": "#7B1FA2", "pink": "#E91E63",
    "teal": "#00897B", "yellow": "#FDD835", "grey": "#757575",
    "cyan": "#00ACC1", "indigo": "#3949AB",
}

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, CURRENT_YEAR - 11, -1)]


class EducationView(ctk.CTkFrame):
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
            self, text="Education",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_education_statistics_tab()
        self._build_education_overview_tab()
        self._build_school_capacity_tab()

    # ── Tab 1: Education Statistics ───────────────────────────────

    def _build_education_statistics_tab(self):
        tab = self._tabview.add("Education Statistics")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._es_district = LabeledDropdown(
            controls, label="District", values=["All"] + district_names,
            command=self._on_es_district_change,
        )
        self._es_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._es_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._es_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._es_year = LabeledDropdown(controls, label="Year", values=["All"] + YEAR_OPTIONS)
        self._es_year.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(
            btn_frame, text="Filter", command=self._filter_education,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=70, height=30,
        ).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(
                btn_frame, text="+ Add", command=self._add_education_dialog,
                font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                text_color=TEXT_LIGHT, width=70, height=30,
            ).pack(side="left", pady=(18, 0), padx=2)

        self._es_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                      text_color=TEXT_SECONDARY)
        self._es_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "year", "title": "Year", "width": 1},
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "total_enrollees", "title": "Total Enrollees", "width": 2},
            {"key": "literacy_rate", "title": "Literacy Rate (%)", "width": 2},
            {"key": "dropout_rate", "title": "Dropout Rate (%)", "width": 2},
            {"key": "out_of_school_youth", "title": "Out-of-School Youth", "width": 2},
            {"key": "school_count", "title": "Schools", "width": 1},
        ]
        self._es_table = DataTable(tab, columns=columns, on_row_click=self._on_education_row_click)
        self._es_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_es_district_change(self, district_name: str):
        if district_name == "All":
            self._es_barangay.set_values(["All"])
            self._es_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._es_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._es_barangay.set("All")

    def _filter_education(self):
        district = self._es_district.get()
        brgy_name = self._es_barangay.get()
        year_val = self._es_year.get()

        barangay_id = None
        district_id = None

        if district != "All":
            district_id = self._district_map.get(district)
            if brgy_name != "All":
                brgy_map = self._load_barangays(district)
                barangay_id = brgy_map.get(brgy_name)

        if barangay_id:
            # Get per-barangay records
            data = get_education_statistics(barangay_id)
            if year_val != "All":
                data = [r for r in data if str(r["year"]) == year_val]
            # Add barangay_name from brgy_map
            brgy_map = self._load_barangays(district)
            for row in data:
                row["barangay_name"] = brgy_name
        else:
            year_int = int(year_val) if year_val != "All" else CURRENT_YEAR
            data = get_education_stats_by_year(year_int, district_id=district_id)

        self._es_table.set_data(data)
        self._es_count.configure(text=f"Showing {len(data)} record(s)")

    def _add_education_dialog(self):
        self._education_dialog(None)

    def _on_education_row_click(self, row_data):
        self._education_dialog(row_data)

    def _education_dialog(self, existing: dict | None):
        is_edit = existing is not None
        title = "Edit Education Statistics" if is_edit else "Add Education Statistics"

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("500x620")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text=title,
            font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY,
        ).pack(pady=(15, 10))

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20)

        # District / Barangay / Year
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

        d_year = LabeledDropdown(scroll, label="Year", values=YEAR_OPTIONS, required=True)
        d_year.pack(fill="x", pady=2)

        # Enrollment fields
        d_total_enrollees = LabeledNumberEntry(scroll, label="Total Enrollees")
        d_total_enrollees.pack(fill="x", pady=2)

        d_elementary = LabeledNumberEntry(scroll, label="Elementary Count")
        d_elementary.pack(fill="x", pady=2)

        d_highschool = LabeledNumberEntry(scroll, label="High School Count")
        d_highschool.pack(fill="x", pady=2)

        d_college = LabeledNumberEntry(scroll, label="College Count")
        d_college.pack(fill="x", pady=2)

        d_osy = LabeledNumberEntry(scroll, label="Out-of-School Youth")
        d_osy.pack(fill="x", pady=2)

        # Rate fields
        d_literacy = LabeledEntry(scroll, label="Literacy Rate (%)", placeholder="e.g. 95.5")
        d_literacy.pack(fill="x", pady=2)

        d_dropout = LabeledEntry(scroll, label="Dropout Rate (%)", placeholder="e.g. 3.2")
        d_dropout.pack(fill="x", pady=2)

        # School capacity fields
        d_school_count = LabeledNumberEntry(scroll, label="School Count")
        d_school_count.pack(fill="x", pady=2)

        d_teacher_count = LabeledNumberEntry(scroll, label="Teacher Count")
        d_teacher_count.pack(fill="x", pady=2)

        d_classroom_count = LabeledNumberEntry(scroll, label="Classroom Count")
        d_classroom_count.pack(fill="x", pady=2)

        # Pre-fill for edit
        if is_edit:
            edit_district = existing.get("district_name", "")
            edit_barangay = existing.get("barangay_name", "")
            if edit_district and edit_district in district_names:
                d_district.set(edit_district)
                on_district_sel(edit_district)
                if edit_barangay:
                    d_barangay.set(edit_barangay)
            elif not edit_district and edit_barangay:
                # Try to find the district from barangay_id
                for dn in district_names:
                    brgy_map = self._load_barangays(dn)
                    if edit_barangay in brgy_map:
                        d_district.set(dn)
                        on_district_sel(dn)
                        d_barangay.set(edit_barangay)
                        break

            year_str = str(existing.get("year", CURRENT_YEAR))
            if year_str in YEAR_OPTIONS:
                d_year.set(year_str)

            if existing.get("total_enrollees") is not None:
                d_total_enrollees.set(str(existing["total_enrollees"]))
            if existing.get("elementary_count") is not None:
                d_elementary.set(str(existing["elementary_count"]))
            if existing.get("highschool_count") is not None:
                d_highschool.set(str(existing["highschool_count"]))
            if existing.get("college_count") is not None:
                d_college.set(str(existing["college_count"]))
            if existing.get("out_of_school_youth") is not None:
                d_osy.set(str(existing["out_of_school_youth"]))
            if existing.get("literacy_rate") is not None:
                d_literacy.set(str(existing["literacy_rate"]))
            if existing.get("dropout_rate") is not None:
                d_dropout.set(str(existing["dropout_rate"]))
            if existing.get("school_count") is not None:
                d_school_count.set(str(existing["school_count"]))
            if existing.get("teacher_count") is not None:
                d_teacher_count.set(str(existing["teacher_count"]))
            if existing.get("classroom_count") is not None:
                d_classroom_count.set(str(existing["classroom_count"]))

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

            year_str = d_year.get()
            try:
                year_int = int(year_str)
            except ValueError:
                error_label.configure(text="Invalid year.")
                return

            # Parse rates
            literacy_val = None
            dropout_val = None
            lr_text = d_literacy.get()
            if lr_text:
                try:
                    literacy_val = float(lr_text)
                except ValueError:
                    error_label.configure(text="Literacy rate must be a number.")
                    return

            dr_text = d_dropout.get()
            if dr_text:
                try:
                    dropout_val = float(dr_text)
                except ValueError:
                    error_label.configure(text="Dropout rate must be a number.")
                    return

            data = {
                "total_enrollees": d_total_enrollees.get_int(),
                "elementary_count": d_elementary.get_int(),
                "highschool_count": d_highschool.get_int(),
                "college_count": d_college.get_int(),
                "out_of_school_youth": d_osy.get_int(),
                "literacy_rate": literacy_val,
                "dropout_rate": dropout_val,
                "school_count": d_school_count.get_int(),
                "teacher_count": d_teacher_count.get_int(),
                "classroom_count": d_classroom_count.get_int(),
            }

            success, msg = save_education_statistics(brgy_id, year_int, data, self._get_user_id())
            if success:
                dialog.destroy()
                self._filter_education()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(
            btn_frame, text="Save", command=do_save,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
            text_color=TEXT_LIGHT, width=100, height=35,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Cancel", command=dialog.destroy,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=COLORS["grey"],
            text_color=TEXT_LIGHT, width=100, height=35,
        ).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    # ── Tab 2: Education Overview ─────────────────────────────────

    def _build_education_overview_tab(self):
        tab = self._tabview.add("Education Overview")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._eo_scope = LabeledDropdown(
            controls, label="Scope",
            values=["City-Wide", "By District", "By Barangay"],
        )
        self._eo_scope.pack(side="left", padx=(0, 8), fill="x", expand=True)

        district_names = [d["name"] for d in self._districts]
        self._eo_district = LabeledDropdown(
            controls, label="District", values=district_names,
            command=self._on_eo_district_change,
        )
        self._eo_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._eo_barangay = LabeledDropdown(controls, label="Barangay", values=[])
        self._eo_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkButton(
            controls, text="Update", command=self._update_education_overview,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=100, height=35,
        ).pack(side="left", pady=(18, 0))

        self._eo_chart = ChartWidget(tab, figsize=(9, 5))
        self._eo_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _on_eo_district_change(self, dn: str):
        brgy_map = self._load_barangays(dn)
        names = list(brgy_map.keys())
        self._eo_barangay.set_values(names)
        if names:
            self._eo_barangay.set(names[0])

    def _update_education_overview(self):
        scope = self._eo_scope.get()
        barangay_id = None
        district_id = None

        if scope == "By District":
            district_id = self._district_map.get(self._eo_district.get())
        elif scope == "By Barangay":
            dn = self._eo_district.get()
            brgy_map = self._load_barangays(dn)
            barangay_id = brgy_map.get(self._eo_barangay.get())

        trend = get_education_trend(barangay_id=barangay_id, district_id=district_id)

        # For district-level charts, gather data per district
        district_summary = []
        if scope == "City-Wide":
            for d in self._districts:
                summary = get_education_summary(district_id=d["id"])
                stats_list = get_education_stats_by_year(CURRENT_YEAR, district_id=d["id"])
                avg_literacy = (
                    round(sum(r["literacy_rate"] for r in stats_list) / len(stats_list), 1)
                    if stats_list else 0
                )
                avg_dropout = (
                    round(sum(r["dropout_rate"] for r in stats_list) / len(stats_list), 1)
                    if stats_list else 0
                )
                total_osy = sum(r["out_of_school_youth"] for r in stats_list)
                district_summary.append({
                    "name": d["name"],
                    "literacy": avg_literacy,
                    "dropout": avg_dropout,
                    "osy": total_osy,
                })

        # Get enrollment-by-level data
        if barangay_id:
            edu_records = get_education_statistics(barangay_id)
            if edu_records:
                latest = edu_records[0]
                level_data = {
                    "Elementary": latest.get("elementary_count") or 0,
                    "High School": latest.get("highschool_count") or 0,
                    "College": latest.get("college_count") or 0,
                }
            else:
                level_data = {"Elementary": 0, "High School": 0, "College": 0}
        else:
            # Aggregate level data from all stats
            year_int = CURRENT_YEAR
            all_stats = get_education_stats_by_year(year_int, district_id=district_id)
            # We need elementary/highschool/college from get_education_statistics per barangay
            # Use summary approach for level breakdown
            level_data = {"Elementary": 0, "High School": 0, "College": 0}
            for row in all_stats:
                brgy_records = get_education_statistics(row["barangay_id"])
                latest_year_rec = next((r for r in brgy_records if r["year"] == year_int), None)
                if latest_year_rec:
                    level_data["Elementary"] += latest_year_rec.get("elementary_count") or 0
                    level_data["High School"] += latest_year_rec.get("highschool_count") or 0
                    level_data["College"] += latest_year_rec.get("college_count") or 0

        if not trend and not any(level_data.values()):
            self._eo_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No education data available for this selection.",
                ha="center", va="center", fontsize=12, color="#999999", transform=ax.transAxes,
            ))
            return

        def draw(fig):
            # Top-left: Enrollment by level (stacked bar)
            ax1 = fig.add_subplot(221)
            levels = list(level_data.keys())
            counts = list(level_data.values())
            bar_colors = [COLORS["blue"], COLORS["green"], COLORS["orange"]]
            ax1.bar(levels, counts, color=bar_colors)
            ax1.set_title("Enrollment by Level", fontsize=10)
            ax1.set_ylabel("Count")
            for i, (lv, cnt) in enumerate(zip(levels, counts)):
                ax1.text(i, cnt + max(counts) * 0.02, str(cnt), ha="center", fontsize=8)

            # Top-right: Literacy rate by district (bar chart)
            ax2 = fig.add_subplot(222)
            if district_summary:
                d_names = [d["name"].replace("District ", "Dist. ") for d in district_summary]
                d_lit = [d["literacy"] for d in district_summary]
                ax2.bar(d_names, d_lit, color=COLORS["teal"])
                ax2.set_title("Avg Literacy Rate by District (%)", fontsize=10)
                ax2.set_ylabel("Rate (%)")
                ax2.set_ylim(0, 100)
                for i, val in enumerate(d_lit):
                    ax2.text(i, val + 0.5, f"{val}%", ha="center", fontsize=8)
            elif trend:
                # Single scope: show literacy trend
                years = [str(r["year"]) for r in trend]
                lits = [r["avg_literacy"] for r in trend]
                ax2.plot(years, lits, marker="o", color=COLORS["teal"], linewidth=2)
                ax2.set_title("Literacy Rate Trend (%)", fontsize=10)
                ax2.set_ylabel("Rate (%)")
                ax2.tick_params(axis="x", rotation=45, labelsize=7)

            # Bottom-left: Dropout rate trend
            ax3 = fig.add_subplot(223)
            if trend:
                years = [str(r["year"]) for r in trend]
                dropouts = [r["avg_dropout"] for r in trend]
                ax3.plot(years, dropouts, marker="o", color=COLORS["red"], linewidth=2)
                ax3.fill_between(range(len(years)), dropouts, alpha=0.15, color=COLORS["red"])
                ax3.set_title("Dropout Rate Trend (%)", fontsize=10)
                ax3.set_ylabel("Rate (%)")
                ax3.set_xticks(range(len(years)))
                ax3.set_xticklabels(years, rotation=45, fontsize=7)
            else:
                ax3.text(0.5, 0.5, "No trend data", ha="center", va="center",
                         fontsize=10, color="#999999", transform=ax3.transAxes)

            # Bottom-right: Out-of-school youth by district (bar chart)
            ax4 = fig.add_subplot(224)
            if district_summary:
                d_names = [d["name"].replace("District ", "Dist. ") for d in district_summary]
                d_osy = [d["osy"] for d in district_summary]
                ax4.bar(d_names, d_osy, color=COLORS["purple"])
                ax4.set_title("Out-of-School Youth by District", fontsize=10)
                ax4.set_ylabel("Count")
                for i, val in enumerate(d_osy):
                    ax4.text(i, val + max(d_osy) * 0.02 if max(d_osy) > 0 else 0.1,
                             str(val), ha="center", fontsize=8)
            elif trend:
                years = [str(r["year"]) for r in trend]
                osy_vals = [r["osy"] for r in trend]
                ax4.bar(years, osy_vals, color=COLORS["purple"])
                ax4.set_title("Out-of-School Youth Trend", fontsize=10)
                ax4.set_ylabel("Count")
                ax4.tick_params(axis="x", rotation=45, labelsize=7)
            else:
                ax4.text(0.5, 0.5, "No data", ha="center", va="center",
                         fontsize=10, color="#999999", transform=ax4.transAxes)

            fig.subplots_adjust(hspace=0.45, wspace=0.4, top=0.92, bottom=0.12, left=0.1, right=0.97)

        self._eo_chart.update_chart_multi(draw)

    # ── Tab 3: School Capacity ────────────────────────────────────

    def _build_school_capacity_tab(self):
        tab = self._tabview.add("School Capacity")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._sc_year = LabeledDropdown(controls, label="Year", values=YEAR_OPTIONS)
        self._sc_year.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkButton(
            controls, text="Refresh", command=self._refresh_school_capacity,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=100, height=35,
        ).pack(side="left", pady=(18, 0))

        self._sc_info = ctk.CTkLabel(
            tab, text="Student-to-teacher and student-to-classroom ratios per barangay",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._sc_info.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 3))

        columns = [
            {"key": "barangay_name", "title": "Barangay", "width": 3},
            {"key": "school_count", "title": "Schools", "width": 1},
            {"key": "total_enrollees", "title": "Enrollees", "width": 2},
            {"key": "teacher_count", "title": "Teachers", "width": 1},
            {"key": "classroom_count", "title": "Classrooms", "width": 1},
            {"key": "student_teacher_ratio", "title": "Student/Teacher", "width": 2},
            {"key": "student_classroom_ratio", "title": "Student/Classroom", "width": 2},
        ]
        self._sc_table = DataTable(tab, columns=columns)
        self._sc_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _refresh_school_capacity(self):
        year_str = self._sc_year.get()
        try:
            year_int = int(year_str)
        except ValueError:
            year_int = CURRENT_YEAR

        raw_data = get_education_stats_by_year(year_int)
        # Enrich with teacher/classroom counts by querying per-barangay
        enriched = []
        for row in raw_data:
            barangay_id = row["barangay_id"]
            brgy_records = get_education_statistics(barangay_id)
            year_rec = next((r for r in brgy_records if r["year"] == year_int), None)
            teacher_count = year_rec.get("teacher_count") if year_rec else None
            classroom_count = year_rec.get("classroom_count") if year_rec else None
            total_enrollees = row.get("total_enrollees") or 0

            if teacher_count and teacher_count > 0:
                student_teacher_ratio = f"{total_enrollees / teacher_count:.1f}"
            else:
                student_teacher_ratio = "N/A"

            if classroom_count and classroom_count > 0:
                student_classroom_ratio = f"{total_enrollees / classroom_count:.1f}"
            else:
                student_classroom_ratio = "N/A"

            enriched.append({
                "barangay_name": row["barangay_name"],
                "school_count": row["school_count"],
                "total_enrollees": total_enrollees,
                "teacher_count": teacher_count or 0,
                "classroom_count": classroom_count or 0,
                "student_teacher_ratio": student_teacher_ratio,
                "student_classroom_ratio": student_classroom_ratio,
            })

        self._sc_table.set_data(enriched)
        self._sc_info.configure(
            text=f"Showing {len(enriched)} barangay(s) for year {year_int}"
        )

    def refresh(self):
        pass
