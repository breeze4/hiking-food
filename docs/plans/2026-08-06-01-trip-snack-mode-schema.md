# Trip Snack Mode + Schema Foundation

## Parent spec

[Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md)

## What to build

The gating and schema foundation for structured snacks (spec: Data Flow, Behavior). One migration adds `snack_model`, `snacks_per_day`, `oz_per_snack` to trips (backfill existing rows to `legacy`) and creates three empty tables: `snack_unit_types`, `snack_unit_ingredients`, `trip_snack_units`. New trips default to `structured` / 4 / 2; clone copies all three fields. The trip calculator UI shows and edits the two numeric fields on structured trips and shows the mode read-only. No planning behavior changes yet — this slice is demoable as "create a trip, see structured defaults in the calculator; old trips read legacy."

## Goal

Every trip carries an explicit snack model with configurable snacks-per-day and oz-per-snack, existing trips are frozen as legacy, and the new unit tables exist — so every later slice can gate on `snack_model` and build on the tables.

## Type

AFK

## Blocked by

None - can start immediately.

## User stories addressed

- User story 1 (new trips structured by default)
- User story 2 (old trips stay legacy)
- User story 10 (configurable per trip)
- User story 11 (clone copies model + config)

## Acceptance criteria

- [x] `venv/bin/pytest` passes; migration test proves a pre-migration DB backfills every existing trip to `snack_model='legacy'` and creates the three tables.
- [x] A legacy trip's `GET /api/trips/{id}/summary` response is identical before and after the migration (assert in a test by comparing full dicts).
- [x] `POST /api/trips` returns `snack_model='structured'`, `snacks_per_day=4`, `oz_per_snack=2` without the client sending them.
- [x] `POST /api/trips/{id}/clone` on a trip with non-default values copies all three fields exactly.
- [x] `PUT /api/trips/{id}` can update `snacks_per_day` and `oz_per_snack`; `snack_model` is accepted on update (no dedicated UI affordance, per spec Out of Scope).
- [x] Trip calculator shows "Snacks/day" and "Oz/snack" inputs for a structured trip and hides them for a legacy trip; `pnpm lint && pnpm build && pnpm test` pass.

## Owns

- `backend/models.py` — `Trip` (3 new columns); new classes `SnackUnitType`, `SnackUnitIngredient`, `TripSnackUnit`
- `backend/migrations.py` — new `_migration_3_structured_snacks`, `MIGRATIONS` tuple
- `backend/schemas.py` — trip schemas only (`TripCreate`, `TripUpdate`, `TripDetailRead`, `TripListRead` as needed)
- `backend/services/trip_queries.py` — `trip_detail_view`, `trip_list_view` (expose the 3 fields; nothing else)
- `backend/services/trip_planning.py` — trip create/clone paths (copy the 3 fields on clone)
- `backend/tests/test_migrations.py` — new migration cases
- `backend/tests/test_trip_workflows.py` — create/clone/update defaults
- `frontend/src/components/TripCalculator.jsx` + `TripCalculator.test.jsx` — the two new inputs
- `frontend/src/api.js` — trip payload fields if needed

## Must not touch

- `backend/services/catalog_queries.py` — owned by plan `2026-08-06-02-snack-unit-library.md`
- `backend/routers/snacks.py`, any new library router — owned by plan `2026-08-06-02`
- `backend/services/autofill.py`, `backend/services/daily_plan_queries.py`, `backend/routers/daily_plan.py` — owned by plan `2026-08-06-04`
- `trip_summary_view`, `packing_view`, `shopping_view` in `backend/services/trip_queries.py` — owned by plans `2026-08-06-03` / `2026-08-06-05`
- `backend/mcp_server.py` — owned by plan `2026-08-06-06`
- `frontend/src/components/SnackSelection.jsx` — owned by plan `2026-08-06-03`

## Defines interfaces

- `Trip.snack_model` / `snacks_per_day` / `oz_per_snack` columns + trip read/write schemas — consumed by plans 02–06
- Tables/models `SnackUnitType`, `SnackUnitIngredient`, `TripSnackUnit` — consumed by plans 02, 03, 04, 05, 06

## Pattern exemplar

- **MUST follow the pattern in**: `backend/migrations.py` — `_migration_2_trip_cascades` + `_add_column_if_missing` (ordered idempotent migration, appended to `MIGRATIONS`)
- Follow the pattern in: `backend/models.py` — `RecipeIngredient` for the composition table shape; `Trip`'s existing default columns (`oz_per_day`, `cal_per_oz`) for the config fields

## Tasks

- [x] Add the three trip columns and three new model classes to `models.py` (unit type: name, notes; composition: unit_type_id FK, ingredient_id FK, amount_oz; trip unit: trip_id FK cascade, nullable catalog_item_id FK, nullable unit_type_id FK, quantity, packed, actual_weight_oz, trip_notes).
- [x] Write `_migration_3_structured_snacks`: add columns (backfill `snack_model='legacy'` on existing rows, defaults 4/2), create tables; append to `MIGRATIONS`.
- [x] Default new trips to `structured` at creation; copy the three fields in clone.
- [x] Expose fields through trip schemas and `trip_detail_view` / `trip_list_view`.
- [x] Migration + workflow tests, including the legacy-summary-unchanged invariant.
- [x] Trip calculator inputs (structured trips only) + component test.

## Implementation notes

Existing rows must backfill to `legacy` inside the migration; the column default for *new* rows is applied at the create-trip code path (set `structured` explicitly there), not via the SQLite column default — a column default of `structured` would silently apply to any INSERT that omits it, which is exactly what the backfill must avoid racing with. Keep the column default `legacy` and set `structured` in the create path.
