# Phase 9: Real-Time Dashboard & Scheduled Updates — Design Specification

## Context

The Milestone 1 dashboard required manual navigation to refresh. Phase 9 adds auto-refresh and a pending submissions indicator for real-time monitoring.

## What Was Built

### Auto-Refresh
- `dashboard_view.py` calls `self.after(DASHBOARD_REFRESH_SECONDS * 1000, self.refresh)` at the end of each `refresh()` cycle
- Default interval: 60 seconds (configurable in `config.py`)
- Dashboard stats, charts, district overview, and activity feed all update automatically

### Pending Submissions Card
- New stat card "Pending Submissions" added to the dashboard top row
- Shows count from `submission_service.get_pending_count()`
- Orange color (#E65100) to draw attention

### Configuration
- `config.py`: `DASHBOARD_REFRESH_SECONDS = 60`

## Files Modified
- `ui/views/dashboard_view.py` — auto-refresh loop, pending submissions stat card
- `config.py` — DASHBOARD_REFRESH_SECONDS constant
