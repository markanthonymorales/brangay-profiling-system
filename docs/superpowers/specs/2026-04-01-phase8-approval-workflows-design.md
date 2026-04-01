# Phase 8: Approval Workflows — Design Specification

## Context

In Milestone 1, data entry saved directly to the database. Phase 8 introduces an approval pipeline where encoders submit data for review, and coordinators/admins approve or reject submissions before data is persisted.

## What Was Built

### Submission Model
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| submitted_by | FK users | Who submitted |
| reviewed_by | FK users | Who approved/rejected (nullable) |
| table_name | VARCHAR | Target table (population_records, income_data, etc.) |
| barangay_id | FK barangays | Which barangay |
| year | INTEGER | Data year (nullable) |
| record_data | TEXT (JSON) | The submitted data payload |
| status | VARCHAR | draft / pending / approved / rejected |
| review_notes | TEXT | Reviewer's comments |
| reviewed_at | DATETIME | When reviewed |

### Workflow
1. Encoder fills out data entry form → clicks "Submit for Review"
2. `create_submission()` stores data as JSON with status "pending"
3. Submission appears in the Submissions queue view
4. Coordinator/admin opens submission → sees data preview
5. Clicks "Approve" → `approve_submission()` saves data to actual table via `_apply_submission()` handler
6. Or clicks "Reject" with notes → `reject_submission()` updates status

### Save Handlers
Maps table_name to the correct service save function:
- `population_records` → `population_service.save_population_record`
- `resident_categories` → `resident_service.save_resident_category`
- `income_data` → `economic_service.save_income_record`
- `utilities` → `infrastructure_service.save_utility_record`
- `waste_management` → `infrastructure_service.save_waste_record`

### Submissions View
- Filterable by status (All/pending/approved/rejected)
- Pending count badge
- Click row → detail dialog with data preview + approve/reject buttons
- Review notes field for rejection reasons

## Files Created
- `services/submission_service.py` — create, approve, reject, list, get_pending_count
- `ui/views/submissions_view.py` — queue view with approve/reject UI

## Files Modified
- `database/models.py` — Submission model
- `ui/components/sidebar.py` — "Submissions" nav item
- `ui/app.py` — submissions view dispatch
