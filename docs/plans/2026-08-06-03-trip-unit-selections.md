# Trip Unit Selections + Quota + Planner UI

## Parent spec

[Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md)

## What to build

The core structured planning slice (spec: Data Flow, Behavior). Trip endpoints to add/update/remove unit selections (packaged catalog item OR library unit type, × quantity, packed flag, actual weight). A quota service computes per-day and total unit quotas (round-to-nearest of `snacks_per_day` × day fraction). The trip summary reports units filled vs quota on structured trips instead of the 60% snack calorie band (weight/calories become secondary readouts; lunch's 40% band unchanged). The snack selection UI grows a structured branch: unit rows with quantities, a filled/quota meter, per-row tolerance badge against the trip's `oz_per_snack`, and packed/actual-weight handling. Legacy trips render exactly as today. Clone copies unit selection rows.

## Goal

On a structured trip the user fills a visible unit quota (e.g., 12 of 14) from packaged snacks and library bags, sees drifty units flagged, and packs against it — while every legacy trip's planner and summary remain pixel- and byte-identical.

## Type

AFK

## Blocked by

- Blocked by `2026-08-06-01-trip-snack-mode-schema.md`
- Blocked by `2026-08-06-02-snack-unit-library.md`

## User stories addressed

- User stories 4, 5, 6, 7, 8, 9 (planner side), 16, 17
- User story 11 (clone copies selections)

## Acceptance criteria

- [ ] `venv/bin/pytest` passes with new tests: quota for 0.5+2+0.5 @ 4/day = 12 (2+4+4+2); 0.25 first day rounds to 1; selections CRUD; unit endpoints on a legacy trip return 409; clone copies selection rows with packed reset.
- [ ] Structured trip summary includes `snack_units: {quota, filled, per_day}` and its `slot_subtotals.snacks` carries no `target_cal` band; a legacy trip's summary dict is unchanged (asserted against a pre-change snapshot in tests).
- [ ] Unit calories/weight follow the packaged (catalog serving) vs bag (library derived) rules from the spec, verified in `trip_summary_view` totals.
- [ ] Planner UI on a structured trip: add a packaged unit and a bag unit, set quantities, meter shows filled/quota and turns complete at quota; row badge appears when unit weight is outside ±25% of the trip's `oz_per_snack`; packed checkbox + actual weight editable.
- [ ] Planner UI on a legacy trip is unchanged (existing `SnackSelection` component tests still pass untouched except for added structured cases).
- [ ] `pnpm lint && pnpm build && pnpm test` pass.

## Owns

- `backend/services/snack_units.py` — new module: quota math (`unit_quota(trip)` → total + per-day list), selection views, unit weight/calorie resolution (delegating bag math to `snack_unit_type_view`)
- `backend/routers/trips.py` — new unit selection endpoints; `clone_trip` (add selection-row copying)
- `backend/services/trip_planning.py` — selection operations + structured-only guard
- `backend/services/trip_queries.py` — `trip_summary_view` (structured branch: unit meter, drop snack calorie band), `trip_detail_view` (include selections)
- `backend/schemas.py` — selection schemas
- `backend/tests/test_snack_units_trip.py` — new
- `frontend/src/components/SnackSelection.jsx` + `SnackSelection.test.jsx` — structured branch
- `frontend/src/components/TripSummary.jsx` — unit meter display
- `frontend/src/api.js` — selection API helpers

## Must not touch

- `backend/models.py`, `backend/migrations.py` — schema frozen (plan `2026-08-06-01`)
- `backend/services/catalog_queries.py`, `backend/routers/snack_units.py` — owned by plan `2026-08-06-02`
- `packing_view`, `shopping_view` in `backend/services/trip_queries.py` — owned by plan `2026-08-06-05`
- `backend/services/autofill.py`, `backend/services/daily_plan_queries.py`, `backend/routers/daily_plan.py` — owned by plan `2026-08-06-04`
- `backend/mcp_server.py`, `.claude/agents/plan-food.md` — owned by plan `2026-08-06-06`

## Defines interfaces

- `backend/services/snack_units.py` — `unit_quota(trip)` and selection view shape — consumed by plans `2026-08-06-04` (per-day distribution), `05` (expansion), `06` (MCP)
- Trip summary `snack_units` block — consumed by plan `2026-08-06-06` and the frontend
- `/api/trips/{id}/snack-units` REST shape — consumed by plan `2026-08-06-06`

## Pattern exemplar

- **MUST follow the pattern in**: `backend/routers/trips.py` — `add_trip_snack` / `update_trip_snack` / `remove_trip_snack` for the selection endpoints
- Follow the pattern in: `backend/services/trip_queries.py` — `trip_snack_view` for selection views and `trip_summary_view`'s `slot_subtotals` for the meter fields; `frontend/src/components/SnackSelection.jsx` existing sections for the structured branch's look and feel

## Tasks

- [ ] `snack_units.py` service: quota math (per-day round-half-up of `snacks_per_day` × fraction over the day list), selection resolution (packaged vs bag), selection view.
- [ ] Selection endpoints + structured-only guard (409 on legacy trips) + schemas.
- [ ] Clone: copy `trip_snack_units` rows, reset packed/actual weight (match existing snack clone posture).
- [ ] `trip_summary_view` structured branch: `snack_units` meter block; snacks slot loses the calorie band; unit weight/calories/macros roll into trip totals; legacy path untouched.
- [ ] Backend tests per criteria, including the legacy-invariance snapshot.
- [ ] Frontend structured snacks section: unit picker (catalog packaged items + library types), quantity steppers, meter, tolerance badges, packed/actual-weight; summary meter; component tests.

## Implementation notes

Day list construction already exists in `autofill.build_day_list` — but this plan must not touch `autofill.py`, so `snack_units.py` derives its day fractions directly from the trip's `first_day_fraction` / `full_days` / `last_day_fraction` fields (trivial math, no shared helper needed; plan 04 reconciles if drift appears). Macro accumulation for units follows the exact pattern `trip_summary_view` uses for `TripSnack` rows: per-oz ingredient data × ounces, tracked in `macro_covered_calories`.
