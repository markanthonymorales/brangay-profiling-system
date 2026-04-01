import logging
from database.db import get_session
from database.models import (
    Barangay, PopulationRecord, IncomeData, Utility,
    CrimeIncident, TrafficIncident, GovernmentFacility, Business, LandType
)
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
        brgy = session.get(Barangay, barangay_id)
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

        # ── Budget Allocation Estimates ────────────────────────
        latest_pop = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year.desc())
            .first()
        )

        population = latest_pop.total_population if latest_pop and latest_pop.total_population else 0
        per_capita_budget = 500  # base PHP per capita

        if population > 0:
            # Weight by infrastructure gaps
            infra_gap_weight = 1.0
            if util:
                gaps = []
                if util.water_coverage_pct is not None:
                    gaps.append(100 - util.water_coverage_pct)
                if util.power_coverage_pct is not None:
                    gaps.append(100 - util.power_coverage_pct)
                if gaps:
                    avg_gap = sum(gaps) / len(gaps)
                    infra_gap_weight = 1.0 + (avg_gap / 100) * 0.5  # up to 1.5x

            # Weight by poverty rate
            poverty_weight = 1.0
            if income and income.below_poverty_count:
                total_hh = (income.below_poverty_count + (income.low_income_count or 0) +
                            (income.middle_income_count or 0) + (income.high_income_count or 0))
                if total_hh > 0:
                    poverty_rate = income.below_poverty_count / total_hh
                    poverty_weight = 1.0 + poverty_rate * 0.5  # up to 1.5x

            estimated_budget = population * per_capita_budget * infra_gap_weight * poverty_weight
            recommendations.append({
                "category": CAT_ECONOMIC,
                "priority": PRIORITY_MEDIUM,
                "title": f"Estimated annual budget allocation: PHP {estimated_budget:,.0f}",
                "details": (
                    f"Based on population of {population:,} at PHP {per_capita_budget}/capita, "
                    f"weighted by infrastructure gap ({infra_gap_weight:.2f}x) and "
                    f"poverty factor ({poverty_weight:.2f}x)."
                ),
            })

        # ── Emergency Response Readiness ─────────────────────
        facility_count = (
            session.query(func.count(GovernmentFacility.id))
            .filter_by(barangay_id=barangay_id)
            .scalar()
        ) or 0

        if population > 0:
            pop_density = population / (brgy.area_sqkm if brgy.area_sqkm and brgy.area_sqkm > 0 else 1)
            # Score: higher is worse (less ready)
            # Factors: fewer facilities, more crime, higher density
            facility_score = max(0, 3 - facility_count) * 20  # 0-60
            crime_score = min(crime_count * 3, 40)  # 0-40
            density_penalty = min(pop_density / 1000, 20)  # 0-20
            readiness_risk = facility_score + crime_score + density_penalty

            if readiness_risk >= 60:
                readiness_level = PRIORITY_HIGH
                readiness_text = "Critical"
            elif readiness_risk >= 30:
                readiness_level = PRIORITY_MEDIUM
                readiness_text = "Moderate"
            else:
                readiness_level = PRIORITY_LOW
                readiness_text = "Adequate"

            recommendations.append({
                "category": CAT_PUBLIC_SAFETY,
                "priority": readiness_level,
                "title": f"Emergency response readiness: {readiness_text} (score: {readiness_risk:.0f})",
                "details": (
                    f"Based on {facility_count} facilities, {crime_count} crimes (12mo), "
                    f"and population density of {pop_density:,.0f}/sq.km. "
                    f"{'Recommend establishing additional emergency response stations.' if readiness_risk >= 30 else 'Current readiness level is acceptable.'}"
                ),
            })

        # ── Social Services Needs ────────────────────────────
        if income and income.below_poverty_count and income.below_poverty_count > 0:
            recommendations.append({
                "category": CAT_COMMUNITY,
                "priority": PRIORITY_HIGH if income.below_poverty_count >= 100 else PRIORITY_MEDIUM,
                "title": f"Social services: {income.below_poverty_count} households below poverty line",
                "details": (
                    f"Recommend coordination with DSWD for 4Ps (Pantawid Pamilyang Pilipino Program) enrollment. "
                    f"Conduct community needs assessment for additional social welfare programs. "
                    f"Identify eligible households for AICS (Assistance to Individuals in Crisis Situations)."
                ),
            })

        # ── Business Development Potential ────────────────────
        active_businesses = (
            session.query(func.count(Business.id))
            .filter(Business.barangay_id == barangay_id, Business.is_active == True)
            .scalar()
        ) or 0

        commercial_land = (
            session.query(LandType)
            .filter(LandType.barangay_id == barangay_id, LandType.type.ilike("%commercial%"))
            .first()
        )
        commercial_pct = commercial_land.percentage if commercial_land and commercial_land.percentage else 0

        if population > 0:
            avg_income_val = income.average_household_income if income and income.average_household_income else 0
            biz_potential = "high" if (commercial_pct > 10 or active_businesses > 10 or avg_income_val > 30000) else (
                "moderate" if (commercial_pct > 5 or active_businesses > 5 or avg_income_val > 15000) else "low"
            )

            recommendations.append({
                "category": CAT_ECONOMIC,
                "priority": PRIORITY_MEDIUM if biz_potential == "high" else PRIORITY_LOW,
                "title": f"Business development potential: {biz_potential.capitalize()}",
                "details": (
                    f"Commercial land: {commercial_pct:.1f}%, Active businesses: {active_businesses}, "
                    f"Avg income: PHP {avg_income_val:,.0f}. "
                    f"{'Prioritize business permit streamlining and market development.' if biz_potential == 'high' else 'Consider livelihood training programs and MSME support.' if biz_potential == 'moderate' else 'Focus on basic livelihood programs before commercial development.'}"
                ),
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


def generate_crime_prevention_plan(barangay_id: int) -> dict | None:
    """Generate a crime prevention plan with patrol schedules, CCTV recs, and community programs."""
    session = get_session()
    try:
        brgy = session.get(Barangay, barangay_id)
        if not brgy:
            return None

        cutoff_1yr = date.today() - timedelta(days=365)
        cutoff_2yr = date.today() - timedelta(days=730)

        # Crime summary
        recent_crimes = (
            session.query(CrimeIncident)
            .filter(CrimeIncident.barangay_id == barangay_id,
                    CrimeIncident.date_occurred >= cutoff_1yr)
            .all()
        )
        prev_crimes = (
            session.query(CrimeIncident)
            .filter(CrimeIncident.barangay_id == barangay_id,
                    CrimeIncident.date_occurred >= cutoff_2yr,
                    CrimeIncident.date_occurred < cutoff_1yr)
            .all()
        )

        total_recent = len(recent_crimes)
        total_prev = len(prev_crimes)

        # Trend
        if total_prev > 0:
            trend_pct = round(((total_recent - total_prev) / total_prev) * 100, 1)
        else:
            trend_pct = 0.0

        if trend_pct > 10:
            trend = "increasing"
        elif trend_pct < -10:
            trend = "decreasing"
        else:
            trend = "stable"

        # Top types
        type_counts = {}
        for c in recent_crimes:
            type_counts[c.crime_type] = type_counts.get(c.crime_type, 0) + 1
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        crime_summary = {
            "total_incidents": total_recent,
            "top_types": [{"type": t, "count": c} for t, c in top_types],
            "trend": trend,
            "trend_pct": trend_pct,
        }

        # Patrol schedule
        patrol_schedule = [
            {
                "shift": "Morning (6AM-2PM)",
                "priority": "medium",
                "focus_areas": ["School zones", "Market areas", "Public parks"],
            },
            {
                "shift": "Afternoon (2PM-10PM)",
                "priority": "high" if total_recent >= 10 else "medium",
                "focus_areas": ["Commercial areas", "Transport terminals", "Busy intersections"],
            },
            {
                "shift": "Night (10PM-6AM)",
                "priority": "high",
                "focus_areas": ["Dark alleys and unlit streets", "Residential perimeters", "Establishments"],
            },
        ]

        # CCTV recommendations
        cctv_recommendations = []
        if total_recent >= 5:
            cctv_recommendations.append({
                "location_desc": "Main entry/exit points of the barangay",
                "priority": "high",
                "reason": f"High traffic area with {total_recent} incidents in 12 months",
            })
        if type_counts.get("theft", 0) >= 2 or type_counts.get("robbery", 0) >= 2:
            cctv_recommendations.append({
                "location_desc": "Commercial and market areas",
                "priority": "high",
                "reason": "Theft/robbery hotspot",
            })
        if total_recent >= 3:
            cctv_recommendations.append({
                "location_desc": "Barangay hall and public facilities perimeter",
                "priority": "medium",
                "reason": "Public safety monitoring",
            })

        # Community programs
        community_programs = []
        program_triggers = {
            "drugs": {
                "name": "Anti-Drug Awareness & Rehabilitation Referral",
                "target_group": "At-risk youth and affected families",
                "description": "Partner with PDEA and DSWD for drug awareness seminars and rehabilitation program referrals.",
            },
            "theft": {
                "name": "Livelihood Training Program",
                "target_group": "Unemployed and underemployed residents",
                "description": "Skills training and micro-enterprise support to address economic roots of theft.",
            },
            "robbery": {
                "name": "Economic Development & Livelihood Support",
                "target_group": "Low-income households",
                "description": "DSWD coordination for livelihood grants and employment assistance.",
            },
            "assault": {
                "name": "Conflict Resolution & Mediation Program",
                "target_group": "Community members and families",
                "description": "Barangay-level conflict resolution training and community mediation services.",
            },
            "domestic_violence": {
                "name": "VAWC Support & Family Welfare",
                "target_group": "Victims and at-risk families",
                "description": "Strengthen VAWC desk, partner with DSWD for counseling and shelter services.",
            },
        }

        for crime_type, count in type_counts.items():
            ct_lower = crime_type.lower()
            for trigger_key, program in program_triggers.items():
                if trigger_key in ct_lower and count >= 2:
                    prog = dict(program)
                    prog["triggered_by"] = f"{crime_type} ({count} incidents)"
                    community_programs.append(prog)
                    break

        # Always add neighborhood watch if crime count >= 5
        if total_recent >= 5:
            community_programs.append({
                "name": "Neighborhood Watch & Barangay Tanod Strengthening",
                "target_group": "All community members",
                "description": "Organize block-level neighborhood watch groups and strengthen barangay tanod patrols.",
                "triggered_by": f"General high crime ({total_recent} incidents)",
            })

        # Youth engagement for any significant crime
        if total_recent >= 3:
            community_programs.append({
                "name": "Youth Engagement & After-School Programs",
                "target_group": "Youth aged 13-21",
                "description": "Sports leagues, skills workshops, and mentorship programs to keep youth engaged.",
                "triggered_by": f"Crime prevention through youth engagement",
            })

        return {
            "barangay_name": brgy.name,
            "district_name": brgy.district.name,
            "generated_date": date.today().strftime("%Y-%m-%d"),
            "crime_summary": crime_summary,
            "patrol_schedule": patrol_schedule,
            "cctv_recommendations": cctv_recommendations,
            "community_programs": community_programs,
        }
    finally:
        session.close()
