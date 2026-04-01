# Phase 13: Enhanced Recommendations & Retry Handling — Design Specification

## Context

Milestone 1 action plans had basic recommendations for public safety, infrastructure, and economic development. Phase 13 adds budget allocation estimates, emergency response readiness scoring, social services targeting, business development potential assessment, and a retry queue for failed database operations.

## What Was Built

### Enhanced Action Plan Recommendations

`services/plan_service.py` `generate_action_plan()` now generates 4 additional recommendation types:

**1. Budget Allocation Estimates**
- Formula: `population * per_capita_budget * infra_gap_weight * poverty_weight`
- Base: PHP 500 per capita
- Infrastructure gap weight: 1.0 to 1.5x (based on water/power coverage gaps)
- Poverty weight: 1.0 to 1.5x (based on below-poverty household ratio)
- Example: "Estimated annual budget allocation: PHP 30,887,296"

**2. Emergency Response Readiness Score**
- Factors: facility count (fewer = worse), crime rate, population density
- Score breakdown:
  - Facility score: `max(0, 3 - facility_count) * 20` (0-60 points)
  - Crime score: `min(crime_count * 3, 40)` (0-40 points)
  - Density penalty: `min(pop_density / 1000, 20)` (0-20 points)
- Levels: Critical (60+), Moderate (30-59), Adequate (<30)
- Recommends additional emergency response stations if score >= 30

**3. Social Services Needs**
- Triggers when below_poverty_count > 0
- HIGH priority if >= 100 households below poverty
- Recommends: DSWD coordination, 4Ps enrollment, AICS eligibility assessment
- Example: "Social services: 490 households below poverty line"

**4. Business Development Potential**
- Factors: commercial land %, active business count, average income
- Levels:
  - High: commercial > 10% OR businesses > 10 OR income > PHP 30,000
  - Moderate: commercial > 5% OR businesses > 5 OR income > PHP 15,000
  - Low: below moderate thresholds
- Prescriptive: permit streamlining (high), livelihood training (moderate), basic programs (low)

### Retry Queue

**RetryQueue Model:**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| operation | VARCHAR(100) | module.function format |
| table_name | VARCHAR(50) | Target table |
| data | TEXT (JSON) | Operation parameters |
| error_message | TEXT | Last error |
| attempts | INTEGER | Current attempt count |
| max_attempts | INTEGER | Default 3 |
| status | VARCHAR(20) | pending / completed / failed |

**Retry Functions:**
- `add_to_retry_queue(operation, table_name, data, error)` — queue a failed operation
- `process_retry_queue()` — re-attempt pending items, update status on success/failure
- `get_retry_queue(status, limit)` — list queue items for monitoring

**Processing Logic:**
1. Query pending items where attempts < max_attempts
2. For each: increment attempts, import module, call function with stored data
3. On success: status = "completed"
4. On failure: update error_message, if attempts >= max_attempts: status = "failed"

## Files Created
- None (RetryQueue model added to existing models.py)

## Files Modified
- `database/models.py` — RetryQueue model
- `services/plan_service.py` — 4 new recommendation generators (budget, emergency, social, business)
- `services/system_service.py` — add_to_retry_queue, process_retry_queue, get_retry_queue
