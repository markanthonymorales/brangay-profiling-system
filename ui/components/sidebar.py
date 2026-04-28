import customtkinter as ctk
from ui.theme import (
    SIDEBAR_BG, SIDEBAR_TEXT, SIDEBAR_HOVER, SIDEBAR_ACTIVE,
    SIDEBAR_WIDTH, FONT_FAMILY, FONT_SIZE_NORMAL, PADDING_NORMAL, TEXT_LIGHT,
    PRIMARY_COLOR
)


class SidebarItem(ctk.CTkButton):
    def __init__(self, master, text, icon="", command=None, **kwargs):
        super().__init__(
            master,
            text=f"  {icon}  {text}",
            command=command,
            anchor="w",
            height=40,
            corner_radius=8,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color="transparent",
            text_color=SIDEBAR_TEXT,
            hover_color=SIDEBAR_HOVER,
            **kwargs,
        )
        self._is_active = False

    def set_active(self, active: bool):
        self._is_active = active
        if active:
            self.configure(fg_color=SIDEBAR_ACTIVE, text_color=TEXT_LIGHT)
        else:
            self.configure(fg_color="transparent", text_color=SIDEBAR_TEXT)


# ── Navigation Categories ─────────────────────────────────────

# Menu categories with their items
# Format: (category_name, icon, items_list)
# Each item: (view_key, display_name, icon, required_permission)
NAV_CATEGORIES = [
    ("OVERVIEW", "Overview", [
        ("dashboard", "Dashboard", "\U0001F4CA", None),
        ("barangays", "Barangays", "\U0001F3D8", None),
        ("map", "Map", "\U0001F5FA", None),
    ]),
    ("DATA", "Data", [
        ("data_entry", "Data Entry", "\U0001F4DD", "enter_data"),
        ("submissions", "Submissions", "\U0001F4E5", "approve_submissions"),
    ]),
    ("ANALYTICS", "Analytics", [
        ("analytics", "Analytics", "\U0001F4C8", None),
        ("comparisons", "Comparisons", "\U0001F4CA", None),
        ("forecasting", "Forecasting", "\U0001F52E", None),
        ("reports", "Reports", "\U0001F4C4", None),
    ]),
    ("DEPARTMENTS", "Departments", [
        ("crime", "Crime & Safety", "\U0001F6E1", None),
        ("health", "Health & Welfare", "\U0001F3E5", None),
        ("disaster", "Disaster & Safety", "\U0001F6A8", None),
        ("education", "Education", "\U0001F393", None),
        ("business_permits", "Business Permits", "\U0001F4BC", None),
    ]),
    ("PLANNING", "Planning", [
        ("urban_planning", "Urban Planning", "\U0001F3E0", "view_data"),
        ("citizen_portal", "Citizen Portal", "\U0001F464", None),
        ("action_plans", "Action Plans", "\U0001F4CB", None),
        ("notifications", "Notifications", "\U0001F514", None),
    ]),
    ("GOVERNANCE", "Governance", [
        ("governance", "Governance", "\U0001F4DC", "view_data"),
    ]),
    ("SYSTEM", "System", [
        ("users", "User Management", "\U0001F465", "manage_users"),
        ("audit_log", "Audit Log", "\U0001F4DC", "view_audit_log"),
        ("schedule", "Data Collection", "\U0001F4C5", "manage_schedules"),
        ("system", "System", "\u2699", "view_system"),
    ]),
]


# Role-based category visibility
# Categories shown per role (None = all authenticated users)
CATEGORY_VISIBLE_FOR = {
    "OVERVIEW": None,  # All users
    "DATA": "enter_data",  # encoder, admin, city_official, district_coordinator
    "ANALYTICS": None,  # All users (view_data implied for logins)
    "DEPARTMENTS": None,  # All users
    "PLANNING": None,  # All users
    "GOVERNANCE": "view_data",  # admin, city_official, district_coordinator
    "SYSTEM": "manage_users",  # admin only
}


def can_access_category(role: str, category_permission: str | None) -> bool:
    """Check if role can access a category."""
    from auth.roles import has_permission
    
    if category_permission is None:
        # Logged in users can access
        return role in ("admin", "city_official", "district_coordinator", "encoder", "viewer")
    
    return has_permission(role, category_permission)


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, user_role="viewer", **kwargs):
        super().__init__(master, width=SIDEBAR_WIDTH, corner_radius=0,
                         fg_color=SIDEBAR_BG, **kwargs)
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._items: dict[str, SidebarItem] = {}
        self._user_role = user_role

        # Logo + title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(15, 5))

        try:
            from utils.logo_generator import get_logo_small_path
            from PIL import Image
            logo_img = ctk.CTkImage(Image.open(get_logo_small_path()), size=(36, 36))
            logo_row = ctk.CTkFrame(title_frame, fg_color="transparent")
            logo_row.pack(anchor="w")
            ctk.CTkLabel(logo_row, image=logo_img, text="").pack(side="left", padx=(0, 8))
            text_col = ctk.CTkFrame(logo_row, fg_color="transparent")
            text_col.pack(side="left")
            ctk.CTkLabel(text_col, text="Davao City", font=(FONT_FAMILY, 10),
                         text_color="#DAA520").pack(anchor="w")
            ctk.CTkLabel(text_col, text="Barangay Profiling", font=(FONT_FAMILY, 13, "bold"),
                         text_color=TEXT_LIGHT).pack(anchor="w")
        except Exception:
            ctk.CTkLabel(title_frame, text="Davao City", font=(FONT_FAMILY, 10),
                         text_color="#DAA520").pack(anchor="w")
            ctk.CTkLabel(title_frame, text="Barangay Profiling", font=(FONT_FAMILY, 13, "bold"),
                         text_color=TEXT_LIGHT).pack(anchor="w")

        # Gold separator
        ctk.CTkFrame(self, height=2, fg_color="#DAA520").pack(
            fill="x", padx=PADDING_NORMAL, pady=(12, 10)
        )

        # Scrollable container for nav items
        self._scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color=SIDEBAR_BG, scrollbar_button_color=SIDEBAR_HOVER,
            scrollbar_button_hover_color=SIDEBAR_ACTIVE,
        )
        self._scroll_frame.pack(fill="both", expand=True)

        # Build categories
        self._build_categories()

    def _build_categories(self):
        """Build categorized navigation menu."""
        for category_key, category_name, items in NAV_CATEGORIES:
            # Check if user can access this category
            category_permission = CATEGORY_VISIBLE_FOR.get(category_key)
            if not can_access_category(self._user_role, category_permission):
                continue

            # Category header
            category_frame = ctk.CTkFrame(self._scroll_frame, fg_color="transparent")
            category_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(12, 4))
            
            ctk.CTkLabel(
                category_frame,
                text=category_name.upper(),
                font=(FONT_FAMILY, 9, "bold"),
                text_color="#DAA520",  # Gold color for category headers
                anchor="w",
            ).pack(anchor="w", pady=(8, 4))

            # Add items in this category
            category_items = ctk.CTkFrame(self._scroll_frame, fg_color="transparent")
            category_items.pack(fill="x")

            for item_key, item_text, item_icon, item_permission in items:
                # Check if user has permission for this specific item
                if item_permission and not can_access_category(self._user_role, item_permission):
                    continue

                item = SidebarItem(
                    category_items,
                    text=item_text,
                    icon=item_icon,
                    command=lambda k=item_key: self._handle_click(k),
                )
                item.pack(fill="x", padx=PADDING_NORMAL, pady=1)
                self._items[item_key] = item

    def _add_item(self, key: str, text: str, icon: str):
        item = SidebarItem(
            self._scroll_frame, text=text, icon=icon,
            command=lambda k=key: self._handle_click(k),
        )
        item.pack(fill="x", padx=PADDING_NORMAL, pady=2)
        self._items[key] = item

    def _handle_click(self, key: str):
        for k, item in self._items.items():
            item.set_active(k == key)
        self._on_navigate(key)

    def set_active(self, key: str):
        for k, item in self._items.items():
            item.set_active(k == key)