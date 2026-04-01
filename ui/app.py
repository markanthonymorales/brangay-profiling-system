import customtkinter as ctk
import logging
from config import APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from auth.auth_manager import AuthManager
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
    HEADER_BG, HEADER_BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    PRIMARY_COLOR, DANGER_COLOR, TEXT_LIGHT, BG_COLOR,
    PADDING_NORMAL, PADDING_LARGE,
)
from ui.components.sidebar import Sidebar

logger = logging.getLogger(__name__)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Set window icon
        try:
            from utils.logo_generator import get_icon_path
            self.iconbitmap(get_icon_path())
        except Exception:
            pass

        self._auth = AuthManager()
        self._current_view = None
        self._sidebar = None
        self._header_frame = None
        self._content_frame = None
        self._views_cache: dict = {}

        self._show_login()

    def _clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()
        self._sidebar = None
        self._header_frame = None
        self._content_frame = None
        self._views_cache.clear()
        self._current_view = None

    def _show_login(self):
        self._clear_window()
        from ui.views.login_view import LoginView
        login = LoginView(self, on_login_success=self._on_login_success)
        login.pack(fill="both", expand=True)

    def _on_login_success(self):
        user = self._auth.get_current_user()
        if user and user.must_change_password:
            self._show_change_password()
        else:
            self._show_main()

    def _show_change_password(self):
        self._clear_window()

        frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        frame.pack(fill="both", expand=True)

        card = ctk.CTkFrame(frame, fg_color="white", corner_radius=12, width=400, height=300)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(
            card, text="Change Password",
            font=(FONT_FAMILY, 20, "bold"), text_color=TEXT_PRIMARY,
        ).pack(pady=(30, 5))

        ctk.CTkLabel(
            card, text="You must change your default password before continuing.",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 20))

        new_pw = ctk.CTkEntry(card, placeholder_text="New Password", show="*",
                              font=(FONT_FAMILY, FONT_SIZE_NORMAL), width=300, height=38)
        new_pw.pack(pady=5)

        confirm_pw = ctk.CTkEntry(card, placeholder_text="Confirm Password", show="*",
                                  font=(FONT_FAMILY, FONT_SIZE_NORMAL), width=300, height=38)
        confirm_pw.pack(pady=5)
        confirm_pw.bind("<Return>", lambda e: do_change())

        error_label = ctk.CTkLabel(card, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                   text_color=DANGER_COLOR)
        error_label.pack(pady=5)

        def do_change():
            if new_pw.get() != confirm_pw.get():
                error_label.configure(text="Passwords do not match.")
                return
            user = self._auth.get_current_user()
            success, msg = self._auth.change_password(user.id, new_pw.get())
            if success:
                self._show_main()
            else:
                error_label.configure(text=msg)

        ctk.CTkButton(
            card, text="Change Password", command=do_change,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color="#DAA520", hover_color="#B8860B",
            text_color="#003366", width=300, height=44, corner_radius=8,
        ).pack(pady=(5, 10))

    def _show_main(self):
        self._clear_window()
        user = self._auth.get_current_user()

        # Header (Davao blue)
        self._header_frame = ctk.CTkFrame(self, fg_color=HEADER_BG, height=54, corner_radius=0)
        self._header_frame.pack(fill="x")
        self._header_frame.pack_propagate(False)

        # Logo + title
        try:
            from utils.logo_generator import get_logo_small_path
            from PIL import Image
            logo_img = ctk.CTkImage(Image.open(get_logo_small_path()), size=(32, 32))
            ctk.CTkLabel(self._header_frame, image=logo_img, text="").pack(side="left", padx=(PADDING_LARGE, 8))
        except Exception:
            pass

        ctk.CTkLabel(
            self._header_frame, text=APP_NAME,
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_LIGHT,
        ).pack(side="left")

        # Gold accent line
        gold_line = ctk.CTkFrame(self, fg_color="#DAA520", height=3, corner_radius=0)
        gold_line.pack(fill="x")

        # Right side of header
        right_frame = ctk.CTkFrame(self._header_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=PADDING_LARGE)

        ctk.CTkButton(
            right_frame, text="Logout", command=self._logout,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg_color="#DAA520", hover_color="#B8860B", text_color="#003366",
            width=80, height=30, corner_radius=6,
        ).pack(side="right", padx=(10, 0))

        role_text = user.role.capitalize() if user else ""
        ctk.CTkLabel(
            right_frame, text=f"{user.full_name}  |  {role_text}",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color="#B0BEC5",
        ).pack(side="right")

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = Sidebar(body, on_navigate=self._navigate,
                                user_role=user.role if user else "viewer")
        self._sidebar.pack(side="left", fill="y")

        # Content area
        self._content_frame = ctk.CTkFrame(body, fg_color=BG_COLOR, corner_radius=0)
        self._content_frame.pack(side="left", fill="both", expand=True)

        # Default view
        self._navigate("dashboard")
        self._sidebar.set_active("dashboard")

    def _navigate(self, view_key: str):
        if self._current_view:
            self._current_view.pack_forget()

        if view_key not in self._views_cache:
            view = self._create_view(view_key)
            if view:
                self._views_cache[view_key] = view

        view = self._views_cache.get(view_key)
        if view:
            view.pack(fill="both", expand=True)
            self._current_view = view
            if hasattr(view, "refresh"):
                view.refresh()

    def _create_view(self, view_key: str):
        if view_key == "dashboard":
            from ui.views.dashboard_view import DashboardView
            return DashboardView(self._content_frame)
        elif view_key == "barangays":
            from ui.views.barangay_list_view import BarangayListView
            return BarangayListView(self._content_frame, on_open_profile=self._open_barangay_profile)
        elif view_key == "data_entry":
            from ui.views.data_entry_view import DataEntryView
            return DataEntryView(self._content_frame)
        elif view_key == "submissions":
            from ui.views.submissions_view import SubmissionsView
            return SubmissionsView(self._content_frame)
        elif view_key == "reports":
            from ui.views.reports_view import ReportsView
            return ReportsView(self._content_frame)
        elif view_key == "analytics":
            from ui.views.analytics_view import AnalyticsView
            return AnalyticsView(self._content_frame)
        elif view_key == "comparisons":
            from ui.views.comparison_view import ComparisonView
            return ComparisonView(self._content_frame)
        elif view_key == "crime":
            from ui.views.crime_view import CrimeView
            return CrimeView(self._content_frame)
        elif view_key == "action_plans":
            from ui.views.action_plan_view import ActionPlanView
            return ActionPlanView(self._content_frame)
        elif view_key == "map":
            from ui.views.map_view import MapView
            return MapView(self._content_frame)
        elif view_key == "forecasting":
            from ui.views.forecast_view import ForecastView
            return ForecastView(self._content_frame)
        elif view_key == "notifications":
            from ui.views.notification_view import NotificationView
            return NotificationView(self._content_frame)
        elif view_key == "users":
            from ui.views.user_mgmt_view import UserMgmtView
            return UserMgmtView(self._content_frame)
        elif view_key == "audit_log":
            from ui.views.audit_log_view import AuditLogView
            return AuditLogView(self._content_frame)
        elif view_key == "schedule":
            from ui.views.schedule_view import ScheduleView
            return ScheduleView(self._content_frame)
        elif view_key == "system":
            from ui.views.system_view import SystemView
            return SystemView(self._content_frame)
        return None

    def _open_barangay_profile(self, barangay_data: dict):
        if self._current_view:
            self._current_view.pack_forget()

        cache_key = f"profile_{barangay_data['id']}"
        if cache_key in self._views_cache:
            self._views_cache[cache_key].destroy()

        from ui.views.barangay_profile_view import BarangayProfileView
        view = BarangayProfileView(
            self._content_frame,
            barangay_id=barangay_data["id"],
            on_back=lambda: self._navigate("barangays"),
        )
        self._views_cache[cache_key] = view
        view.pack(fill="both", expand=True)
        self._current_view = view

    def _logout(self):
        self._auth.logout()
        self._show_login()
