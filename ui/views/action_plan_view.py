import os
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, DANGER_COLOR,
    WARNING_COLOR, TEXT_LIGHT, BG_COLOR, CARD_BG, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.form_fields import LabeledDropdown
from ui.dialogs.message_dialog import MessageDialog
from services.barangay_service import get_all_districts, get_barangays_by_district
from services.plan_service import generate_action_plan
from config import BASE_DIR

PRIORITY_COLORS = {
    "HIGH": DANGER_COLOR,
    "MEDIUM": WARNING_COLOR,
    "LOW": ACCENT_COLOR,
}

CATEGORY_ICONS = {
    "Public Safety": "\U0001F6E1",
    "Infrastructure": "\U0001F3D7",
    "Community Services": "\U0001F465",
    "Economic Development": "\U0001F4B0",
}


class ActionPlanView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._districts = get_all_districts()
        self._district_map = {d["name"]: d["id"] for d in self._districts}
        self._barangay_map: dict[str, int] = {}
        self._plan_data = None
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Action Plans",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Selector row
        selector = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        selector.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        inner = ctk.CTkFrame(selector, fg_color="transparent")
        inner.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        district_names = [d["name"] for d in self._districts]
        self._district_dd = LabeledDropdown(
            inner, label="District", values=district_names,
            command=self._on_district_change,
        )
        self._district_dd.pack(side="left", padx=(0, 10), fill="x", expand=True)

        self._barangay_dd = LabeledDropdown(inner, label="Barangay", values=[])
        self._barangay_dd.pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            inner, text="Generate Plan", command=self._generate,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=140, height=38,
        ).pack(side="left", pady=(18, 0), padx=(0, 5))

        self._export_btn = ctk.CTkButton(
            inner, text="Export PDF", command=self._export_pdf,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, width=120, height=38,
            state="disabled",
        )
        self._export_btn.pack(side="left", pady=(18, 0))

        # Results area
        self._results = ctk.CTkScrollableFrame(self, fg_color=CARD_BG, corner_radius=12)
        self._results.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._placeholder = ctk.CTkLabel(
            self._results, text="Select a barangay and click 'Generate Plan' to create an action plan.",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._placeholder.pack(pady=40)

        if district_names:
            self._on_district_change(district_names[0])

    def _on_district_change(self, district_name: str):
        did = self._district_map.get(district_name)
        if not did:
            return
        brgys = get_barangays_by_district(did)
        self._barangay_map = {b["name"]: b["id"] for b in brgys}
        names = list(self._barangay_map.keys())
        self._barangay_dd.set_values(names)
        if names:
            self._barangay_dd.set(names[0])

    def _generate(self):
        brgy_name = self._barangay_dd.get()
        brgy_id = self._barangay_map.get(brgy_name)
        if not brgy_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return

        self._plan_data = generate_action_plan(brgy_id)
        self._render_plan()
        self._export_btn.configure(state="normal")

    def _render_plan(self):
        for w in self._results.winfo_children():
            w.destroy()

        data = self._plan_data
        if not data:
            return

        # Header
        ctk.CTkLabel(
            self._results,
            text=f"Action Plan: Brgy. {data['barangay_name']}",
            font=(FONT_FAMILY, 18, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 2))

        ctk.CTkLabel(
            self._results,
            text=f"{data['district_name']}  |  Generated: {data['generated_date']}  |  Crime (12mo): {data['crime_count_12m']}  |  Traffic (12mo): {data['traffic_count_12m']}",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 15))

        # Recommendations
        for i, rec in enumerate(data["recommendations"], 1):
            card = ctk.CTkFrame(self._results, fg_color="#FAFAFA", corner_radius=10)
            card.pack(fill="x", padx=PADDING_NORMAL, pady=4)

            # Left: priority badge + icon
            left = ctk.CTkFrame(card, fg_color="transparent", width=60)
            left.pack(side="left", padx=(PADDING_NORMAL, 5), pady=PADDING_NORMAL)
            left.pack_propagate(False)

            priority_color = PRIORITY_COLORS.get(rec["priority"], TEXT_SECONDARY)
            ctk.CTkLabel(
                left, text=rec["priority"],
                font=(FONT_FAMILY, 9, "bold"), text_color=TEXT_LIGHT,
                fg_color=priority_color, corner_radius=4, padx=6, pady=2,
            ).pack(anchor="w")

            icon = CATEGORY_ICONS.get(rec["category"], "\U0001F4CB")
            ctk.CTkLabel(left, text=icon, font=(FONT_FAMILY, 20)).pack(anchor="w", pady=(5, 0))

            # Right: content
            right = ctk.CTkFrame(card, fg_color="transparent")
            right.pack(side="left", fill="x", expand=True, padx=(0, PADDING_NORMAL), pady=PADDING_NORMAL)

            ctk.CTkLabel(
                right, text=f"#{i}  {rec['title']}",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
                anchor="w", wraplength=700,
            ).pack(anchor="w")

            ctk.CTkLabel(
                right, text=rec["category"],
                font=(FONT_FAMILY, 10), text_color=PRIMARY_COLOR,
            ).pack(anchor="w", pady=(2, 3))

            ctk.CTkLabel(
                right, text=rec["details"],
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
                anchor="w", wraplength=700, justify="left",
            ).pack(anchor="w")

    def _export_pdf(self):
        if not self._plan_data:
            return

        from utils.pdf_builder import _get_styles, _build_table, _fmt, _add_header_footer
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors as rl_colors

        default_dir = os.path.join(BASE_DIR, "data", "reports")
        os.makedirs(default_dir, exist_ok=True)

        brgy = self._plan_data["barangay_name"].replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"Action_Plan_{brgy}_{date_str}.pdf"

        filepath = filedialog.asksaveasfilename(
            initialdir=default_dir, initialfile=filename,
            defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")],
        )
        if not filepath:
            return

        try:
            styles = _get_styles()
            title = f"Action Plan: Brgy. {self._plan_data['barangay_name']}"

            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                    topMargin=50, bottomMargin=40, leftMargin=40, rightMargin=40)
            elements = []

            elements.append(Paragraph(title, styles["ReportTitle"]))
            elements.append(Paragraph(
                f"{self._plan_data['district_name']} | Generated: {self._plan_data['generated_date']} | "
                f"Crime (12mo): {self._plan_data['crime_count_12m']} | Traffic (12mo): {self._plan_data['traffic_count_12m']}",
                styles["ReportSubtitle"]
            ))

            headers = ["#", "Priority", "Category", "Recommendation", "Details"]
            rows = []
            for i, rec in enumerate(self._plan_data["recommendations"], 1):
                rows.append([
                    str(i), rec["priority"], rec["category"],
                    rec["title"], rec["details"][:120] + ("..." if len(rec["details"]) > 120 else ""),
                ])

            col_widths = [0.3 * inch, 0.7 * inch, 1.2 * inch, 2.0 * inch, 2.8 * inch]
            elements.append(_build_table(headers, rows, col_widths=col_widths))

            doc.build(
                elements,
                onFirstPage=lambda c, d: _add_header_footer(c, d, title),
                onLaterPages=lambda c, d: _add_header_footer(c, d, title),
            )
            MessageDialog(self, title="Export", message=f"Action plan exported to {filepath}", dialog_type="success")
        except Exception as e:
            MessageDialog(self, title="Error", message=str(e), dialog_type="error")

    def refresh(self):
        pass
