import customtkinter as ctk
from datetime import datetime, date
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.data_table import DataTable
from ui.components.form_fields import LabeledEntry, LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from auth.auth_manager import AuthManager
from services.governance_service import (
    VALID_STATUSES,
    get_decisions, get_decision, approve_decision, reject_decision,
    implement_decision, get_decision_summary,
)
from services.audit_service import get_audit_logs, get_recent_activity


class GovernanceView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._built_tabs = set()
        self._build_ui()

    def _get_user_id(self) -> int:
        user = self._auth.get_current_user()
        return user.id if user else 0

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Governance & Compliance",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12,
                                         command=self._on_tab_change)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._tabview.add("Pending Approvals")
        self._tabview.add("Decision Log")
        self._tabview.add("Compliance Report")
        self._tabview.add("Audit Trail")

        self._build_pending_tab()
        self._built_tabs.add("Pending Approvals")

    def _on_tab_change(self):
        current = self._tabview.get()
        if current in self._built_tabs:
            return
        self._built_tabs.add(current)
        if current == "Decision Log":
            self._build_decision_log_tab()
        elif current == "Compliance Report":
            self._build_compliance_tab()
        elif current == "Audit Trail":
            self._build_audit_trail_tab()

    # ── Tab 1: Pending Approvals ─────────────────────────────

    def _build_pending_tab(self):
        tab = self._tabview.tab("Pending Approvals")

        # Refresh button
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkButton(
            btn_frame, text="Refresh", command=self._load_pending,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=90, height=30,
        ).pack(side="left", padx=(0, 8))

        self._pending_count = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=TEXT_SECONDARY,
        )
        self._pending_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "id", "title": "ID", "width": 1},
            {"key": "decision_type", "title": "Type", "width": 2},
            {"key": "decider_name", "title": "Decider", "width": 2},
            {"key": "rationale", "title": "Rationale", "width": 3},
            {"key": "created_at", "title": "Created", "width": 2},
            {"key": "status", "title": "Status", "width": 1},
        ]
        self._pending_table = DataTable(tab, columns=columns, on_row_click=self._on_pending_row_click)
        self._pending_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        self._load_pending()

    def _load_pending(self):
        decisions = get_decisions(status="pending")
        self._pending_table.set_data(decisions)
        count = len(decisions)
        self._pending_count.configure(text=f"{count} decision(s) pending approval")

    def _on_pending_row_click(self, row_data: dict):
        decision_id = row_data.get("id")
        if not decision_id:
            return
        self._show_approval_dialog(decision_id)

    def _show_approval_dialog(self, decision_id: int):
        decision = get_decision(decision_id)
        if not decision:
            MessageDialog(self, "Error", "Decision not found.", "error")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Decision Approval")
        dialog.geometry("600x500")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=PADDING_LARGE)

        # Decision details
        ctk.CTkLabel(
            scroll, text=f"Decision #{decision['id']}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 10))

        info_items = [
            ("Type", decision.get("decision_type", "-")),
            ("Decider", decision.get("decider_name", "-")),
            ("Status", decision.get("status", "-")),
            ("Created", decision.get("created_at", "-")),
            ("Context", str(decision.get("context", "-"))),
            ("Options Considered", str(decision.get("options_considered", "-"))),
            ("Chosen Option", str(decision.get("chosen_option", "-"))),
            ("Rationale", decision.get("rationale", "-")),
        ]

        for label, value in info_items:
            frame = ctk.CTkFrame(scroll, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            ctk.CTkLabel(
                frame, text=f"{label}:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                text_color=TEXT_PRIMARY, width=120, anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                frame, text=str(value)[:200], font=(FONT_FAMILY, FONT_SIZE_SMALL),
                text_color=TEXT_SECONDARY, anchor="w", wraplength=400,
            ).pack(side="left", fill="x", expand=True)

        # Rejection reason (for reject action)
        ctk.CTkLabel(scroll, text="Rejection Reason (if rejecting):",
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_PRIMARY).pack(
            anchor="w", pady=(15, 5))
        reject_reason = ctk.CTkTextbox(scroll, height=80, font=(FONT_FAMILY, FONT_SIZE_SMALL))
        reject_reason.pack(fill="x", pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        def do_approve():
            user_id = self._get_user_id()
            success, msg = approve_decision(decision_id, user_id)
            dialog.destroy()
            MessageDialog(self, "Approve Decision", msg, "success" if success else "error")
            if success:
                self._load_pending()

        def do_reject():
            reason = reject_reason.get("1.0", "end").strip()
            if not reason:
                MessageDialog(self, "Error", "Rejection reason is required.", "error")
                return
            user_id = self._get_user_id()
            success, msg = reject_decision(decision_id, user_id, reason)
            dialog.destroy()
            MessageDialog(self, "Reject Decision", msg, "success" if success else "error")
            if success:
                self._load_pending()

        def do_implement():
            user_id = self._get_user_id()
            success, msg = implement_decision(decision_id, user_id)
            dialog.destroy()
            MessageDialog(self, "Implement Decision", msg, "success" if success else "error")
            if success:
                self._load_pending()

        ctk.CTkButton(
            btn_frame, text="Approve", command=do_approve,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=100,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Reject", command=do_reject,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=DANGER_COLOR,
            text_color=TEXT_LIGHT, width=100,
        ).pack(side="left", padx=(0, 8))

        if decision.get("status") == "approved":
            ctk.CTkButton(
                btn_frame, text="Mark Implemented", command=do_implement,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=ACCENT_COLOR,
                text_color=TEXT_LIGHT, width=140,
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Close", command=dialog.destroy,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color="grey",
            text_color=TEXT_LIGHT, width=100,
        ).pack(side="right")

    # ── Tab 2: Decision Log ──────────────────────────────────

    def _build_decision_log_tab(self):
        tab = self._tabview.tab("Decision Log")

        # Filters
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._dl_status = LabeledDropdown(
            controls, label="Status", values=["All"] + VALID_STATUSES,
        )
        self._dl_status.pack(side="left", padx=(0, 8), fill="x", expand=True)

        # Get decision types from service
        summary = get_decision_summary()
        type_list = list(summary.get("by_type", {}).keys()) if summary else []
        self._dl_type = LabeledDropdown(
            controls, label="Type", values=["All"] + type_list,
        )
        self._dl_type.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._dl_year = LabeledDropdown(
            controls, label="Year",
            values=["All"] + [str(y) for y in range(date.today().year, date.today().year - 6, -1)],
        )
        self._dl_year.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(
            btn_frame, text="Filter", command=self._load_decisions,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=70, height=30,
        ).pack(side="left", pady=(18, 0), padx=2)

        self._dl_count = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=TEXT_SECONDARY,
        )
        self._dl_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "id", "title": "ID", "width": 1},
            {"key": "decision_type", "title": "Type", "width": 2},
            {"key": "decider_name", "title": "Decider", "width": 2},
            {"key": "approver_name", "title": "Approver", "width": 2},
            {"key": "status", "title": "Status", "width": 1},
            {"key": "created_at", "title": "Created", "width": 2},
            {"key": "approved_at", "title": "Approved", "width": 2},
        ]
        self._dl_table = DataTable(tab, columns=columns, on_row_click=self._on_dl_row_click)
        self._dl_table.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        self._load_decisions()

    def _load_decisions(self):
        status = self._dl_status.get()
        decision_type = self._dl_type.get()
        status_filter = status if status != "All" else None
        type_filter = decision_type if decision_type != "All" else None

        decisions = get_decisions(
            status=status_filter,
            decision_type=type_filter,
            limit=200,
        )
        self._dl_table.set_data(decisions)
        count = len(decisions)
        self._dl_count.configure(text=f"{count} decision(s) found")

    def _on_dl_row_click(self, row_data: dict):
        decision_id = row_data.get("id")
        if not decision_id:
            return
        self._show_approval_dialog(decision_id)

    # ── Tab 3: Compliance Report ─────────────────────────────

    def _build_compliance_tab(self):
        tab = self._tabview.tab("Compliance Report")

        # Summary cards
        summary = get_decision_summary()
        if not summary:
            ctk.CTkLabel(
                tab, text="No compliance data available.",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
            ).pack(pady=50)
            return

        # Top stats
        stats_frame = ctk.CTkFrame(tab, fg_color="transparent")
        stats_frame.pack(fill="x", padx=PADDING_LARGE, pady=PADDING_LARGE)

        total = summary.get("total", 0)
        by_status = summary.get("by_status", {})
        by_type = summary.get("by_type", {})
        pending = summary.get("pending_approval", 0)

        # Create stat cards
        self._create_stat_card(stats_frame, "Total Decisions", str(total), PRIMARY_COLOR)
        self._create_stat_card(stats_frame, "Pending Approval", str(pending), WARNING_COLOR)
        self._create_stat_card(stats_frame, "Approved", str(by_status.get("approved", 0)), PRIMARY_COLOR)
        self._create_stat_card(stats_frame, "Implemented", str(by_status.get("implemented", 0)), ACCENT_COLOR)
        self._create_stat_card(stats_frame, "Cancelled", str(by_status.get("cancelled", 0)), DANGER_COLOR)

        # By Status breakdown
        status_frame = ctk.CTkFrame(tab, fg_color=CARD_BG, corner_radius=12)
        status_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            status_frame, text="Decisions by Status",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        for status, count in by_status.items():
            row = ctk.CTkFrame(status_frame, fg_color="transparent")
            row.pack(fill="x", padx=PADDING_NORMAL, pady=2)
            ctk.CTkLabel(
                row, text=f"{status}:", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                text_color=TEXT_PRIMARY, width=100, anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=str(count), font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                text_color=TEXT_PRIMARY,
            ).pack(side="left")

        # By Type breakdown
        type_frame = ctk.CTkFrame(tab, fg_color=CARD_BG, corner_radius=12)
        type_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            type_frame, text="Decisions by Type",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        for dtype, count in by_type.items():
            row = ctk.CTkFrame(type_frame, fg_color="transparent")
            row.pack(fill="x", padx=PADDING_NORMAL, pady=2)
            ctk.CTkLabel(
                row, text=f"{dtype}:", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                text_color=TEXT_PRIMARY, width=200, anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=str(count), font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                text_color=TEXT_PRIMARY,
            ).pack(side="left")

        # Recent activity
        activity_frame = ctk.CTkFrame(tab, fg_color=CARD_BG, corner_radius=12)
        activity_frame.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        ctk.CTkLabel(
            activity_frame, text="Recent Activity (Last 20)",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        recent = get_recent_activity(limit=20)
        if recent:
            for entry in recent[:10]:  # Show first 10
                row = ctk.CTkFrame(activity_frame, fg_color="transparent")
                row.pack(fill="x", padx=PADDING_NORMAL, pady=1)
                ctk.CTkLabel(
                    row, text=f"{entry.get('timestamp', '')[:16]}",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL),
                    text_color=TEXT_SECONDARY, width=120, anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    row, text=f"{entry.get('action', '')} on {entry.get('table_name', '')}",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL),
                    text_color=TEXT_PRIMARY, anchor="w",
                ).pack(side="left", fill="x", expand=True)
        else:
            ctk.CTkLabel(
                activity_frame, text="No recent activity.",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
            ).pack(padx=PADDING_NORMAL, pady=5)

    def _create_stat_card(self, parent, title: str, value: str, color: str):
        card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=10, height=80)
        card.pack(side="left", fill="x", expand=True, padx=(0, 5))
        card.pack_propagate(False)

        ctk.CTkLabel(
            card, text=value,
            font=(FONT_FAMILY, 28, "bold"), text_color=color,
        ).pack(expand=True)
        ctk.CTkLabel(
            card, text=title,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 8))

    # ── Tab 4: Audit Trail ────────────────────────────────────

    def _build_audit_trail_tab(self):
        tab = self._tabview.tab("Audit Trail")

        # Filters
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        # Get unique table names from audit logs
        logs_sample = get_audit_logs(limit=500)
        table_names = sorted(set(l.get("table_name", "") for l in logs_sample if l.get("table_name")))
        action_types = sorted(set(l.get("action", "") for l in logs_sample if l.get("action")))

        self._at_table = LabeledDropdown(
            controls, label="Table", values=["All"] + table_names,
        )
        self._at_table.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._at_action = LabeledDropdown(
            controls, label="Action", values=["All"] + action_types,
        )
        self._at_action.pack(side="left", padx=(0, 8), fill="x", expand=True)

        self._at_limit = LabeledDropdown(
            controls, label="Limit", values=["50", "100", "200", "500"],
        )
        self._at_limit.set("100")
        self._at_limit.pack(side="left", padx=(0, 8), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(side="left", padx=(0, 0))

        ctk.CTkButton(
            btn_frame, text="Filter", command=self._load_audit_logs,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=70, height=30,
        ).pack(side="left", pady=(18, 0), padx=2)

        self._at_count = ctk.CTkLabel(
            tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=TEXT_SECONDARY,
        )
        self._at_count.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        columns = [
            {"key": "id", "title": "ID", "width": 1},
            {"key": "timestamp", "title": "Timestamp", "width": 2},
            {"key": "username", "title": "User", "width": 2},
            {"key": "action", "title": "Action", "width": 1},
            {"key": "table_name", "title": "Table", "width": 2},
            {"key": "record_id", "title": "Record ID", "width": 1},
            {"key": "old_values", "title": "Old Values", "width": 3},
            {"key": "new_values", "title": "New Values", "width": 3},
        ]
        self._at_table_grid = DataTable(tab, columns=columns)
        self._at_table_grid.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        self._load_audit_logs()

    def _load_audit_logs(self):
        table_name = self._at_table.get()
        action = self._at_action.get()
        limit = int(self._at_limit.get())

        table_filter = table_name if table_name != "All" else None
        action_filter = action if action != "All" else None

        logs = get_audit_logs(
            table_name=table_filter,
            action=action_filter,
            limit=limit,
        )

        # Truncate long JSON values for display
        for log in logs:
            old = log.get("old_values")
            new = log.get("new_values")
            if old and isinstance(old, dict):
                log["old_values"] = str(old)[:100]
            if new and isinstance(new, dict):
                log["new_values"] = str(new)[:100]

        self._at_table_grid.set_data(logs)
        count = len(logs)
        self._at_count.configure(text=f"{count} log(s) found")

    # ── Public refresh method ─────────────────────────────────

    def refresh(self):
        current = self._tabview.get()
        if current == "Pending Approvals":
            self._load_pending()
        elif current == "Decision Log":
            self._load_decisions()
        elif current == "Audit Trail":
            self._load_audit_logs()
