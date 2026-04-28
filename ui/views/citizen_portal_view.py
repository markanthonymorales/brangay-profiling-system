import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE, FONT_SIZE_LARGE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
    PADDING_SMALL, SUCCESS_COLOR,
)
from services.citizen_portal_service import create_submission, get_submission_by_code

# Submission types for dropdown (lowercase to match service)
SUBMISSION_TYPES = ["incident", "concern", "feedback"]

# Category options
CATEGORIES = [
    "infrastructure", "public_safety", "health", "disaster",
    "traffic", "noise", "business", "environment", "other"
]


class CitizenPortalView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=PRIMARY_COLOR, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header, text="Citizen Portal", font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            text_color=TEXT_LIGHT, anchor="w", justify="left"
        ).pack(anchor="w", padx=PADDING_LARGE, pady=PADDING_LARGE)

        ctk.CTkLabel(
            header, text="Submit concerns and track their resolution",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color="#B0C4DE",
            anchor="w", justify="left"
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        # Tab view for Submit/Track
        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=PADDING_LARGE)

        # Add tabs
        self._tabview.add("Submit Issue")
        self._tabview.add("Track Status")

        # Build each tab
        self._build_submit_tab()
        self._build_track_tab()

    # ── Submit Tab ─────────────────────────────────────────────

    def _build_submit_tab(self):
        tab = self._tabview.tab("Submit Issue")

        # Scrollable container
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=PADDING_LARGE)

        # Title
        ctk.CTkLabel(
            scroll, text="Submit a Concern",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, PADDING_LARGE))

        # Form instructions
        ctk.CTkLabel(
            scroll, text="Fill out the form below to submit your concern. "
                        "A tracking code will be generated for you to follow up.",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
            justify="left", anchor="w"
        ).pack(anchor="w", pady=(0, PADDING_LARGE))

        # Submission Type
        type_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        type_frame.pack(fill="x", pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            type_frame, text="Type *", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, PADDING_SMALL))

        self._submit_type = ctk.CTkComboBox(
            type_frame, values=SUBMISSION_TYPES, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color=CARD_BG, border_color="#D0D5DD", button_color=PRIMARY_COLOR,
            dropdown_fg_color=CARD_BG, dropdown_hover_color=PRIMARY_COLOR,
        )
        self._submit_type.pack(fill="x")
        self._submit_type.set("Incident")

        # Category
        cat_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        cat_frame.pack(fill="x", pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            cat_frame, text="Category", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, PADDING_SMALL))

        ctk.CTkLabel(
            cat_frame, text="(Optional - leave blank for auto-categorization)",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, PADDING_SMALL))

        self._submit_category = ctk.CTkComboBox(
            cat_frame, values=["Auto-detect"] + CATEGORIES, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg_color=CARD_BG, border_color="#D0D5DD", button_color=PRIMARY_COLOR,
            dropdown_fg_color=CARD_BG, dropdown_hover_color=PRIMARY_COLOR,
        )
        self._submit_category.pack(fill="x")
        self._submit_category.set("Auto-detect")

        # Description
        desc_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        desc_frame.pack(fill="x", pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            desc_frame, text="Description *", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, PADDING_SMALL))

        self._submit_description = ctk.CTkTextbox(
            desc_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=CARD_BG,
            border_color="#D0D5DD", text_color=TEXT_PRIMARY, height=120
        )
        self._submit_description.pack(fill="x")
        self._submit_description.insert("1.0", "")

        # Location
        loc_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        loc_frame.pack(fill="x", pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            loc_frame, text="Location", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, PADDING_SMALL))

        ctk.CTkLabel(
            loc_frame, text="(e.g., near intersection, barangay name, landmark)",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, PADDING_SMALL))

        self._submit_location = ctk.CTkEntry(
            loc_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=CARD_BG,
            border_color="#D0D5DD", text_color=TEXT_PRIMARY, placeholder_text="Enter location..."
        )
        self._submit_location.pack(fill="x")

        # Reporter info section
        reporter_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        reporter_frame.pack(fill="x", pady=(0, PADDING_LARGE))

        ctk.CTkLabel(
            reporter_frame, text="Your Contact Information (Optional)",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, PADDING_SMALL))

        ctk.CTkLabel(
            reporter_frame, text="Providing contact info helps us follow up, but not required.",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, PADDING_NORMAL))

        # Reporter Name
        self._submit_name = ctk.CTkEntry(
            reporter_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=CARD_BG,
            border_color="#D0D5DD", text_color=TEXT_PRIMARY, placeholder_text="Your name (optional)"
        )
        self._submit_name.pack(fill="x", pady=(0, PADDING_NORMAL))

        # Reporter Contact
        self._submit_contact = ctk.CTkEntry(
            reporter_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=CARD_BG,
            border_color="#D0D5DD", text_color=TEXT_PRIMARY, placeholder_text="Contact number (optional)"
        )
        self._submit_contact.pack(fill="x", pady=(0, PADDING_NORMAL))

        # Reporter Email
        self._submit_email = ctk.CTkEntry(
            reporter_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=CARD_BG,
            border_color="#D0D5DD", text_color=TEXT_PRIMARY, placeholder_text="Email (optional)"
        )
        self._submit_email.pack(fill="x", pady=(0, PADDING_LARGE))

        # Submit button
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x")

        self._submit_btn = ctk.CTkButton(
            btn_frame, text="Submit Report", command=self._on_submit,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, height=45
        )
        self._submit_btn.pack(fill="x")

        # Result frame (hidden initially)
        self._result_frame = ctk.CTkFrame(scroll, fg_color="#E8F5E9", corner_radius=8)
        self._result_frame.pack(fill="x", pady=(PADDING_LARGE, 0))
        self._result_frame.pack_forget()

        res_title = ctk.CTkLabel(
            self._result_frame, text="Submission Successful!",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=SUCCESS_COLOR
        )
        res_title.pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_SMALL))

        self._tracking_code_label = ctk.CTkLabel(
            self._result_frame, text="",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=PRIMARY_COLOR
        )
        self._tracking_code_label.pack(anchor="w", padx=PADDING_LARGE)

        ctk.CTkLabel(
            self._result_frame, text="Save this code to track your report status.",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_SMALL, PADDING_LARGE))

        # Error frame (hidden initially)
        self._error_frame = ctk.CTkFrame(scroll, fg_color="#FFEBEE", corner_radius=8)
        self._error_frame.pack(fill="x", pady=(PADDING_LARGE, 0))
        self._error_frame.pack_forget()

        ctk.CTkLabel(
            self._error_frame, text="Submission Failed",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=DANGER_COLOR
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_SMALL))

        self._error_message = ctk.CTkLabel(
            self._error_frame, text="",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_PRIMARY
        )
        self._error_message.pack(anchor="w", padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

    def _on_submit(self):
        self._result_frame.pack_forget()
        self._error_frame.pack_forget()

        # Get form data
        submission_type = self._submit_type.get().lower()
        category = self._submit_category.get()
        if category == "Auto-detect":
            category = None
        description = self._submit_description.get("1.0", "end-1c").strip()
        location = self._submit_location.get().strip() or None
        reporter_name = self._submit_name.get().strip() or None
        reporter_contact = self._submit_contact.get().strip() or None
        reporter_email = self._submit_email.get().strip() or None

        # Validation
        if not description:
            self._show_error("Please enter a description of your concern.")
            return

        # Build data dict
        data = {
            "submission_type": submission_type,
            "category": category,
            "description": description,
            "location": location,
            "reporter_name": reporter_name,
            "reporter_contact": reporter_contact,
            "reporter_email": reporter_email,
        }

        # Submit
        success, result = create_submission(data)

        if success:
            self._tracking_code_label.configure(text=f"Tracking Code: {result}")
            self._result_frame.pack(fill="x", pady=(PADDING_LARGE, 0))
            # Clear form
            self._submit_description.delete("1.0", "end")
            self._submit_location.delete(0, "end")
            self._submit_name.delete(0, "end")
            self._submit_contact.delete(0, "end")
            self._submit_email.delete(0, "end")
        else:
            self._show_error(result)

    def _show_error(self, message: str):
        self._error_message.configure(text=message)
        self._error_frame.pack(fill="x", pady=(PADDING_LARGE, 0))

    # ── Track Tab ─────────────────────────────────────────────

    def _build_track_tab(self):
        tab = self._tabview.tab("Track Status")

        # Scrollable container
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=PADDING_LARGE)

        # Title
        ctk.CTkLabel(
            scroll, text="Track Your Report",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, PADDING_LARGE))

        # Instructions
        ctk.CTkLabel(
            scroll, text="Enter your tracking code to check the status of your report.",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
            justify="left", anchor="w"
        ).pack(anchor="w", pady=(0, PADDING_LARGE))

        # Tracking code input
        input_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        input_frame.pack(fill="x", pady=(0, PADDING_LARGE))

        ctk.CTkLabel(
            input_frame, text="Tracking Code *",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, PADDING_SMALL))

        self._track_code = ctk.CTkEntry(
            input_frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL), fg_color=CARD_BG,
            border_color="#D0D5DD", text_color=TEXT_PRIMARY, placeholder_text="e.g., CS-A1B2C3D4"
        )
        self._track_code.pack(fill="x", pady=(0, PADDING_NORMAL))

        # Search button
        ctk.CTkButton(
            input_frame, text="Check Status", command=self._on_track,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), fg_color=PRIMARY_COLOR,
            text_color=TEXT_LIGHT, height=40
        ).pack(fill="x")

        # Status result frame (hidden initially)
        self._status_result = ctk.CTkFrame(scroll, fg_color=CARD_BG, border_color="#D0D5DD", border_width=1)
        self._status_result.pack(fill="x", pady=(PADDING_LARGE, 0))
        self._status_result.pack_forget()

        # Status content
        status_header = ctk.CTkFrame(self._status_result, fg_color="transparent")
        status_header.pack(fill="x", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._status_badge = ctk.CTkLabel(
            status_header, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=WARNING_COLOR, text_color=TEXT_LIGHT, corner_radius=12, padx=12, pady=4
        )
        self._status_badge.pack(anchor="w")

        ctk.CTkLabel(
            self._status_result, text="Report Details",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_NORMAL, PADDING_SMALL))

        self._status_details = ctk.CTkLabel(
            self._status_result, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            text_color=TEXT_SECONDARY, justify="left", anchor="w"
        )
        self._status_details.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        # Resolution notes (hidden initially)
        self._resolution_frame = ctk.CTkFrame(self._status_result, fg_color="#E8F5E9", corner_radius=8)
        self._resolution_frame.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_LARGE))
        self._resolution_frame.pack_forget()

        ctk.CTkLabel(
            self._resolution_frame, text="Resolution Notes:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=SUCCESS_COLOR
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_SMALL))

        self._resolution_text = ctk.CTkLabel(
            self._resolution_frame, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            text_color=TEXT_PRIMARY, justify="left", anchor="w", wraplength=500
        )
        self._resolution_text.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        # Error frame (hidden initially)
        self._track_error = ctk.CTkFrame(scroll, fg_color="#FFEBEE", corner_radius=8)
        self._track_error.pack(fill="x", pady=(PADDING_LARGE, 0))
        self._track_error.pack_forget()

        ctk.CTkLabel(
            self._track_error, text="Tracking Code Not Found",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=DANGER_COLOR
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_SMALL))

        ctk.CTkLabel(
            self._track_error, text="Please check your tracking code and try again.",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

    def _on_track(self):
        self._status_result.pack_forget()
        self._track_error.pack_forget()

        code = self._track_code.get().strip().upper()
        if not code:
            self._track_error.pack(fill="x", pady=(PADDING_LARGE, 0))
            return

        result = get_submission_by_code(code)

        if result:
            self._show_status_result(result)
        else:
            self._track_error.pack(fill="x", pady=(PADDING_LARGE, 0))

    def _show_status_result(self, data: dict):
        # Status badge
        status_text = data.get("status", "unknown").upper()
        status_colors = {
            "submitted": WARNING_COLOR,
            "acknowledged": "#1E88E5",
            "routed": "#7B1FA2",
            "resolved": SUCCESS_COLOR,
            "rejected": DANGER_COLOR,
        }
        bg_color = status_colors.get(data.get("status", ""), WARNING_COLOR)
        self._status_badge.configure(text=f"  {status_text}  ", fg_color=bg_color)

        # Build details text
        details = []
        details.append(f"Type: {data.get('submission_type', '').title()}")
        details.append(f"Category: {data.get('category', 'N/A')}")
        if data.get("location"):
            details.append(f"Location: {data.get('location')}")
        details.append(f"Submitted: {data.get('created_at', 'N/A')}")
        if data.get("resolved_at"):
            details.append(f"Resolved: {data.get('resolved_at')}")

        self._status_details.configure(text="\n".join(details))

        # Resolution notes
        if data.get("resolution_notes"):
            self._resolution_text.configure(text=data.get("resolution_notes"))
            self._resolution_frame.pack(fill="x", padx=PADDING_LARGE, pady=(PADDING_NORMAL, PADDING_LARGE))
        else:
            self._resolution_frame.pack_forget()

        self._status_result.pack(fill="x", pady=(PADDING_LARGE, 0))