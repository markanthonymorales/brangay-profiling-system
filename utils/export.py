import csv
import os
import logging

logger = logging.getLogger(__name__)


def export_to_csv(data: list[dict], headers: list[str], filepath: str) -> tuple[bool, str]:
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return True, f"Exported to {filepath}"
    except PermissionError:
        return False, f"Permission denied: {filepath}"
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        return False, str(e)


def export_report_to_csv(report_type: str, report_data: dict, filepath: str) -> tuple[bool, str]:
    if report_type == "barangay_profile":
        return _export_barangay_profile_csv(report_data, filepath)
    elif report_type == "district_summary":
        return _export_district_csv(report_data, filepath)
    elif report_type == "citywide":
        return _export_citywide_csv(report_data, filepath)
    elif report_type == "comparative":
        return _export_comparative_csv(report_data, filepath)
    return False, f"Unknown report type: {report_type}"


def _export_barangay_profile_csv(data: dict, filepath: str) -> tuple[bool, str]:
    rows = []
    brgy = data.get("barangay", {})
    headers = ["Section", "Field", "Value"]

    # Basic info
    for field, value in brgy.items():
        rows.append({"Section": "Basic Info", "Field": field, "Value": value})

    # Population
    for rec in data.get("population", []):
        for field, value in rec.items():
            rows.append({"Section": f"Population ({rec.get('year', '')})", "Field": field, "Value": value})

    # Resident categories
    for rec in data.get("resident_categories", []):
        for field, value in rec.items():
            rows.append({"Section": f"Residents ({rec.get('year', '')})", "Field": field, "Value": value})

    # Income
    for rec in data.get("income", []):
        for field, value in rec.items():
            rows.append({"Section": f"Income ({rec.get('year', '')})", "Field": field, "Value": value})

    # Businesses
    for i, biz in enumerate(data.get("businesses", []), 1):
        for field, value in biz.items():
            rows.append({"Section": f"Business #{i}", "Field": field, "Value": value})

    # Utilities
    for rec in data.get("utilities", []):
        for field, value in rec.items():
            rows.append({"Section": f"Utilities ({rec.get('year', '')})", "Field": field, "Value": value})

    # Land types
    for lt in data.get("land_types", []):
        for field, value in lt.items():
            rows.append({"Section": "Land Types", "Field": field, "Value": value})

    # Waste management
    for rec in data.get("waste_management", []):
        for field, value in rec.items():
            rows.append({"Section": f"Waste Mgmt ({rec.get('year', '')})", "Field": field, "Value": value})

    # Food sources
    for fs in data.get("food_sources", []):
        for field, value in fs.items():
            rows.append({"Section": "Food Sources", "Field": field, "Value": value})

    # Government facilities
    for fac in data.get("government_facilities", []):
        for field, value in fac.items():
            rows.append({"Section": "Gov Facilities", "Field": field, "Value": value})

    # Religious demographics
    for rec in data.get("religious_demographics", []):
        for field, value in rec.items():
            rows.append({"Section": f"Religion ({rec.get('year', '')})", "Field": field, "Value": value})

    return export_to_csv(rows, headers, filepath)


def _export_district_csv(data: dict, filepath: str) -> tuple[bool, str]:
    rows = []
    headers = ["Category", "Metric", "Value"]

    district = data.get("district", {})
    rows.append({"Category": "District", "Metric": "Name", "Value": district.get("name", "")})
    rows.append({"Category": "District", "Metric": "Barangay Count", "Value": district.get("barangay_count", 0)})

    for category_key in ("population", "income", "utilities", "businesses"):
        cat_data = data.get(category_key, {})
        for metric, value in cat_data.items():
            rows.append({"Category": category_key.capitalize(), "Metric": metric, "Value": value})

    # Barangay list
    for brgy in data.get("barangay_list", []):
        rows.append({
            "Category": "Barangay",
            "Metric": brgy["name"],
            "Value": f"Pop: {brgy['population'] or 'N/A'}, Class: {brgy['classification']}",
        })

    return export_to_csv(rows, headers, filepath)


def _export_citywide_csv(data: dict, filepath: str) -> tuple[bool, str]:
    rows = []
    headers = ["Category", "Metric", "Value"]

    city = data.get("city", {})
    rows.append({"Category": "City", "Metric": "Total Barangays", "Value": city.get("total_barangays", 0)})
    rows.append({"Category": "City", "Metric": "Total Districts", "Value": city.get("total_districts", 0)})

    for category_key in ("population", "income", "utilities", "businesses"):
        cat_data = data.get(category_key, {})
        for metric, value in cat_data.items():
            rows.append({"Category": category_key.capitalize(), "Metric": metric, "Value": value})

    for dr in data.get("districts", []):
        d_name = dr.get("district", {}).get("name", "")
        d_pop = dr.get("population", {})
        rows.append({
            "Category": f"District: {d_name}",
            "Metric": "Barangays",
            "Value": dr.get("district", {}).get("barangay_count", 0),
        })
        rows.append({
            "Category": f"District: {d_name}",
            "Metric": "Population",
            "Value": d_pop.get("total_population", 0),
        })

    return export_to_csv(rows, headers, filepath)


def _export_comparative_csv(data: dict, filepath: str) -> tuple[bool, str]:
    barangays = data.get("barangays", [])
    if not barangays:
        return False, "No barangay data to export."

    headers = [
        "Barangay", "District", "Population", "Households", "Avg Income (PHP)",
        "Water Coverage %", "Power Coverage %", "Internet Coverage %", "Active Businesses",
    ]

    rows = []
    for b in barangays:
        rows.append({
            "Barangay": b.get("name", ""),
            "District": b.get("district_name", ""),
            "Population": b.get("population") or "N/A",
            "Households": b.get("household_count") or "N/A",
            "Avg Income (PHP)": b.get("avg_income") or "N/A",
            "Water Coverage %": b.get("water_coverage") or "N/A",
            "Power Coverage %": b.get("power_coverage") or "N/A",
            "Internet Coverage %": b.get("internet_coverage") or "N/A",
            "Active Businesses": b.get("business_count", 0),
        })

    return export_to_csv(rows, headers, filepath)
