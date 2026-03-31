from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    ENCODER = "encoder"
    VIEWER = "viewer"


ROLE_PERMISSIONS = {
    Role.ADMIN: {
        "view_data", "enter_data", "edit_data", "delete_data",
        "manage_users", "view_audit_log", "generate_reports", "export_data",
    },
    Role.ENCODER: {
        "view_data", "enter_data", "edit_data",
        "generate_reports", "export_data",
    },
    Role.VIEWER: {
        "view_data", "generate_reports", "export_data",
    },
}


def has_permission(role: str, permission: str) -> bool:
    try:
        role_enum = Role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(role_enum, set())


def get_role_display(role: str) -> str:
    return role.capitalize()
