# Daily Plan Integration for Snack Units

## Parent spec

[Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md)

## What to build

Structured trips' unit selections flow into the daily plan (spec: Data Flow, Behavior — daily plan). Auto-fill on a structured trip distributes unit selections into the existing `morning_snacks` / `afternoon_snacks` slots — 2 + 2 per full day, scaled by the per-day quota on partial days (a 2-unit half day gets 1 + 1) — using a new `snack_unit` assignment source type. Manual add/remove/adjust of unit assignments works through the existing assignment endpoints. The day page renders unit items (name, weight, calories) like snack items. Legacy trips' auto-fill and rendering are unchanged.

## Goal

Auto-fill on a structured trip lands every packed unit on a day — two in the morning slot, two in the afternoon, scaled on partial days — and the day view shows them, while legacy trips' daily plans are untouched.

## Type

AFK

## Blocked by

- Blocked by `2026-08-06-03-trip-unit-selections.md`

## User stories addressed

- User story 12

## Acceptance criteria

- [ ] `venv/bin/pytest` passes with new tests: a 0.5+2+0.5 trip @ 4/day with 12 units assigned gets 1+1 on each half day and 2+2 on full days; over-quota selections spill evenly (existing snack spill posture); under-quota leaves later slots empty with units unallocated-free; a legacy trip's auto-fill output is unchanged (snapshot assertion).
- [ ] `snack_unit` assignments round-trip through the existing assignment add/remove/patch endpoints and appear in `daily_plan_view` with name/weight/calories.
- [ ] Removing a unit assignment returns its quantity to the unallocated pool.
- [ ] Day page renders unit items in morning/afternoon snack slots for a structured trip; `pnpm lint && pnpm build && pnpm test` pass (existing `DailyPlanPage` tests untouched except added cases).

## Owns

- `backend/services/autofill.py` — new `distribute_snack_units`; `auto_fill` (structured branch: units replace the snack distribution for the snacks slots; lunch + drink mixes unchanged)
- `backend/services/daily_plan_queries.py` — `_autofill_inputs`, new `_snack_unit_info`, `_assignment_item`, `daily_plan_view`, `regenerate_daily_plan`
- `backend/routers/daily_plan.py` — accept `snack_unit` source type on assignment endpoints
- `backend/tests/test_daily_plan_units.py` — new
- `frontend/src/pages/DailyPlanPage.jsx` + `DailyPlanPage.test.jsx` — unit item rendering

## Must not touch

- `backend/services/snack_units.py`, `backend/services/trip_queries.py`, `backend/routers/trips.py` — owned by plan `2026-08-06-03`
- `backend/services/catalog_queries.py`, `backend/routers/snack_units.py` — owned by plan `2026-08-06-02`
- `backend/models.py`, `backend/migrations.py` — schema frozen (plan `2026-08-06-01`; `trip_day_assignments.source_type` is TEXT, no migration needed for the new value)
- `backend/mcp_server.py` — owned by plan `2026-08-06-06`
- `frontend/src/components/SnackSelection.jsx` — owned by plan `2026-08-06-03`

## Defines interfaces

- `snack_unit` value for `TripDayAssignment.source_type` (source_id = `trip_snack_units.id`) — consumed by plan `2026-08-06-06` (auto-fill MCP tool already regenerates plans)

## Pattern exemplar

- **MUST follow the pattern in**: `backend/services/autofill.py` — `distribute_snacks` (even distribution, eligible-day handling) for `distribute_snack_units`
- Follow the pattern in: `backend/tests/test_daily_plan.py` — fixture + assertion style; `backend/services/daily_plan_queries.py` — `_snack_info` for `_snack_unit_info`

## Tasks

- [ ] `distribute_snack_units`: walk days with per-day quotas from `snack_units.unit_quota`, fill morning then afternoon alternately up to ceil/floor split (2+2 on a 4-quota day, 1+1 on a 2-quota day), spreading unit types across days for variety (round-robin by type, matching `distribute_snacks`' heaviest-first order).
- [ ] Structured branch in `auto_fill`: snacks-slot distribution uses units; lunch (`TripSnack` slot `lunch`) and drink mixes flow exactly as today.
- [ ] `_snack_unit_info` + assignment item rendering + source-type validation on the assignment endpoints.
- [ ] Backend tests per criteria, including legacy snapshot.
- [ ] Day page unit rendering + component test cases.
