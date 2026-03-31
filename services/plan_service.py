import logging
from database.db import get_session
from database.models import Barangay, PopulationRecord, IncomeData, Utility, CrimeIncident, TrafficIncident
from services.crime_service import get_crime_stats, get_crime_forecast
from sqlalchemy import func
from datetime import date, timedelta

logger = logging.getLogger(__name__)

PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"

CAT_PUBLIC_SAFETY = "Public Safety"
CAT_INFRASTRUCTURE = "Infrastructure"
CAT_COMMUNITY = "Community Services"
CAT_ECONOMIC = "Economic Development"


def generate_action_plan(barangay_id: int) -> dict | None:
    session = get_session()
    try:
        brgy = session.query(Barangay).get(barangay_id)
        if not brgy:
            return None

        recommendations = []
        cutoff = date.today() - timedelta(days=365)

        # ── Crime Analysis ────────────────────────────────────
        crime_count = (
            session.query(func.count(CrimeIncident.id))
            .filter(CrimeIncident.barangay_id == barangay_id, CrimeIncident.date_occurred >= cutoff)
            .scalar()
        ) or 0

        traffic_count = (
            session.query(func.count(TrafficIncident.id))
            .filter(TrafficIncident.barangay_id == barangay_id, TrafficIncident.date_occurred >= cutoff)
            .scalar()
        ) or 0

        # Crime severity
        if crime_count >= 16:
            recommendations.append({
                "category": CAT_PUBLIC_SAFETY,
                "priority": PRIORITY_HIGH,
                "title": "Critical crime level — deploy additional law enforcement",
                "details": f"{crime_count} crime incidents in the last 12 months. Recommend increased police visibility, community patrols, and coordination with PNP.",
            })
        elif crime_count >= 6:
            recommendations.append({
                "category": CAT_PUBLIC_SAFETY,
                "priority": PRIORITY_MEDIUM,
                "title": "Elevated crime rate — strengthen community watch",
                "details": f"{crime_count} crime incidents in the last 12 months. Recommend establishing or reinforcing barangay tanod patrols and community watch programs.",
            })
        elif crime_count > 0:
            recommendations.append({
                "category": CAT_PUBLIC_SAFETY,
                "priority": PRIORITY_LOW,
                "title": "Maintain current public safety measures",
                "details": f"{crime_count} crime incidents in the last 12 months. Crime levels are manageable. Continue existing community safety programs.",
            })

        # Crime trend forecast
        forecast = get_crime_forecast(barangay_id=barangay_id)
        if forecast["trend"] == "increasing":
            recommendations.append({
                "category": CAT_PUBLIC_SAFETY,
                "priority": PRIORITY_HIGH,
                "title": "Rising crime trend — preventive intervention needed",
                "details": "Crime incidents are on an increasing trend. Recommend proactive intervention: community engagement programs, CCTV installation, and coordination with DILG.",
            })

        # Top crime type
        crime_stats = get_crime_stats(barangay_id=barangay_id)
        if crime_stats["by_type"]:
            top_type = max(crime_stats["by_type"], key=crime_stats["by_type"].get)
            top_count = crime_stats["by_type"][top_type]
            if top_count >= 3:
                type_actions = {
                    "theft": "Increase street lighting and CCTV coverage in high-theft areas.",
                    "assault": "Conduct conflict resolution and anti-violence awareness programs.",
                    "drugs": "Coordinate with PDEA for anti-drug operations and rehabilitation referrals.",
                    "robbery": "Establish quick-response teams and improve emergency communication systems.",
                    "vandalism": "Deploy community beautification programs and youth engagement activities.",
                    "domestic_violence": "Strengthen VAWC desk services and partner with DSWD for family support.",
                    "fraud": "Conduct consumer awareness campaigns and strengthen business registration checks.",
                }
                action = type_actions.get(top_type, f"Develop targeted intervention program for {top_type} incidents.")
                recommendations.append({
                    "category": CAT_PUBLIC_SAFETY,
                    "priority": PRIORITY_MEDIUM,
                    "title": f"Address top crime type: {top_type} ({top_count} incidents)",
                    "details": action,
                })

        # Traffic
        if traffic_count >= 10:
            recommendations.append({
                "category": CAT_INFRASTRUCTURE,
                "priority": PRIORITY_HIGH,
                "title": "High traffic incident rate — road safety improvements needed",
                "details": f"{traffic_count} traffic incidents in 12 months. Recommend traffic management review, road signage improvement, and speed enforcement.",
            })
        elif traffic_count >= 3:
            recommendations.append({
                "category": CAT_INFRASTRUCTURE,
                "priority": PRIORITY_MEDIUM,
                "title": "Monitor traffic safety",
                "details": f"{traffic_count} traffic incidents in 12 months. Review traffic flow and identify accident-prone intersections.",
            })

        # ── Infrastructure Analysis ───────────────────────────
        util = (
            session.query(Utility)
            .filter_by(barangay_id=barangay_id)
            .order_by(Utility.year.desc())
            .first()
        )

        if util:
            if util.water_coverage_pct is not None and util.water_coverage_pct < 80:
                recommendations.append({
                    "category": CAT_INFRASTRUCTURE,
                    "priority": PRIORITY_HIGH if util.water_coverage_pct < 50 else PRIORITY_MEDIUM,
                    "title": f"Water coverage gap — {util.water_coverage_pct:.0f}% coverage",
                    "details": f"Water coverage is below target (80%). Coordinate with {util.water_source or 'water provider'} to expand distribution network.",
                })

            if util.power_coverage_pct is not None and util.power_coverage_pct < 90:
                recommendations.append({
                    "category": CAT_INFRASTRUCTURE,
                    "priority": PRIORITY_HIGH if util.power_coverage_pct < 60 else PRIORITY_MEDIUM,
                    "title": f"Power coverage gap — {util.power_coverage_pct:.0f}% coverage",
                    "details": f"Power coverage is below target (90%). Coordinate with {util.power_provider or 'power provider'} for electrification expansion.",
                })

            if util.internet_coverage_pct is not None and util.internet_coverage_pct < 50:
                recommendations.append({
                    "category": CAT_INFRASTRUCTURE,
                    "priority": PRIORITY_MEDIUM,
                    "title": f"Low internet coverage — {util.internet_coverage_pct:.0f}%",
                    "details": "Internet coverage is below 50%. Advocate for ISP expansion or community Wi-Fi programs to support digital access.",
                })
        else:
            recommendations.append({
                "category": CAT_INFRASTRUCTURE,
                "priority": PRIORITY_LOW,
                "title": "No utility data recorded",
                "details": "Conduct a utilities survey to assess water, power, and internet coverage levels.",
            })

        # ── Economic Analysis ─────────────────────────────────
        income = (
            session.query(IncomeData)
            .filter_by(barangay_id=barangay_id)
            .order_by(IncomeData.year.desc())
            .first()
        )

        if income:
            if income.below_poverty_count and income.below_poverty_count > 0:
                total_hh = (income.below_poverty_count + (income.low_income_count or 0) +
                            (income.middle_income_count or 0) + (income.high_income_count or 0))
                if total_hh > 0:
                    poverty_pct = (income.below_poverty_count / total_hh) * 100
                    if poverty_pct > 30:
                        recommendations.append({
                            "category": CAT_ECONOMIC,
                            "priority": PRIORITY_HIGH,
                            "title": f"High poverty rate — {poverty_pct:.0f}% below poverty line",
                            "details": f"{income.below_poverty_count} households below poverty line. Recommend livelihood programs, skills training, and DSWD coordination for 4Ps beneficiaries.",
                        })
                    elif poverty_pct > 15:
                        recommendations.append({
                            "category": CAT_ECONOMIC,
                            "priority": PRIORITY_MEDIUM,
                            "title": f"Moderate poverty rate — {poverty_pct:.0f}%",
                            "details": "Recommend community-based livelihood programs and micro-enterprise support.",
                        })

        # ── Population Analysis ───────────────────────────────
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year.desc())
            .limit(2)
            .all()
        )

        if len(pop_records) >= 2:
            latest = pop_records[0]
            previous = pop_records[1]
            if latest.total_population and previous.total_population and previous.total_population > 0:
                growth_pct = ((latest.total_population - previous.total_population) / previous.total_population) * 100
                if growth_pct > 5:
                    recommendations.append({
                        "category": CAT_COMMUNITY,
                        "priority": PRIORITY_MEDIUM,
                        "title": f"Rapid population growth — {growth_pct:.1f}% increase",
                        "details": "Rapid growth may strain services. Assess capacity for health centers, schools, and public facilities.",
                    })

        # ── No data fallback ──────────────────────────────────
        if not recommendations:
            recommendations.append({
                "category": CAT_COMMUNITY,
                "priority": PRIORITY_LOW,
                "title": "Insufficient data for analysis",
                "details": "Enter more barangay data (population, income, utilities, crime incidents) to generate meaningful action plans.",
            })

        # Sort by priority
        priority_order = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 99))

        return {
            "barangay_name": brgy.name,
            "district_name": brgy.district.name,
            "generated_date": date.today().strftime("%Y-%m-%d"),
            "crime_count_12m": crime_count,
            "traffic_count_12m": traffic_count,
            "recommendations": recommendations,
        }
    finally:
        session.close()
