from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    CITY_OFFICIAL = "city_official"
    DISTRICT_COORDINATOR = "district_coordinator"
    ENCODER = "encoder"
    VIEWER = "viewer"


# Backward-compatible aliases
ROLE_LABELS = {
    Role.ADMIN: "Administrator",
    Role.CITY_OFFICIAL: "City Official",
    Role.DISTRICT_COORDINATOR: "District Coordinator",
    Role.ENCODER: "Encoder",
    Role.VIEWER: "Viewer",
}

ALL_ROLES = [r.value for r in Role]

ROLE_PERMISSIONS = {
    Role.ADMIN: {
        "view_data", "enter_data", "edit_data", "delete_data",
        "manage_users", "view_audit_log", "generate_reports", "export_data",
        "manage_departments", "approve_submissions", "view_system",
        "view_all_districts", "view_all_barangays",
    },
    Role.CITY_OFFICIAL: {
        "view_data", "generate_reports", "export_data",
        "approve_submissions", "view_audit_log",
        "view_all_districts", "view_all_barangays",
    },
    Role.DISTRICT_COORDINATOR: {
        "view_data", "enter_data", "edit_data",
        "generate_reports", "export_data",
        "approve_submissions",
        # Scoped to their district only (enforced at query level)
    },
    Role.ENCODER: {
        "view_data", "enter_data", "edit_data",
        "generate_reports", "export_data",
        # Scoped to their department's district/barangay
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
    try:
        return ROLE_LABELS.get(Role(role), role.capitalize())
    except ValueError:
        return role.capitalize()


def can_view_all_data(role: str) -> bool:
    """Check if role has unrestricted data access (no department scoping)."""
    return has_permission(role, "view_all_districts")
