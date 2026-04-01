import json
import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.data_table import DataTable
from ui.components.form_fields import LabeledDropdown, LabeledEntry
from ui.dialogs.message_dialog import MessageDialog
from ui.dialogs.confirm_dialog import ConfirmDialog
from auth.auth_manager import AuthManager
from services.submission_service import (
    list_submissions, approve_submission, reject_submission,
    get_submission_detail, get_pending_count,
)

STATUS_COLORS = {
    "pending": WARNING_COLOR,
    "approved": ACCENT_COLOR,
    "rejected": DANGER_COLOR,
    "draft": TEXT_SECONDARY,
}


class SubmissionsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        ctk.CTkLabel(
            header, text="Submissions",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left")

        self._pending_badge = ctk.CTkLabel(
            header, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            text_color=TEXT_LIGHT, fg_color=WARNING_COLOR, corner_radius=10, padx=8, pady=2,
        )
        self._pending_badge.pack(side="left", padx=10)

        # Filters
        filter_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        filter_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        inner.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        self._status_filter = LabeledDropdown(
            inner, label="Status", values=["All", "pending", "approved", "rejected"],
        )
        self._status_filter.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            inner, text="Filter", command=self._load_data,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, width=80, height=35,
        ).pack(side="left", pady=(18, 0))

        # Table
        columns = [
            {"key": "id", "title": "#", "width": 1},
            {"key": "submitter_name", "title": "Submitted By", "width": 2},
            {"key": "table_name", "title": "Data Type", "width": 2},
            {"key": "barangay_name", "title": "Barangay", "width": 2},
            {"key": "year", "title": "Year", "width": 1},
            {"key": "status", "title": "Status", "width": 1},
            {"key": "created_at", "title": "Submitted", "width": 2},
            {"key": "reviewer_name", "title": "Reviewed By", "width": 2},
        ]
        self._table = DataTable(self, columns=columns, on_row_click=self._on_row_click)
        self._table.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

    def _load_data(self):
        status = self._status_filter.get()
        status_filter = status if status != "All" else None
        data = list_submissions(status=status_filter)
        self._table.set_data(data)

        pending = get_pending_count()
        self._pending_badge.configure(
            text=f"{pending} pending" if pending > 0 else "No pending",
            fg_color=WARNING_COLOR if pending > 0 else ACCENT_COLOR,
        )

    def _on_row_click(self, row_data: dict):
        detail = get_submission_detail(row_data["id"])
        if not detail:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Submission #{detail['id']}")
        dialog.geometry("550x500")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        # Header
        ctk.CTkLabel(dialog, text=f"Submission #{detail['id']}",
                     font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY).pack(pady=(15, 5))

        status_color = STATUS_COLORS.get(detail["status"], TEXT_SECONDARY)
        ctk.CTkLabel(dialog, text=detail["status"].upper(),
                     font=(FONT_FAMILY, 11, "bold"), text_color=TEXT_LIGHT,
                     fg_color=status_color, corner_radius=4, padx=8, pady=2).pack(pady=(0, 10))

        # Info
        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 5))

        info_fields = [
            ("Submitted By", detail["submitter_name"]),
            ("Data Type", detail["table_name"].replace("_", " ").title()),
            ("Barangay", detail["barangay_name"]),
            ("Year", str(detail["year"]) if detail["year"] else "N/A"),
            ("Submitted", detail["created_at"]),
        ]

        if detail["reviewer_name"]:
            info_fields.append(("Reviewed By", detail["reviewer_name"]))
            info_fields.append(("Reviewed At", detail["reviewed_at"]))
        if detail["review_notes"]:
            info_fields.append(("Notes", detail["review_notes"]))

        for label, value in info_fields:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{label}:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                         text_color=TEXT_PRIMARY, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(value), font=(FONT_FAMILY, FONT_SIZE_SMALL),
                         text_color=TEXT_SECONDARY).pack(side="left")

        # Data preview
        ctk.CTkLabel(scroll, text="Submitted Data:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(10, 3))

        data_text = ctk.CTkTextbox(scroll, height=100, font=(FONT_FAMILY, 10))
        data_text.pack(fill="x")
        data_text.insert("1.0", json.dumps(detail["record_data"], indent=2))
        data_text.configure(state="disabled")

        # Action buttons (only for pending submissions)
        if detail["status"] == "pending" and self._auth.check_permission("approve_submissions"):
            notes_entry = LabeledEntry(dialog, label="Review Notes (optional)")
            notes_entry.pack(fill="x", padx=20, pady=(5, 5))

            action_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            action_frame.pack(pady=(0, 15))

            def do_approve():
                success, msg = approve_submission(detail["id"],
                                                   self._auth.get_current_user().id,
                                                   notes_entry.get())
                dialog.destroy()
                self._load_data()
                MessageDialog(self, title="Approve", message=msg,
                              dialog_type="success" if success else "error")

            def do_reject():
                success, msg = reject_submission(detail["id"],
                                                  self._auth.get_current_user().id,
                                                  notes_entry.get())
                dialog.destroy()
                self._load_data()
                MessageDialog(self, title="Reject", message=msg,
                              dialog_type="success" if success else "error")

            ctk.CTkButton(action_frame, text="Approve", command=do_approve,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                          fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT,
                          width=120, height=35).pack(side="left", padx=5)

            ctk.CTkButton(action_frame, text="Reject", command=do_reject,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                          fg_color=DANGER_COLOR, text_color=TEXT_LIGHT,
                          width=120, height=35).pack(side="left", padx=5)

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                      fg_color="gray", text_color=TEXT_LIGHT, width=100).pack(pady=(0, 15))

        dialog.after(100, dialog.focus_force)

    def refresh(self):
        self._load_data()
