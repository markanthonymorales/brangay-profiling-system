import customtkinter as ctk
from datetime import date
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
from services.business_permit_service import (
    PERMIT_STATUSES, BUSINESS_TYPES,
    save_business_permit, delete_business_permit, get_business_permits,
    get_permit_stats, get_expiring_permits,
)

COLORS = {
    "blue": "#1E88E5", "green": "#43A047", "orange": "#FB8C00",
    "red": "#E53935", "purple": "#7B1FA2", "pink": "#E91E63",
    "teal": "#00897B", "yellow": "#FDD835", "grey": "#757575",
    "cyan": "#00ACC1", "lime": "#C0CA33",
}

TYPE_COLORS = [
    COLORS["blue"], COLORS["green"], COLORS["orange"], COLORS["red"],
    COLORS["purple"], COLORS["pink"], COLORS["teal"], COLORS["yellow"],
    COLORS["cyan"], COLORS["lime"],
]

STATUS_COLORS = {
    "active": COLORS["green"],
    "expired": COLORS["red"],
    "revoked": COLORS["orange"],
    "pending": COLORS["yellow"],
}


class BusinessPermitView(ctk.CTkFrame):
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
            self, text="Business Permits",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12,
                                        command=self._on_tab_change)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._built_tabs = set()

        self._tabview.add("Permits")
        self._tabview.add("Permit Overview")
        self._tabview.add("Expiring Permits")

        self._build_permits_tab()
        self._built_tabs.add("Permits")

    def _on_tab_change(self):
        current = self._tabview.get()
        if current in self._built_tabs:
            return
        self._built_tabs.add(current)
        if current == "Permit Overview":
            self._build_overview_tab()
        elif current == "Expiring Permits":
            self._build_expiring_tab()

    # ── Tab 1: Permits ────────────────────────────────────────

    def _build_permits_tab(self):
        tab = self._tabview.tab("Permits")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        district_names = [d["name"] for d in self._districts]
        self._p_district = LabeledDropdown(controls, label="District", values=["All"] + district_names,
                                           command=self._on_p_district_change)
        self._p_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._p_barangay = LabeledDropdown(controls, label="Barangay", values=["All"])
        self._p_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._p_type = LabeledDropdown(controls, label="Type", values=["All"] + BUSINESS_TYPES)
        self._p_type.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._p_status = LabeledDropdown(controls, label="Status", values=["All"] + PERMIT_STATUSES)
        self._p_status.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(btn_frame, text="Filter", command=self._filter_permits,
                      font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        if self._auth.check_permission("enter_data"):
            ctk.CTkButton(btn_frame, text="+ Add", command=self._add_permit_dialog,
                          font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=ACCENT_COLOR,
                          text_color=TEXT_LIGHT, width=70, height=30).pack(side="left", pady=(18, 0), padx=2)

        self._p_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                     text_color=TEXT_SECONDARY)
        self._p_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "business_name", "title": "Business Name", "width": 2},
            {"key": "owner_name", "title": "Owner", "width": 2},
            {"key": "business_type", "title": "Type", "width": 1},
            {"key": "permit_number", "title": "Permit No.", "width": 1},
            {"key": "status", "title": "Status", "width": 1},
            {"key": "date_expiry", "title": "Expiry", "width": 1},
        ]
        self._p_table = DataTable(tab, columns=columns, on_row_click=self._on_permit_row_click)
        self._p_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _on_p_district_change(self, district_name: str):
        if district_name == "All":
            self._p_barangay.set_values(["All"])
            self._p_barangay.set("All")
        else:
            brgy_map = self._load_barangays(district_name)
            self._p_barangay.set_values(["All"] + list(brgy_map.keys()))
            self._p_barangay.set("All")

    def _filter_permits(self):
        district = self._p_district.get()
        brgy_name = self._p_barangay.get()
        b_type = self._p_type.get()
        status = self._p_status.get()

        barangay_id = None
        if brgy_name != "All" and district != "All":
            brgy_map = self._load_barangays(district)
            barangay_id = brgy_map.get(brgy_name)

        data = get_business_permits(
            barangay_id=barangay_id,
            business_type=b_type if b_type != "All" else None,
            status=status if status != "All" else None,
        )
        self._p_table.set_data(data)
        self._p_count.configure(text=f"Showing {len(data)} permit(s)")

    def _add_permit_dialog(self):
        self._permit_dialog()

    def _on_permit_row_click(self, row_data):
        self._permit_dialog(row_data)

    # ── Permit Dialog ─────────────────────────────────────────

    def _permit_dialog(self, existing: dict | None = None):
        is_edit = existing is not None
        title = "Edit Business Permit" if is_edit else "Add Business Permit"

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

        d_business_name = LabeledEntry(scroll, label="Business Name", required=True)
        d_business_name.pack(fill="x", pady=2)

        d_owner_name = LabeledEntry(scroll, label="Owner Name", required=True)
        d_owner_name.pack(fill="x", pady=2)

        d_business_type = LabeledDropdown(scroll, label="Business Type", values=BUSINESS_TYPES)
        d_business_type.pack(fill="x", pady=2)

        d_permit_number = LabeledEntry(scroll, label="Permit Number")
        d_permit_number.pack(fill="x", pady=2)

        d_date_issued = LabeledEntry(scroll, label="Date Issued (YYYY-MM-DD)",
                                     placeholder=date.today().strftime("%Y-%m-%d"))
        d_date_issued.set(date.today().strftime("%Y-%m-%d"))
        d_date_issued.pack(fill="x", pady=2)

        d_date_expiry = LabeledEntry(scroll, label="Date Expiry (YYYY-MM-DD)",
                                     placeholder=date.today().strftime("%Y-%m-%d"))
        d_date_expiry.pack(fill="x", pady=2)

        d_status = LabeledDropdown(scroll, label="Status", values=PERMIT_STATUSES)
        d_status.pack(fill="x", pady=2)

        d_revenue = LabeledNumberEntry(scroll, label="Annual Revenue")
        d_revenue.pack(fill="x", pady=2)

        d_employees = LabeledNumberEntry(scroll, label="Employee Count")
        d_employees.pack(fill="x", pady=2)

        d_address = LabeledEntry(scroll, label="Address")
        d_address.pack(fill="x", pady=2)

        # Pre-fill for edit
        if is_edit:
            edit_district = existing.get("district_name", "")
            edit_barangay = existing.get("barangay_name", "")
            # Try to find the district for this barangay
            if not edit_district:
                for dn in district_names:
                    brgy_map = self._load_barangays(dn)
                    if edit_barangay in brgy_map:
                        edit_district = dn
                        break
            if edit_district and edit_district in district_names:
                d_district.set(edit_district)
                on_district_sel(edit_district)
                if edit_barangay:
                    d_barangay.set(edit_barangay)

            d_business_name.set(existing.get("business_name", ""))
            d_owner_name.set(existing.get("owner_name", ""))
            d_business_type.set(existing.get("business_type", BUSINESS_TYPES[0]))
            d_permit_number.set(existing.get("permit_number", ""))
            d_date_issued.set(existing.get("date_issued", ""))
            d_date_expiry.set(existing.get("date_expiry", ""))
            d_status.set(existing.get("status", PERMIT_STATUSES[0]))
            revenue = existing.get("annual_revenue", "")
            d_revenue.set(str(revenue) if revenue else "")
            employees = existing.get("employee_count", "")
            d_employees.set(str(employees) if employees else "")
            d_address.set(existing.get("address", ""))

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

            business_name = d_business_name.get()
            if not business_name:
                error_label.configure(text="Business name is required.")
                return

            owner_name = d_owner_name.get()
            if not owner_name:
                error_label.configure(text="Owner name is required.")
                return

            # Parse dates
            date_issued_val = None
            date_issued_str = d_date_issued.get()
            if date_issued_str:
                try:
                    date_issued_val = date.fromisoformat(date_issued_str)
                except ValueError:
                    error_label.configure(text="Invalid date issued format. Use YYYY-MM-DD.")
                    return

            date_expiry_val = None
            date_expiry_str = d_date_expiry.get()
            if date_expiry_str:
                try:
                    date_expiry_val = date.fromisoformat(date_expiry_str)
                except ValueError:
                    error_label.configure(text="Invalid date expiry format. Use YYYY-MM-DD.")
                    return

            data = {
                "business_name": business_name,
                "owner_name": owner_name,
                "business_type": d_business_type.get() or None,
                "permit_number": d_permit_number.get() or None,
                "date_issued": date_issued_val,
                "date_expiry": date_expiry_val,
                "status": d_status.get(),
                "annual_revenue": d_revenue.get_float(default=None),
                "employee_count": d_employees.get_int(default=None),
                "address": d_address.get() or None,
            }
            if is_edit:
                data["id"] = existing["id"]

            success, msg = save_business_permit(brgy_id, data, self._get_user_id())
            if success:
                dialog.destroy()
                self._filter_permits()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(btn_frame, text="Save", command=do_save,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        if is_edit and self._auth.check_permission("delete_data"):
            def do_delete():
                success, msg = delete_business_permit(existing["id"], self._get_user_id())
                dialog.destroy()
                self._filter_permits()
                dt = "success" if success else "error"
                MessageDialog(self, title="Delete", message=msg, dialog_type=dt)

            ctk.CTkButton(btn_frame, text="Delete", command=do_delete,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=DANGER_COLOR,
                          text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    # ── Tab 2: Permit Overview ────────────────────────────────

    def _build_overview_tab(self):
        tab = self._tabview.tab("Permit Overview")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._ov_scope = LabeledDropdown(controls, label="Scope",
                                         values=["City-Wide", "By District", "By Barangay"])
        self._ov_scope.pack(side="left", padx=(0, 8), fill="x", expand=True)

        district_names = [d["name"] for d in self._districts]
        self._ov_district = LabeledDropdown(controls, label="District", values=district_names,
                                            command=self._on_ov_district_change)
        self._ov_district.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._ov_barangay = LabeledDropdown(controls, label="Barangay", values=[])
        self._ov_barangay.pack(side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkButton(controls, text="Update", command=self._update_overview,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", pady=(18, 0))

        self._ov_chart = ChartWidget(tab, figsize=(9, 5))
        self._ov_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _on_ov_district_change(self, dn):
        brgy_map = self._load_barangays(dn)
        names = list(brgy_map.keys())
        self._ov_barangay.set_values(names)
        if names:
            self._ov_barangay.set(names[0])

    def _update_overview(self):
        scope = self._ov_scope.get()
        barangay_id = None
        district_id = None

        if scope == "By District":
            district_id = self._district_map.get(self._ov_district.get())
        elif scope == "By Barangay":
            dn = self._ov_district.get()
            brgy_map = self._load_barangays(dn)
            barangay_id = brgy_map.get(self._ov_barangay.get())

        stats = get_permit_stats(barangay_id=barangay_id, district_id=district_id)

        if stats["total"] == 0:
            self._ov_chart.update_chart(lambda fig, ax: ax.text(
                0.5, 0.5, "No permit data available for this selection.",
                ha="center", va="center", fontsize=12, color="#999999", transform=ax.transAxes))
            return

        def draw(fig):
            # Top-left: permits by type (pie)
            ax1 = fig.add_subplot(131)
            by_type = {k: v for k, v in stats["by_type"].items() if k}
            if by_type:
                labels = list(by_type.keys())
                values = list(by_type.values())
                colors = TYPE_COLORS[:len(labels)]
                ax1.pie(values, labels=labels, colors=colors, autopct="%1.0f%%",
                        textprops={"fontsize": 7})
                ax1.set_title("Permits by Type", fontsize=10)
            else:
                ax1.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax1.transAxes)

            # Top-middle: revenue by type (bar)
            ax2 = fig.add_subplot(132)
            by_status = {k: v for k, v in stats["by_status"].items() if k}
            if by_status:
                s_labels = list(by_status.keys())
                s_values = list(by_status.values())
                s_colors = [STATUS_COLORS.get(s, COLORS["grey"]) for s in s_labels]
                ax2.bar(s_labels, s_values, color=s_colors)
                ax2.set_title("By Status", fontsize=10)
                ax2.set_ylabel("Count")
                ax2.tick_params(axis="x", rotation=30, labelsize=7)
            else:
                ax2.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax2.transAxes)

            # Top-right: active vs expired vs other (donut)
            ax3 = fig.add_subplot(133)
            active = stats["by_status"].get("active", 0)
            expired = stats["by_status"].get("expired", 0)
            other = stats["total"] - active - expired
            donut_labels = []
            donut_values = []
            donut_colors = []
            if active:
                donut_labels.append("Active")
                donut_values.append(active)
                donut_colors.append(COLORS["green"])
            if expired:
                donut_labels.append("Expired")
                donut_values.append(expired)
                donut_colors.append(COLORS["red"])
            if other > 0:
                donut_labels.append("Other")
                donut_values.append(other)
                donut_colors.append(COLORS["orange"])
            if donut_values:
                ax3.pie(donut_values, labels=donut_labels, colors=donut_colors,
                        autopct="%1.0f%%", wedgeprops=dict(width=0.4),
                        textprops={"fontsize": 7})
                ax3.set_title("Status Breakdown", fontsize=10)
            else:
                ax3.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax3.transAxes)

            fig.subplots_adjust(hspace=0.4, wspace=0.5, top=0.9, bottom=0.1, left=0.05, right=0.95)

        self._ov_chart.update_chart_multi(draw)

    # ── Tab 3: Expiring Permits ───────────────────────────────

    def _build_expiring_tab(self):
        tab = self._tabview.tab("Expiring Permits")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._exp_window = LabeledDropdown(controls, label="Expiry Window",
                                           values=["30 days", "60 days", "90 days"])
        self._exp_window.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(controls, text="Refresh", command=self._refresh_expiring,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", pady=(18, 0))

        self._exp_count = ctk.CTkLabel(tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                       text_color=TEXT_SECONDARY)
        self._exp_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "business_name", "title": "Business Name", "width": 2},
            {"key": "owner_name", "title": "Owner", "width": 2},
            {"key": "permit_number", "title": "Permit No.", "width": 1},
            {"key": "date_expiry", "title": "Expiry Date", "width": 1},
            {"key": "is_expired", "title": "Expired?", "width": 1},
        ]
        self._exp_table = DataTable(tab, columns=columns)
        self._exp_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _refresh_expiring(self):
        window_str = self._exp_window.get()
        days = int(window_str.split()[0])
        data = get_expiring_permits(days_ahead=days)
        # Convert bool to readable string for display
        for row in data:
            row["is_expired"] = "Yes" if row["is_expired"] else "No"
        self._exp_table.set_data(data)
        self._exp_count.configure(text=f"Showing {len(data)} permit(s) expiring within {days} days")

    def refresh(self):
        pass
