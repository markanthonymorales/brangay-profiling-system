import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.stat_card import StatCard
from ui.components.data_table import DataTable
from ui.components.form_fields import LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from ui.dialogs.confirm_dialog import ConfirmDialog
from services.system_service import (
    create_backup, restore_backup, delete_backup, list_backups,
    run_integrity_checks, get_system_stats, get_error_log,
    get_last_auto_report,
)

STATUS_COLORS = {
    "pass": ACCENT_COLOR,
    "fail": DANGER_COLOR,
    "warning": WARNING_COLOR,
}

LEVEL_COLORS = {
    "INFO": TEXT_SECONDARY,
    "WARNING": WARNING_COLOR,
    "ERROR": DANGER_COLOR,
}


class SystemView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="System Monitoring",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_overview_tab()
        self._build_backups_tab()
        self._build_integrity_tab()
        self._build_logs_tab()

    # ── Tab 1: Overview ───────────────────────────────────────

    def _build_overview_tab(self):
        tab = self._tabview.add("Overview")

        # Stat cards
        cards = ctk.CTkFrame(tab, fg_color="transparent")
        cards.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 10))

        self._stat_cards = {}
        configs = [
            ("db_size", "Database Size", "\U0001F4BE", PRIMARY_COLOR),
            ("total_records", "Total Records", "\U0001F4CA", ACCENT_COLOR),
            ("last_backup", "Last Backup", "\U0001F4E6", WARNING_COLOR),
            ("backup_count", "Backups", "\U0001F5C4", "#7B1FA2"),
        ]
        for i, (key, title, icon, color) in enumerate(configs):
            card = StatCard(cards, title=title, icon=icon, color=color)
            card.pack(side="left", expand=True, fill="x", padx=(0 if i == 0 else 8, 0))
            self._stat_cards[key] = card

        # App start time
        self._start_label = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._start_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 10))

        # Table counts
        ctk.CTkLabel(tab, text="Record Counts by Table",
                     font=(FONT_FAMILY, 13, "bold"), text_color=TEXT_PRIMARY,
                     ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 5))

        columns = [
            {"key": "table", "title": "Table", "width": 3},
            {"key": "count", "title": "Records", "width": 1},
        ]
        self._counts_table = DataTable(tab, columns=columns)
        self._counts_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _refresh_overview(self):
        stats = get_system_stats()

        self._stat_cards["db_size"].set_value(f"{stats['db_size_mb']} MB")
        self._stat_cards["total_records"].set_value(f"{stats['total_records']:,}")
        self._stat_cards["last_backup"].set_value(stats["last_backup"] or "Never")
        self._stat_cards["backup_count"].set_value(str(stats["backup_count"]))
        auto_report = get_last_auto_report()
        auto_text = f"Last auto-report: {auto_report['created']} ({auto_report['filename']})" if auto_report else "Last auto-report: None"
        self._start_label.configure(text=f"App started: {stats['app_start_time']}  |  Log size: {stats['log_size_mb']} MB  |  {auto_text}")

        table_data = [
            {"table": name.replace("_", " ").title(), "count": count}
            for name, count in stats["table_counts"].items()
        ]
        self._counts_table.set_data(table_data)

    # ── Tab 2: Backups ────────────────────────────────────────

    def _build_backups_tab(self):
        tab = self._tabview.add("Backups")

        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 10))

        ctk.CTkButton(
            btn_frame, text="Backup Now", command=self._do_backup,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, width=130, height=35,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Refresh", command=self._refresh_backups,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=80, height=35,
        ).pack(side="left")

        self._backup_info = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._backup_info.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 5))

        columns = [
            {"key": "filename", "title": "Filename", "width": 4},
            {"key": "size_mb", "title": "Size (MB)", "width": 1},
            {"key": "created", "title": "Created", "width": 2},
        ]
        self._backup_table = DataTable(tab, columns=columns, on_row_click=self._on_backup_click)
        self._backup_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _do_backup(self):
        success, msg = create_backup()
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Backup", message=msg, dialog_type=dialog_type)
        self._refresh_backups()

    def _refresh_backups(self):
        backups = list_backups()
        self._backup_table.set_data(backups)
        self._backup_info.configure(text=f"{len(backups)} backup(s) stored")

    def _on_backup_click(self, row_data: dict):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Backup: {row_data['filename']}")
        dialog.geometry("420x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=row_data["filename"],
                     font=(FONT_FAMILY, 13, "bold"), text_color=TEXT_PRIMARY).pack(pady=(20, 5))
        ctk.CTkLabel(dialog, text=f"Size: {row_data['size_mb']} MB  |  Created: {row_data['created']}",
                     font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY).pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def do_restore():
            dialog.destroy()
            ConfirmDialog(
                self, title="Confirm Restore",
                message=f"Restore database from {row_data['filename']}?\nA safety backup will be created first.\nYou will need to restart the app after restore.",
                on_confirm=lambda: self._execute_restore(row_data["filename"]),
            )

        def do_delete():
            dialog.destroy()
            ConfirmDialog(
                self, title="Confirm Delete",
                message=f"Delete backup {row_data['filename']}? This cannot be undone.",
                on_confirm=lambda: self._execute_delete(row_data["filename"]),
            )

        ctk.CTkButton(btn_frame, text="Restore", command=do_restore,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=WARNING_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Delete", command=do_delete,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=DANGER_COLOR,
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Close", command=dialog.destroy,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color="gray",
                      text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    def _execute_restore(self, filename: str):
        success, msg = restore_backup(filename)
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Restore", message=msg, dialog_type=dialog_type)
        self._refresh_backups()

    def _execute_delete(self, filename: str):
        success, msg = delete_backup(filename)
        dialog_type = "success" if success else "error"
        MessageDialog(self, title="Delete Backup", message=msg, dialog_type=dialog_type)
        self._refresh_backups()

    # ── Tab 3: Integrity ──────────────────────────────────────

    def _build_integrity_tab(self):
        tab = self._tabview.add("Integrity")

        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 10))

        ctk.CTkButton(
            btn_frame, text="Run Integrity Check", command=self._run_checks,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=180, height=35,
        ).pack(side="left")

        self._check_summary = ctk.CTkLabel(
            tab, text="Click 'Run Integrity Check' to validate database health.",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._check_summary.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 5))

        self._check_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._check_frame.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _run_checks(self):
        for w in self._check_frame.winfo_children():
            w.destroy()

        results = run_integrity_checks()

        pass_count = sum(1 for r in results if r["status"] == "pass")
        fail_count = sum(1 for r in results if r["status"] == "fail")
        warn_count = sum(1 for r in results if r["status"] == "warning")
        self._check_summary.configure(
            text=f"{len(results)} checks: {pass_count} passed, {warn_count} warnings, {fail_count} failed",
        )

        for r in results:
            row = ctk.CTkFrame(self._check_frame, fg_color="#FAFAFA", corner_radius=8)
            row.pack(fill="x", pady=3)

            # Status icon
            status = r["status"]
            icon = {"pass": "\u2705", "fail": "\u274c", "warning": "\u26a0\ufe0f"}.get(status, "?")
            color = STATUS_COLORS.get(status, TEXT_SECONDARY)

            ctk.CTkLabel(
                row, text=icon, font=(FONT_FAMILY, 16), width=30,
            ).pack(side="left", padx=(PADDING_NORMAL, 5), pady=8)

            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True, pady=8)

            ctk.CTkLabel(
                text_frame, text=r["check"],
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w")

            ctk.CTkLabel(
                text_frame, text=r["details"],
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
            ).pack(anchor="w")

            ctk.CTkLabel(
                row, text=status.upper(),
                font=(FONT_FAMILY, 10, "bold"), text_color=color,
            ).pack(side="right", padx=PADDING_NORMAL)

    # ── Tab 4: Logs ───────────────────────────────────────────

    def _build_logs_tab(self):
        tab = self._tabview.add("Logs")

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._log_level = LabeledDropdown(
            controls, label="Level", values=["All", "INFO", "WARNING", "ERROR"],
        )
        self._log_level.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            controls, text="Refresh", command=self._refresh_logs,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=100, height=35,
        ).pack(side="left", pady=(18, 0))

        self._log_count = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._log_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(5, 3))

        self._log_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._log_frame.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _refresh_logs(self):
        for w in self._log_frame.winfo_children():
            w.destroy()

        level = self._log_level.get()
        level_filter = level if level != "All" else None
        entries = get_error_log(level=level_filter, limit=200)

        self._log_count.configure(text=f"Showing {len(entries)} log entries")

        if not entries:
            ctk.CTkLabel(
                self._log_frame, text="No log entries found.",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
            ).pack(pady=20)
            return

        for e in entries:
            row = ctk.CTkFrame(self._log_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)

            color = LEVEL_COLORS.get(e["level"], TEXT_SECONDARY)

            ctk.CTkLabel(
                row, text=f"[{e['level']}]",
                font=(FONT_FAMILY, 9, "bold"), text_color=color, width=60,
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=e["timestamp"][:19],
                font=(FONT_FAMILY, 9), text_color=TEXT_SECONDARY, width=140,
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=f"{e['source']}: {e['message']}",
                font=(FONT_FAMILY, 9), text_color=TEXT_PRIMARY,
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

    def refresh(self):
        self._refresh_overview()
        self._refresh_backups()
