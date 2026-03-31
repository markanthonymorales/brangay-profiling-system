import os
import logging
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

logger = logging.getLogger(__name__)

# Davao City Government Colors
HEADER_BG = colors.HexColor("#003366")
HEADER_TEXT = colors.white
ROW_ALT = colors.HexColor("#F0F2F5")
ROW_NORMAL = colors.white
GRID_COLOR = colors.HexColor("#D0D5DD")
TITLE_COLOR = colors.HexColor("#003366")
SECTION_COLOR = colors.HexColor("#1A1A2E")
GOLD_COLOR = colors.HexColor("#DAA520")


def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=TITLE_COLOR,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=SECTION_COLOR,
        spaceBefore=16,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="FieldLabel",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.HexColor("#444444"),
    ))
    styles.add(ParagraphStyle(
        name="FieldValue",
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#222222"),
    ))
    return styles


def _build_table(headers: list[str], rows: list[list], col_widths=None) -> Table:
    data = [headers] + rows
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]

    # Alternating row colors
    for i in range(1, len(data)):
        bg = ROW_ALT if i % 2 == 0 else ROW_NORMAL
        style_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

    table.setStyle(TableStyle(style_commands))
    return table


def _fmt(value, default="-"):
    if value is None:
        return default
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _add_header_footer(canvas, doc, title: str):
    canvas.saveState()
    page_w = doc.pagesize[0]
    page_h = doc.pagesize[1]
    left = doc.leftMargin
    right = page_w - doc.rightMargin

    # Header bar (Davao blue)
    canvas.setFillColor(colors.HexColor("#003366"))
    canvas.rect(0, page_h - 42, page_w, 42, fill=True, stroke=False)

    # Gold accent line
    canvas.setFillColor(colors.HexColor("#DAA520"))
    canvas.rect(0, page_h - 45, page_w, 3, fill=True, stroke=False)

    # Header text
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(colors.white)
    canvas.drawString(left, page_h - 28, "City Government of Davao")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#B0BEC5"))
    canvas.drawString(left, page_h - 38, "Barangay Profiling System")
    canvas.setFillColor(colors.white)
    canvas.drawRightString(right, page_h - 28,
                           f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Footer
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#003366"))
    canvas.drawString(left, 20, "Davao City Barangay Profiling System")
    canvas.setFillColor(colors.HexColor("#DAA520"))
    canvas.drawCentredString(page_w / 2, 20, "Confidential - For Official Use Only")
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawRightString(right, 20, f"Page {doc.page}")
    # Footer line
    canvas.setStrokeColor(colors.HexColor("#DAA520"))
    canvas.line(left, 30, right, 30)
    canvas.restoreState()


# ── Barangay Profile PDF ─────────────────────────────────────

class BarangayProfilePDF:
    def __init__(self, data: dict):
        self._data = data

    def build(self, filepath: str) -> tuple[bool, str]:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            styles = _get_styles()
            brgy = self._data.get("barangay", {})
            title = f"Barangay Profile: {brgy.get('name', 'Unknown')}"

            doc = SimpleDocTemplate(
                filepath, pagesize=letter,
                topMargin=50, bottomMargin=40, leftMargin=40, rightMargin=40,
            )

            elements = []

            # Title
            elements.append(Paragraph(title, styles["ReportTitle"]))
            elements.append(Paragraph(
                f"{brgy.get('district_name', '')} | {brgy.get('classification', 'N/A')}",
                styles["ReportSubtitle"]
            ))

            # Basic info
            elements.append(Paragraph("Basic Information", styles["SectionHeader"]))
            info_data = [
                ["Field", "Value"],
                ["District", brgy.get("district_name", "")],
                ["Classification", brgy.get("classification", "N/A")],
                ["Latitude", _fmt(brgy.get("latitude"))],
                ["Longitude", _fmt(brgy.get("longitude"))],
                ["Area (sq km)", _fmt(brgy.get("area_sqkm"))],
            ]
            elements.append(_build_table(info_data[0], info_data[1:], col_widths=[2 * inch, 4 * inch]))

            # Population
            pop_data = self._data.get("population", [])
            if pop_data:
                elements.append(Paragraph("Population Records", styles["SectionHeader"]))
                headers = ["Year", "Total Pop.", "Male", "Female", "Voters", "Non-Reg.", "Foreign", "Households"]
                rows = [
                    [_fmt(r.get("year")), _fmt(r.get("total_population")), _fmt(r.get("male_count")),
                     _fmt(r.get("female_count")), _fmt(r.get("registered_voters")),
                     _fmt(r.get("non_registered_residents")), _fmt(r.get("foreign_residents")),
                     _fmt(r.get("household_count"))]
                    for r in pop_data
                ]
                elements.append(_build_table(headers, rows))

            # Resident categories
            res_data = self._data.get("resident_categories", [])
            if res_data:
                elements.append(Paragraph("Resident Categories", styles["SectionHeader"]))
                headers = ["Year", "Renters", "Homeowners", "Squatters", "Informal Settlers"]
                rows = [
                    [_fmt(r.get("year")), _fmt(r.get("renters_count")), _fmt(r.get("homeowners_count")),
                     _fmt(r.get("squatters_count")), _fmt(r.get("informal_settlers_count"))]
                    for r in res_data
                ]
                elements.append(_build_table(headers, rows))

            # Income
            income_data = self._data.get("income", [])
            if income_data:
                elements.append(Paragraph("Income Data", styles["SectionHeader"]))
                headers = ["Year", "Avg Income (PHP)", "Below Poverty", "Low", "Middle", "High"]
                rows = [
                    [_fmt(r.get("year")), _fmt(r.get("average_household_income")),
                     _fmt(r.get("below_poverty_count")), _fmt(r.get("low_income_count")),
                     _fmt(r.get("middle_income_count")), _fmt(r.get("high_income_count"))]
                    for r in income_data
                ]
                elements.append(_build_table(headers, rows))

            # Businesses
            biz_data = self._data.get("businesses", [])
            if biz_data:
                elements.append(Paragraph(f"Businesses ({len(biz_data)})", styles["SectionHeader"]))
                headers = ["Name", "Type", "Active", "Registered"]
                rows = [
                    [b.get("name", ""), b.get("type", ""),
                     "Yes" if b.get("is_active") else "No", b.get("registered_date", "")]
                    for b in biz_data
                ]
                elements.append(_build_table(headers, rows))

            # Utilities
            util_data = self._data.get("utilities", [])
            if util_data:
                elements.append(Paragraph("Utilities", styles["SectionHeader"]))
                headers = ["Year", "Water Source", "Water %", "Power Provider", "Power %", "Internet %"]
                rows = [
                    [_fmt(r.get("year")), r.get("water_source", ""),
                     _fmt(r.get("water_coverage_pct")), r.get("power_provider", ""),
                     _fmt(r.get("power_coverage_pct")), _fmt(r.get("internet_coverage_pct"))]
                    for r in util_data
                ]
                elements.append(_build_table(headers, rows))

            # Land types
            land_data = self._data.get("land_types", [])
            if land_data:
                elements.append(Paragraph("Land Types", styles["SectionHeader"]))
                headers = ["Type", "Area (sq km)", "Percentage %"]
                rows = [
                    [r.get("type", ""), _fmt(r.get("area_sqkm")), _fmt(r.get("percentage"))]
                    for r in land_data
                ]
                elements.append(_build_table(headers, rows))

            # Waste management
            waste_data = self._data.get("waste_management", [])
            if waste_data:
                elements.append(Paragraph("Waste Management", styles["SectionHeader"]))
                headers = ["Year", "Frequency", "Method", "Coverage %"]
                rows = [
                    [_fmt(r.get("year")), r.get("collection_frequency", ""),
                     r.get("disposal_method", ""), _fmt(r.get("coverage_pct"))]
                    for r in waste_data
                ]
                elements.append(_build_table(headers, rows))

            # Food sources
            food_data = self._data.get("food_sources", [])
            if food_data:
                elements.append(Paragraph("Food Sources", styles["SectionHeader"]))
                headers = ["Type", "Description"]
                rows = [[f.get("type", ""), f.get("description", "") or ""] for f in food_data]
                elements.append(_build_table(headers, rows))

            # Government facilities
            fac_data = self._data.get("government_facilities", [])
            if fac_data:
                elements.append(Paragraph("Government Facilities", styles["SectionHeader"]))
                headers = ["Agency", "Type", "Address"]
                rows = [
                    [f.get("agency_name", ""), f.get("facility_type", ""), f.get("address", "") or ""]
                    for f in fac_data
                ]
                elements.append(_build_table(headers, rows))

            # Religious demographics
            rel_data = self._data.get("religious_demographics", [])
            if rel_data:
                elements.append(Paragraph("Religious Demographics", styles["SectionHeader"]))
                headers = ["Year", "Religion", "Count", "Percentage %"]
                rows = [
                    [_fmt(r.get("year")), r.get("religion", ""),
                     _fmt(r.get("count")), _fmt(r.get("percentage"))]
                    for r in rel_data
                ]
                elements.append(_build_table(headers, rows))

            if not any([pop_data, res_data, income_data, biz_data, util_data,
                        land_data, waste_data, food_data, fac_data, rel_data]):
                elements.append(Spacer(1, 20))
                elements.append(Paragraph("No data has been recorded for this barangay yet.", styles["Normal"]))

            doc.build(
                elements,
                onFirstPage=lambda c, d: _add_header_footer(c, d, title),
                onLaterPages=lambda c, d: _add_header_footer(c, d, title),
            )
            return True, f"Report saved to {filepath}"
        except Exception as e:
            logger.error(f"PDF build failed: {e}")
            return False, str(e)


# ── District Summary PDF ─────────────────────────────────────

class DistrictSummaryPDF:
    def __init__(self, data: dict):
        self._data = data

    def build(self, filepath: str) -> tuple[bool, str]:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            styles = _get_styles()
            district = self._data.get("district", {})
            title = f"District Summary: {district.get('name', 'Unknown')}"

            doc = SimpleDocTemplate(
                filepath, pagesize=letter,
                topMargin=50, bottomMargin=40, leftMargin=40, rightMargin=40,
            )

            elements = []
            elements.append(Paragraph(title, styles["ReportTitle"]))
            elements.append(Paragraph(
                f"{district.get('barangay_count', 0)} Barangays",
                styles["ReportSubtitle"]
            ))

            # Population summary
            pop = self._data.get("population", {})
            elements.append(Paragraph("Population Summary", styles["SectionHeader"]))
            pop_table = [
                ["Metric", "Value"],
                ["Total Population", _fmt(pop.get("total_population"))],
                ["Male", _fmt(pop.get("total_male"))],
                ["Female", _fmt(pop.get("total_female"))],
                ["Total Households", _fmt(pop.get("total_households"))],
                ["Registered Voters", _fmt(pop.get("total_voters"))],
            ]
            elements.append(_build_table(pop_table[0], pop_table[1:], col_widths=[3 * inch, 3 * inch]))

            # Income summary
            inc = self._data.get("income", {})
            elements.append(Paragraph("Income Summary", styles["SectionHeader"]))
            inc_table = [
                ["Metric", "Value"],
                ["Avg Household Income (PHP)", _fmt(inc.get("average_household_income"))],
                ["Below Poverty Line", _fmt(inc.get("total_below_poverty"))],
            ]
            elements.append(_build_table(inc_table[0], inc_table[1:], col_widths=[3 * inch, 3 * inch]))

            # Utilities
            util = self._data.get("utilities", {})
            elements.append(Paragraph("Utility Coverage (Average)", styles["SectionHeader"]))
            util_table = [
                ["Metric", "Value"],
                ["Water Coverage %", _fmt(util.get("avg_water_coverage"))],
                ["Power Coverage %", _fmt(util.get("avg_power_coverage"))],
                ["Internet Coverage %", _fmt(util.get("avg_internet_coverage"))],
            ]
            elements.append(_build_table(util_table[0], util_table[1:], col_widths=[3 * inch, 3 * inch]))

            # Businesses
            biz = self._data.get("businesses", {})
            elements.append(Paragraph("Businesses", styles["SectionHeader"]))
            biz_table = [
                ["Metric", "Value"],
                ["Active Businesses", _fmt(biz.get("total_active"))],
                ["Inactive Businesses", _fmt(biz.get("total_inactive"))],
            ]
            elements.append(_build_table(biz_table[0], biz_table[1:], col_widths=[3 * inch, 3 * inch]))

            # Barangay list
            brgy_list = self._data.get("barangay_list", [])
            if brgy_list:
                elements.append(Paragraph(f"Barangays ({len(brgy_list)})", styles["SectionHeader"]))
                headers = ["Barangay", "Population", "Classification"]
                rows = [
                    [b.get("name", ""), _fmt(b.get("population")), b.get("classification", "")]
                    for b in brgy_list
                ]
                elements.append(_build_table(headers, rows))

            doc.build(
                elements,
                onFirstPage=lambda c, d: _add_header_footer(c, d, title),
                onLaterPages=lambda c, d: _add_header_footer(c, d, title),
            )
            return True, f"Report saved to {filepath}"
        except Exception as e:
            logger.error(f"PDF build failed: {e}")
            return False, str(e)


# ── City-Wide Report PDF ─────────────────────────────────────

class CitywideReportPDF:
    def __init__(self, data: dict):
        self._data = data

    def build(self, filepath: str) -> tuple[bool, str]:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            styles = _get_styles()
            title = "Davao City - City-Wide Summary Report"

            city = self._data.get("city", {})
            doc = SimpleDocTemplate(
                filepath, pagesize=letter,
                topMargin=50, bottomMargin=40, leftMargin=40, rightMargin=40,
            )

            elements = []
            elements.append(Paragraph(title, styles["ReportTitle"]))
            elements.append(Paragraph(
                f"{city.get('total_barangays', 0)} Barangays across {city.get('total_districts', 0)} Districts",
                styles["ReportSubtitle"]
            ))

            # City-wide population
            pop = self._data.get("population", {})
            elements.append(Paragraph("Population Summary", styles["SectionHeader"]))
            pop_table = [
                ["Metric", "Value"],
                ["Total Population", _fmt(pop.get("total_population"))],
                ["Male", _fmt(pop.get("total_male"))],
                ["Female", _fmt(pop.get("total_female"))],
                ["Total Households", _fmt(pop.get("total_households"))],
                ["Registered Voters", _fmt(pop.get("total_voters"))],
            ]
            elements.append(_build_table(pop_table[0], pop_table[1:], col_widths=[3 * inch, 3 * inch]))

            # Income
            inc = self._data.get("income", {})
            elements.append(Paragraph("Income Summary", styles["SectionHeader"]))
            inc_table = [
                ["Metric", "Value"],
                ["Avg Household Income (PHP)", _fmt(inc.get("average_household_income"))],
                ["Below Poverty Line", _fmt(inc.get("total_below_poverty"))],
            ]
            elements.append(_build_table(inc_table[0], inc_table[1:], col_widths=[3 * inch, 3 * inch]))

            # Utilities
            util = self._data.get("utilities", {})
            elements.append(Paragraph("Utility Coverage (Average)", styles["SectionHeader"]))
            util_table = [
                ["Metric", "Value"],
                ["Water Coverage %", _fmt(util.get("avg_water_coverage"))],
                ["Power Coverage %", _fmt(util.get("avg_power_coverage"))],
                ["Internet Coverage %", _fmt(util.get("avg_internet_coverage"))],
            ]
            elements.append(_build_table(util_table[0], util_table[1:], col_widths=[3 * inch, 3 * inch]))

            # Businesses
            biz = self._data.get("businesses", {})
            elements.append(Paragraph("Businesses", styles["SectionHeader"]))
            biz_table = [
                ["Metric", "Value"],
                ["Active Businesses", _fmt(biz.get("total_active"))],
                ["Inactive Businesses", _fmt(biz.get("total_inactive"))],
            ]
            elements.append(_build_table(biz_table[0], biz_table[1:], col_widths=[3 * inch, 3 * inch]))

            # Per-district breakdown
            for dr in self._data.get("districts", []):
                d_info = dr.get("district", {})
                d_pop = dr.get("population", {})
                d_inc = dr.get("income", {})
                d_util = dr.get("utilities", {})
                d_biz = dr.get("businesses", {})

                elements.append(Paragraph(
                    f"{d_info.get('name', '')} ({d_info.get('barangay_count', 0)} Barangays)",
                    styles["SectionHeader"]
                ))

                district_table = [
                    ["Metric", "Value"],
                    ["Population", _fmt(d_pop.get("total_population"))],
                    ["Households", _fmt(d_pop.get("total_households"))],
                    ["Voters", _fmt(d_pop.get("total_voters"))],
                    ["Avg Income (PHP)", _fmt(d_inc.get("average_household_income"))],
                    ["Water Coverage %", _fmt(d_util.get("avg_water_coverage"))],
                    ["Power Coverage %", _fmt(d_util.get("avg_power_coverage"))],
                    ["Internet Coverage %", _fmt(d_util.get("avg_internet_coverage"))],
                    ["Active Businesses", _fmt(d_biz.get("total_active"))],
                ]
                elements.append(_build_table(district_table[0], district_table[1:], col_widths=[3 * inch, 3 * inch]))

            doc.build(
                elements,
                onFirstPage=lambda c, d: _add_header_footer(c, d, title),
                onLaterPages=lambda c, d: _add_header_footer(c, d, title),
            )
            return True, f"Report saved to {filepath}"
        except Exception as e:
            logger.error(f"PDF build failed: {e}")
            return False, str(e)


# ── Comparative PDF ───────────────────────────────────────────

class ComparativePDF:
    def __init__(self, data: dict):
        self._data = data

    def build(self, filepath: str) -> tuple[bool, str]:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            styles = _get_styles()
            title = "Barangay Comparative Report"

            barangays = self._data.get("barangays", [])
            if not barangays:
                return False, "No barangay data for comparison."

            doc = SimpleDocTemplate(
                filepath, pagesize=landscape(letter),
                topMargin=50, bottomMargin=40, leftMargin=40, rightMargin=40,
            )

            elements = []
            elements.append(Paragraph(title, styles["ReportTitle"]))
            names = ", ".join(b.get("name", "") for b in barangays)
            elements.append(Paragraph(f"Comparing: {names}", styles["ReportSubtitle"]))

            # Build comparison table: rows are metrics, columns are barangays
            headers = ["Metric"] + [b.get("name", "") for b in barangays]

            metrics = [
                ("District", "district_name"),
                ("Population", "population"),
                ("Households", "household_count"),
                ("Avg Income (PHP)", "avg_income"),
                ("Water Coverage %", "water_coverage"),
                ("Power Coverage %", "power_coverage"),
                ("Internet Coverage %", "internet_coverage"),
                ("Active Businesses", "business_count"),
            ]

            rows = []
            for label, key in metrics:
                row = [label]
                for b in barangays:
                    val = b.get(key)
                    if key == "district_name":
                        row.append(val or "-")
                    else:
                        row.append(_fmt(val))
                rows.append(row)

            # Calculate column widths
            num_cols = len(headers)
            available = 9.5 * inch  # landscape letter minus margins
            metric_width = 1.8 * inch
            brgy_width = (available - metric_width) / max(num_cols - 1, 1)
            col_widths = [metric_width] + [brgy_width] * (num_cols - 1)

            elements.append(_build_table(headers, rows, col_widths=col_widths))

            doc.build(
                elements,
                onFirstPage=lambda c, d: _add_header_footer(c, d, title),
                onLaterPages=lambda c, d: _add_header_footer(c, d, title),
            )
            return True, f"Report saved to {filepath}"
        except Exception as e:
            logger.error(f"PDF build failed: {e}")
            return False, str(e)


# ── Dispatch ──────────────────────────────────────────────────

def build_pdf(report_type: str, data: dict, filepath: str) -> tuple[bool, str]:
    builders = {
        "barangay_profile": BarangayProfilePDF,
        "district_summary": DistrictSummaryPDF,
        "citywide": CitywideReportPDF,
        "comparative": ComparativePDF,
    }
    builder_class = builders.get(report_type)
    if not builder_class:
        return False, f"Unknown report type: {report_type}"
    return builder_class(data).build(filepath)
