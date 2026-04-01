# Phase 10: Enhanced Validation & Notifications — Design Specification

## Context

Milestone 1 had basic field-level validation (required, positive int, percentage range). Phase 10 adds cross-field consistency checks, missing data detection, and a notification system for alerting users about data issues.

## What Was Built

### Validation Service
`services/validation_service.py` — `validate_submission(table_name, data)` performs:

**Cross-field consistency:**
- Population: male_count + female_count should approximately equal total_population (within 5% tolerance)
- Warns if discrepancy exceeds threshold

**Range checks:**
- All percentage fields must be 0-100
- Population counts must be non-negative

**Completeness checks:**
- Required fields per table (total_population for population_records, etc.)
- Warns on missing required fields

Returns `(is_valid: bool, messages: list[str])` — warnings don't block submission, errors do.

### Notification Model
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | FK users | Recipient |
| type | VARCHAR(50) | Category (data_alert, system, validation, etc.) |
| title | VARCHAR(200) | Short headline |
| message | TEXT | Full message |
| severity | VARCHAR(20) | info / warning / error |
| is_read | BOOLEAN | Dismissal state |

### Notification Service
- `create_notification(user_id, type, title, message, severity)`
- `get_notifications(user_id, unread_only=False, limit=50)`
- `mark_read(notification_id)`
- `mark_all_read(user_id)`
- `get_unread_count(user_id)`

### Notification View
- Scrollable list of notifications with severity-colored cards
- Filter: All / Unread Only
- "Mark All Read" button
- Individual dismiss buttons
- Severity icons: info (blue), warning (orange), error (red)

## Files Created
- `services/validation_service.py`
- `services/notification_service.py`
- `ui/views/notification_view.py`

## Files Modified
- `database/models.py` — Notification model
- `ui/components/sidebar.py` — "Notifications" nav item
- `ui/app.py` — notification view dispatch
