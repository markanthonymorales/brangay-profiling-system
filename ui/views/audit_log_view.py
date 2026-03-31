import customtkinter as ctk
from datetime import datetime
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, WARNING_COLOR,
    TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.data_table import DataTable
from ui.components.form_fields import LabeledDropdown, LabeledEntry
from services.audit_service import get_audit_logs
from services.user_service import list_users


class AuditLogView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Audit Log",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Filters
        filter_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        filter_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        inner.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        # User filter
        users = list_users(include_inactive=True)
        user_names = ["All"] + [u["username"] for u in users]
        self._user_map = {u["username"]: u["id"] for u in users}

        self._user_filter = LabeledDropdown(inner, label="User", values=user_names)
        self._user_filter.pack(side="left", padx=(0, 10), fill="x", expand=True)

        # Action filter
        self._action_filter = LabeledDropdown(
            inner, label="Action", values=["All", "CREATE", "UPDATE", "DELETE"],
        )
        self._action_filter.pack(side="left", padx=(0, 10), fill="x", expand=True)

        # Table filter
        self._table_filter = LabeledDropdown(
            inner, label="Table", values=[
                "All", "users", "population_records", "income_data", "businesses",
                "utilities", "land_types", "waste_management",
                "food_sources", "government_facilities", "religious_demographics",
            ],
        )
        self._table_filter.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            inner, text="Filter", command=self._do_filter,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=80, height=35,
        ).pack(side="left", pady=(18, 0))

        # Count label
        self._count_label = ctk.CTkLabel(
            self, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._count_label.pack(anchor="w", padx=PADDING_LARGE, pady=(0, 5))

        # Table
        columns = [
            {"key": "timestamp", "title": "Timestamp", "width": 2},
            {"key": "username", "title": "User", "width": 1},
            {"key": "action", "title": "Action", "width": 1},
            {"key": "table_name", "title": "Table", "width": 2},
            {"key": "record_id", "title": "Record ID", "width": 1},
        ]
        self._table = DataTable(self, columns=columns, on_row_click=self._show_details)
        self._table.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

    def _do_filter(self):
        user_val = self._user_filter.get()
        user_id = self._user_map.get(user_val) if user_val != "All" else None

        action_val = self._action_filter.get()
        action = action_val if action_val != "All" else None

        table_val = self._table_filter.get()
        table_name = table_val if table_val != "All" else None

        logs = get_audit_logs(user_id=user_id, action=action,
                              table_name=table_name, limit=200)
        self._table.set_data(logs)
        self._count_label.configure(text=f"Showing {len(logs)} entries")

    def _show_details(self, row_data: dict):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Audit Log Details")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Audit Log Entry",
                     font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY).pack(pady=(15, 10))

        details = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        details.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        fields = [
            ("Timestamp", row_data.get("timestamp", "")),
            ("User", row_data.get("username", "")),
            ("Action", row_data.get("action", "")),
            ("Table", row_data.get("table_name", "")),
            ("Record ID", row_data.get("record_id", "")),
        ]

        for label, value in fields:
            row = ctk.CTkFrame(details, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{label}:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                         text_color=TEXT_PRIMARY, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(value), font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                         text_color=TEXT_SECONDARY).pack(side="left")

        if row_data.get("old_values"):
            ctk.CTkLabel(details, text="Old Values:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", pady=(10, 2))
            old_text = ctk.CTkTextbox(details, height=80, font=(FONT_FAMILY, FONT_SIZE_SMALL))
            old_text.pack(fill="x")
            old_text.insert("1.0", str(row_data["old_values"]))
            old_text.configure(state="disabled")

        if row_data.get("new_values"):
            ctk.CTkLabel(details, text="New Values:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", pady=(10, 2))
            new_text = ctk.CTkTextbox(details, height=80, font=(FONT_FAMILY, FONT_SIZE_SMALL))
            new_text.pack(fill="x")
            new_text.insert("1.0", str(row_data["new_values"]))
            new_text.configure(state="disabled")

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                      fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=100).pack(pady=10)

        dialog.after(100, dialog.focus_force)

    def refresh(self):
        self._do_filter()
