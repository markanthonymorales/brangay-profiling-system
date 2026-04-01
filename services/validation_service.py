import logging

logger = logging.getLogger(__name__)

# Required fields per table
REQUIRED_FIELDS = {
    "population_records": ["total_population", "male_count", "female_count"],
    "resident_categories": ["renters_count", "homeowners_count"],
    "income_data": ["average_household_income"],
    "utilities": ["water_coverage_pct", "power_coverage_pct"],
    "waste_management": ["coverage_pct"],
}

# Fields that should be percentages (0-100)
PERCENTAGE_FIELDS = {
    "utilities": ["water_coverage_pct", "power_coverage_pct", "internet_coverage_pct"],
    "waste_management": ["coverage_pct"],
}


def validate_submission(table_name: str, data: dict) -> tuple[bool, list[str]]:
    """Validate submission data for cross-field consistency, range checks, and completeness.

    Returns:
        tuple of (is_valid, list of warning/error messages)
    """
    issues = []

    # ── Completeness check ───────────────────────────────────
    required = REQUIRED_FIELDS.get(table_name, [])
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            issues.append(f"Missing required field: {field}")

    # ── Range checks (percentages 0-100) ─────────────────────
    pct_fields = PERCENTAGE_FIELDS.get(table_name, [])
    for field in pct_fields:
        val = data.get(field)
        if val is not None:
            try:
                num = float(val)
                if num < 0 or num > 100:
                    issues.append(f"{field} must be between 0 and 100 (got {num})")
            except (ValueError, TypeError):
                issues.append(f"{field} must be a number (got {val})")

    # ── Cross-field consistency ──────────────────────────────
    if table_name == "population_records":
        _validate_population_consistency(data, issues)

    is_valid = len(issues) == 0
    return is_valid, issues


def _validate_population_consistency(data: dict, issues: list[str]):
    """Check that male + female approximately equals total population."""
    total = data.get("total_population")
    male = data.get("male_count")
    female = data.get("female_count")

    if total is not None and male is not None and female is not None:
        try:
            total_val = int(total)
            male_val = int(male)
            female_val = int(female)
            gender_sum = male_val + female_val

            if total_val > 0:
                diff_pct = abs(gender_sum - total_val) / total_val * 100
                if diff_pct > 10:
                    issues.append(
                        f"Male ({male_val}) + Female ({female_val}) = {gender_sum} "
                        f"differs from total population ({total_val}) by {diff_pct:.1f}%"
                    )
        except (ValueError, TypeError):
            pass

    # Non-negative checks
    for field in ["total_population", "male_count", "female_count",
                  "registered_voters", "household_count"]:
        val = data.get(field)
        if val is not None:
            try:
                if int(val) < 0:
                    issues.append(f"{field} cannot be negative (got {val})")
            except (ValueError, TypeError):
                pass
