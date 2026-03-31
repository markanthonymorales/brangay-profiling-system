import customtkinter as ctk
from config import APP_NAME, APP_VERSION
from auth.auth_manager import AuthManager
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_HEADER,
    PRIMARY_COLOR, PRIMARY_HOVER, DANGER_COLOR, ACCENT_COLOR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_LIGHT, BG_COLOR, PADDING_LARGE,
)


class LoginView(ctk.CTkFrame):
    def __init__(self, master, on_login_success, **kwargs):
        super().__init__(master, fg_color="#003366", **kwargs)
        self._on_login_success = on_login_success
        self._auth = AuthManager()

        # Background gradient effect using layered frames
        bg_top = ctk.CTkFrame(self, fg_color="#003366", corner_radius=0)
        bg_top.place(relx=0, rely=0, relwidth=1, relheight=0.4)

        # Center card
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=16, width=440, height=520,
                            border_width=2, border_color="#DAA520")
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        # Logo
        try:
            from utils.logo_generator import get_logo_path
            from PIL import Image
            logo_img = ctk.CTkImage(Image.open(get_logo_path()), size=(80, 80))
            ctk.CTkLabel(card, image=logo_img, text="").pack(pady=(25, 8))
        except Exception:
            ctk.CTkLabel(
                card, text="\U0001F3DB", font=(FONT_FAMILY, 48),
            ).pack(pady=(25, 8))

        # Title
        ctk.CTkLabel(
            card, text="City Government of Davao",
            font=(FONT_FAMILY, 11), text_color="#DAA520",
        ).pack(pady=(0, 2))

        ctk.CTkLabel(
            card, text="Barangay Profiling System",
            font=(FONT_FAMILY, 18, "bold"), text_color="#003366",
        ).pack(pady=(0, 2))

        ctk.CTkLabel(
            card, text=f"v{APP_VERSION}",
            font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 5))

        # Gold divider
        ctk.CTkFrame(card, height=2, fg_color="#DAA520", corner_radius=0).pack(
            fill="x", padx=60, pady=(5, 20))

        # Username
        self._username = ctk.CTkEntry(
            card, placeholder_text="Username",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), width=300, height=42,
            border_color="#003366",
        )
        self._username.pack(pady=(0, 10))

        # Password
        self._password = ctk.CTkEntry(
            card, placeholder_text="Password", show="*",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), width=300, height=42,
            border_color="#003366",
        )
        self._password.pack(pady=(0, 5))
        self._password.bind("<Return>", lambda e: self._do_login())

        # Error message
        self._error_label = ctk.CTkLabel(
            card, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=DANGER_COLOR,
        )
        self._error_label.pack(pady=5)

        # Login button (gold)
        ctk.CTkButton(
            card, text="Sign In", command=self._do_login,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color="#DAA520", hover_color="#B8860B",
            text_color="#003366", width=300, height=44, corner_radius=8,
        ).pack(pady=(5, 10))

        # Footer
        ctk.CTkLabel(
            card, text="Davao City, Philippines",
            font=(FONT_FAMILY, 9), text_color=TEXT_SECONDARY,
        ).pack(pady=(5, 15))

        self._username.focus_set()

    def _do_login(self):
        username = self._username.get().strip()
        password = self._password.get()

        if not username or not password:
            self._error_label.configure(text="Please enter username and password.")
            return

        success, message = self._auth.login(username, password)
        if success:
            self._on_login_success()
        else:
            self._error_label.configure(text=message)
            self._password.delete(0, "end")
