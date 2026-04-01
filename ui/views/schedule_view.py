import customtkinter as ctk
from datetime import date
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, WARNING_COLOR,
    SUCCESS_COLOR, DANGER_COLOR, TEXT_LIGHT,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from ui.dialogs.message_dialog import MessageDialog
from auth.auth_manager import AuthManager
from services.schedule_service import (
    create_schedule, get_all_schedules, update_schedule,
    get_compliance_dashboard, check_overdue_and_notify,
)


class ScheduleView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Data Collection",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_schedules_tab(self._tabview.add("Schedules"))
        self._build_compliance_tab(self._tabview.add("Compliance"))

    # ── Tab 1: Schedules ─────────────────────────────────────

    def _build_schedules_tab(self, tab):
        # Create form
        form = ctk.CTkFrame(tab, fg_color="#F5F5F5", corner_radius=8)
        form.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        ctk.CTkLabel(form, text="Create New Schedule", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(row, text="Year:", font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(side="left", padx=(0, 3))
        self._year_entry = ctk.CTkEntry(row, width=80, font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self._year_entry.insert(0, str(date.today().year))
        self._year_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row, text="Start:", font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(side="left", padx=(0, 3))
        self._start_entry = ctk.CTkEntry(row, width=110, placeholder_text="YYYY-MM-DD",
                                          font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self._start_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row, text="End:", font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(side="left", padx=(0, 3))
        self._end_entry = ctk.CTkEntry(row, width=110, placeholder_text="YYYY-MM-DD",
                                        font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self._end_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(row, text="Create", command=self._create_schedule,
                       font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=80, height=30,
                       ).pack(side="left")

        # Schedule list
        self._schedule_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._schedule_list.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _create_schedule(self):
        try:
            year = int(self._year_entry.get())
        except ValueError:
            MessageDialog(self, title="Error", message="Invalid year.", dialog_type="error")
            return

        try:
            parts = self._start_entry.get().split("-")
            start = date(int(parts[0]), int(parts[1]), int(parts[2]))
            parts = self._end_entry.get().split("-")
            end = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            MessageDialog(self, title="Error", message="Invalid date format. Use YYYY-MM-DD.", dialog_type="error")
            return

        user = self._auth.get_current_user()
        if not user:
            return

        success, msg = create_schedule(year, start, end, user.id)
        if success:
            MessageDialog(self, title="Success", message=msg, dialog_type="success")
            self._refresh_schedule_list()
        else:
            MessageDialog(self, title="Error", message=msg, dialog_type="error")

    def _refresh_schedule_list(self):
        for w in self._schedule_list.winfo_children():
            w.destroy()

        schedules = get_all_schedules()
        if not schedules:
            ctk.CTkLabel(self._schedule_list, text="No schedules created yet.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=20)
            return

        for sched in schedules:
            row = ctk.CTkFrame(self._schedule_list, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=3)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(fill="x", padx=PADDING_NORMAL, pady=8)

            status_colors = {"upcoming": PRIMARY_COLOR, "active": SUCCESS_COLOR, "closed": TEXT_SECONDARY}
            ctk.CTkLabel(
                info, text=sched["status"].upper(),
                font=(FONT_FAMILY, 9, "bold"), text_color=TEXT_LIGHT,
                fg_color=status_colors.get(sched["status"], TEXT_SECONDARY),
                corner_radius=4, padx=6, pady=2,
            ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                info, text=f"{sched['year']}  |  {sched['start_date']} to {sched['end_date']}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(side="left")

            if sched["notes"]:
                ctk.CTkLabel(
                    info, text=f"  ({sched['notes']})",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
                ).pack(side="left")

            if sched["status"] != "closed":
                user = self._auth.get_current_user()

                def close_sched(sid=sched["id"], uid=user.id if user else 0):
                    update_schedule(sid, uid, status="closed")
                    self._refresh_schedule_list()

                ctk.CTkButton(
                    info, text="Close", command=close_sched,
                    font=(FONT_FAMILY, FONT_SIZE_SMALL),
                    fg_color=DANGER_COLOR, text_color=TEXT_LIGHT, width=60, height=26,
                ).pack(side="right")

            if sched["status"] == "upcoming":
                user = self._auth.get_current_user()

                def activate_sched(sid=sched["id"], uid=user.id if user else 0):
                    update_schedule(sid, uid, status="active")
                    self._refresh_schedule_list()

                ctk.CTkButton(
                    info, text="Activate", command=activate_sched,
                    font=(FONT_FAMILY, FONT_SIZE_SMALL),
                    fg_color=SUCCESS_COLOR, text_color=TEXT_LIGHT, width=70, height=26,
                ).pack(side="right", padx=(0, 5))

    # ── Tab 2: Compliance ────────────────────────────────────

    def _build_compliance_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        ctk.CTkLabel(ctrl, text="Year:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(0, 5))

        self._compliance_year = ctk.CTkEntry(ctrl, width=80, font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self._compliance_year.insert(0, str(date.today().year))
        self._compliance_year.pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Load", command=self._load_compliance,
                       font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=80, height=30,
                       ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Send Overdue Reminders", command=self._send_reminders,
                       font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                       fg_color=WARNING_COLOR, text_color=TEXT_LIGHT, width=170, height=30,
                       ).pack(side="left")

        self._show_incomplete_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ctrl, text="Show only incomplete", variable=self._show_incomplete_var,
                        command=self._load_compliance,
                        font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(side="left", padx=(15, 0))

        # Progress bar
        self._progress_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self._progress_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 5))

        self._progress_bar = ctk.CTkProgressBar(self._progress_frame, width=400, height=16)
        self._progress_bar.set(0)
        self._progress_bar.pack(side="left", padx=(0, 10))

        self._progress_label = ctk.CTkLabel(self._progress_frame, text="0/0 (0%)",
                                             font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                                             text_color=TEXT_PRIMARY)
        self._progress_label.pack(side="left")

        # Compliance table
        self._compliance_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._compliance_list.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _load_compliance(self):
        try:
            year = int(self._compliance_year.get())
        except ValueError:
            return

        data = get_compliance_dashboard(year)

        # Update progress
        total = data["total_barangays"]
        complete = data["complete_count"]
        rate = data["completion_rate_pct"]
        self._progress_bar.set(rate / 100 if total > 0 else 0)
        self._progress_label.configure(text=f"{complete}/{total} ({rate}%)")

        # Render table
        for w in self._compliance_list.winfo_children():
            w.destroy()

        if not data["barangays"]:
            ctk.CTkLabel(self._compliance_list,
                         text=f"No submission tracking data for {year}. Create a schedule first.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=20)
            return

        show_incomplete = self._show_incomplete_var.get()

        for brgy in data["barangays"]:
            if show_incomplete and brgy["is_complete"]:
                continue

            row = ctk.CTkFrame(self._compliance_list, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=2)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(fill="x", padx=PADDING_NORMAL, pady=6)

            # Completion badge
            if brgy["is_complete"]:
                ctk.CTkLabel(
                    info, text="COMPLETE", font=(FONT_FAMILY, 9, "bold"),
                    text_color=TEXT_LIGHT, fg_color=SUCCESS_COLOR,
                    corner_radius=4, padx=6, pady=2,
                ).pack(side="left", padx=(0, 8))
            else:
                ctk.CTkLabel(
                    info, text="INCOMPLETE", font=(FONT_FAMILY, 9, "bold"),
                    text_color=TEXT_LIGHT, fg_color=WARNING_COLOR,
                    corner_radius=4, padx=6, pady=2,
                ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                info, text=f"{brgy['name']}  ({brgy['district_name']})",
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(side="left")

            # Status icons
            checks = ctk.CTkFrame(info, fg_color="transparent")
            checks.pack(side="right")

            for col, label in [
                ("population_submitted", "Pop"),
                ("income_submitted", "Inc"),
                ("utilities_submitted", "Util"),
                ("crime_submitted", "Crime"),
                ("waste_submitted", "Waste"),
            ]:
                submitted = brgy[col]
                icon = "\u2713" if submitted else "\u2717"
                color = SUCCESS_COLOR if submitted else DANGER_COLOR
                ctk.CTkLabel(
                    checks, text=f"{label}:{icon}",
                    font=(FONT_FAMILY, 10), text_color=color,
                ).pack(side="left", padx=3)

    def _send_reminders(self):
        user = self._auth.get_current_user()
        if not user:
            return
        count = check_overdue_and_notify(user.id)
        MessageDialog(self, title="Reminders Sent",
                      message=f"Created {count} overdue notifications.",
                      dialog_type="success" if count > 0 else "info")

    def refresh(self):
        self._refresh_schedule_list()
        self._load_compliance()
