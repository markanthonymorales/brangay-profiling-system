import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR, WARNING_COLOR,
    TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.data_table import DataTable
from ui.components.form_fields import LabeledEntry, LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from ui.dialogs.confirm_dialog import ConfirmDialog
from auth.auth_manager import AuthManager
from auth.roles import Role, ALL_ROLES
from services.user_service import create_user, update_user, deactivate_user, activate_user, list_users
from services.department_service import list_departments


class UserMgmtView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        ctk.CTkLabel(
            header, text="User Management",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Add User", command=self._show_add_dialog,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, width=120, height=35,
        ).pack(side="right")

        # Table
        columns = [
            {"key": "username", "title": "Username", "width": 2},
            {"key": "full_name", "title": "Full Name", "width": 2},
            {"key": "role", "title": "Role", "width": 2},
            {"key": "department_name", "title": "Department", "width": 2},
            {"key": "is_active", "title": "Status", "width": 1},
            {"key": "created_at", "title": "Created", "width": 2},
        ]
        self._table = DataTable(self, columns=columns, on_row_click=self._on_row_click)
        self._table.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

    def _on_row_click(self, row_data: dict):
        self._show_edit_dialog(row_data)

    def _show_add_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add User")
        dialog.geometry("440x480")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="New User", font=(FONT_FAMILY, 16, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(20, 15))

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20)

        username = LabeledEntry(scroll, label="Username", required=True)
        username.pack(fill="x", pady=2)

        full_name = LabeledEntry(scroll, label="Full Name", required=True)
        full_name.pack(fill="x", pady=2)

        password = LabeledEntry(scroll, label="Password", required=True)
        password.pack(fill="x", pady=2)

        role = LabeledDropdown(scroll, label="Role", values=ALL_ROLES)
        role.pack(fill="x", pady=2)

        # Department dropdown
        depts = list_departments()
        dept_names = ["None"] + [d["name"] for d in depts]
        dept_map = {d["name"]: d["id"] for d in depts}
        department = LabeledDropdown(scroll, label="Department", values=dept_names)
        department.pack(fill="x", pady=2)

        error_label = ctk.CTkLabel(dialog, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                   text_color=DANGER_COLOR)
        error_label.pack(pady=3)

        def do_create():
            if not username.get() or not full_name.get() or not password.get():
                error_label.configure(text="All fields are required.")
                return
            dept_id = dept_map.get(department.get())
            user = self._auth.get_current_user()
            success, msg = create_user(
                username.get(), password.get(), full_name.get(),
                role.get(), user.id if user else 0,
                department_id=dept_id,
            )
            if success:
                dialog.destroy()
                self.refresh()
                MessageDialog(self, title="Success", message=msg, dialog_type="success")
            else:
                error_label.configure(text=msg)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Create User", command=do_create,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                      fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, width=140, height=38).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                      fg_color="gray", text_color=TEXT_LIGHT, width=100, height=38).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    def _show_edit_dialog(self, row_data: dict):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Edit User: {row_data['username']}")
        dialog.geometry("440x400")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"Edit: {row_data['username']}",
                     font=(FONT_FAMILY, 16, "bold"), text_color=TEXT_PRIMARY).pack(pady=(20, 15))

        full_name = LabeledEntry(dialog, label="Full Name")
        full_name.set(row_data["full_name"])
        full_name.pack(fill="x", padx=30, pady=2)

        role = LabeledDropdown(dialog, label="Role", values=ALL_ROLES)
        role.set(row_data["role"])
        role.pack(fill="x", padx=30, pady=2)

        depts = list_departments()
        dept_names = ["None"] + [d["name"] for d in depts]
        dept_map = {d["name"]: d["id"] for d in depts}
        department = LabeledDropdown(dialog, label="Department", values=dept_names)
        current_dept = row_data.get("department_name", "None")
        department.set(current_dept if current_dept in dept_names else "None")
        department.pack(fill="x", padx=30, pady=2)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)

        def do_update():
            dept_id = dept_map.get(department.get())
            user = self._auth.get_current_user()
            success, msg = update_user(
                row_data["id"], full_name=full_name.get(), role=role.get(),
                department_id=dept_id,
                updated_by_user_id=user.id if user else 0,
            )
            dialog.destroy()
            self.refresh()
            dialog_type = "success" if success else "error"
            MessageDialog(self, title="Update User", message=msg, dialog_type=dialog_type)

        ctk.CTkButton(btn_frame, text="Save", command=do_update,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                      fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        is_active = row_data.get("is_active", True)
        if is_active:
            def do_deactivate():
                user = self._auth.get_current_user()
                success, msg = deactivate_user(row_data["id"], user.id if user else 0)
                dialog.destroy()
                self.refresh()
                dialog_type = "success" if success else "error"
                MessageDialog(self, title="Deactivate", message=msg, dialog_type=dialog_type)

            ctk.CTkButton(btn_frame, text="Deactivate", command=do_deactivate,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                          fg_color=DANGER_COLOR, text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)
        else:
            def do_activate():
                user = self._auth.get_current_user()
                success, msg = activate_user(row_data["id"], user.id if user else 0)
                dialog.destroy()
                self.refresh()
                dialog_type = "success" if success else "error"
                MessageDialog(self, title="Activate", message=msg, dialog_type=dialog_type)

            ctk.CTkButton(btn_frame, text="Activate", command=do_activate,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                          fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy,
                      font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                      fg_color="gray", text_color=TEXT_LIGHT, width=100, height=35).pack(side="left", padx=5)

        dialog.after(100, dialog.focus_force)

    def refresh(self):
        users = list_users(include_inactive=True)
        for u in users:
            u["is_active"] = "Active" if u["is_active"] else "Inactive"
        self._table.set_data(users)
