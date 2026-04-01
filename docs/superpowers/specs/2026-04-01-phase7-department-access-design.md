# Phase 7: Department-Based Access & Enhanced User Management — Design Specification

## Context

Milestone 1 had 3 simple roles (admin/encoder/viewer) with no department scoping. Phase 7 introduces department-based access control so city officials, district coordinators, and barangay staff see only the data relevant to their jurisdiction.

## What Was Built

### Department Model
- `Department` table: id, name, level (city/district/barangay), district_id (FK nullable), barangay_id (FK nullable)
- Linked to `User` via `department_id` FK

### Expanded Roles (5 roles)
| Role | Permissions | Data Scope |
|------|-------------|------------|
| admin | Full access + manage departments | All data |
| city_official | View + approve + audit log | All data |
| district_coordinator | Enter/edit + approve | Own district only |
| encoder | Enter/edit data | Own department scope |
| viewer | Read-only | Own department scope |

### Scope Filtering
- `get_user_scope(user_id)` returns: `{"scope": "all"}`, `{"scope": "district", "district_id": int}`, or `{"scope": "barangay", "barangay_id": int}`
- Admin and city_official always get scope "all"
- District coordinators scoped to their department's district
- Barangay staff scoped to their department's barangay

### Default Departments Seeded
- City Hall - Office of the Mayor (city)
- City Planning & Development Office (city)
- City Peace & Order Council (city)
- District Office - 1st Congressional District (district)
- District Office - 2nd Congressional District (district)
- District Office - 3rd Congressional District (district)

## Files Created
- `services/department_service.py` — CRUD, scoping, seeding

## Files Modified
- `database/models.py` — Department model, User.department_id
- `auth/roles.py` — 5 roles with ROLE_PERMISSIONS and ROLE_LABELS
- `services/user_service.py` — department_id in create/update/list
- `ui/views/user_mgmt_view.py` — department dropdown in add/edit dialogs
- `database/seed.py` — seed_default_departments() on first run
