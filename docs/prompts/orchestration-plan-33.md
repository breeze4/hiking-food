# Orchestration Prompt: Configurable Trip Targets (Plan 33)

## Project context

- Working directory: `/home/breeze/dev/hiking-food`
- Build: `cd frontend && npm run build`
- Test: `cd backend && venv/bin/pytest`
- Dev: `cd backend && uvicorn main:app --reload` + `cd frontend && npm run dev`
- Spec: `docs/specs/11-configurable-trip-targets.md`
- Plan: `docs/plans/33-configurable-trip-targets.md`
- Handoff directory: `docs/handoff/` (create if needed)

## Orchestrator responsibilities

This is a single-plan, single-agent execution. You are spawning one implementation agent with full context pre-loaded. Before launching:

1. Read all files listed under "Context sources" and inline the relevant sections into the agent's "Context" field.
2. After the agent completes, run the build/test gate.
3. Commit the changes.

## Agent granularity rules

**One agent for this plan.** It has 10 tasks across backend + frontend, all tightly coupled (model columns → calculator → endpoints → UI). Splitting would create unnecessary handoff overhead.

## Execution plan

### Step 1 — Configurable trip targets (backend + frontend)

**Plan**: `docs/plans/33-configurable-trip-targets.md`

**Agent briefing**: Configurable trip calorie/weight targets
- **Context sources** (orchestrator reads these before launch):
  - `backend/calculator.py` (full file, 42 lines)
  - `backend/models.py` lines 54-63 (Trip class)
  - `backend/schemas.py` lines 166-256 (Trip schemas + TripDetailRead)
  - `backend/main.py` lines 23-26 (`_add_column_if_missing` helper) and lines 52-60 (`_run_migrations`)
  - `backend/routers/trips.py` lines 321-326 (`compute_trip_targets` call site) and lines 567-573 (clone)
  - `backend/routers/daily_plan.py` lines 82-85 (hardcoded `cal_per_full_day` calculation)
  - `frontend/src/components/TripCalculator.jsx` (full file, 131 lines)
  - `backend/tests/test_calculator.py` (full file)
- **Read first**: `docs/plans/33-configurable-trip-targets.md`
- **Context**: <orchestrator pastes the above file contents here>

- **Owns**:
  - `backend/models.py` (Trip class only)
  - `backend/schemas.py` (Trip-related schemas only)
  - `backend/calculator.py`
  - `backend/main.py` (`_run_migrations` function only)
  - `backend/routers/trips.py` (summary endpoint + clone function only)
  - `backend/routers/daily_plan.py` (cal_per_full_day calculation only)
  - `backend/tests/test_calculator.py`
  - `frontend/src/components/TripCalculator.jsx`

- **Must not touch**: ingredient/snack/recipe models, app_settings, any other frontend components, daily plan UI, packing screen, seed data

- **MUST follow the pattern in**:
  - `backend/main.py` `_run_migrations`: add three `_add_column_if_missing` calls for the new trip columns, same style as existing calls. Use `"REAL DEFAULT 19"`, `"REAL DEFAULT 24"`, `"REAL DEFAULT 125"` as col_type.
  - `backend/models.py`: same Column style as `drink_mixes_per_day`
  - `backend/schemas.py`: same Optional pattern as existing TripUpdate fields; defaults in TripCreate

- **Implementation notes**:
  - `compute_trip_targets()` signature: add `oz_per_day_low=19`, `oz_per_day_high=24`, `cal_per_oz=125` keyword args. Replace hardcoded 19/24/125 inside the function body with these params.
  - In `routers/trips.py` summary endpoint: pass `trip.oz_per_day_low or 19`, `trip.oz_per_day_high or 24`, `trip.cal_per_oz or 125` to `compute_trip_targets()`.
  - In `routers/daily_plan.py`: replace `(19 + 24) / 2 * 125` with `((trip.oz_per_day_low or 19) + (trip.oz_per_day_high or 24)) / 2 * (trip.cal_per_oz or 125)`.
  - In `clone_trip`: copy `oz_per_day_low`, `oz_per_day_high`, `cal_per_oz` from source trip.
  - In `TripCalculator.jsx`: add `oz_per_day_low`, `oz_per_day_high`, `cal_per_oz` to form state (defaulting from `tripDetail` with fallbacks 19/24/125). Add three inputs in the flex row. Update lines 30-33 to use `form.oz_per_day_low` etc. instead of hardcoded values.
  - In `TripDetailRead`: add the three fields as `Optional[float]` with defaults.
  - Existing calculator tests: update to pass the new params explicitly (or rely on defaults — either way, verify they still pass).

- **Do not**: modify the frontend summary components, snack selection, meal selection, or daily plan page. Those consume the backend's computed targets and will automatically reflect the new values.

- **Done when**:
  1. `cd backend && venv/bin/pytest` passes
  2. `cd frontend && npm run build` succeeds
  3. Trip Calculator UI shows three new inputs (oz/day low, oz/day high, cal/oz)
  4. Changing those inputs updates the recommended weight/calorie ranges in the Trip Calculator display
  5. New trips get defaults (19, 24, 125)
  6. Cloned trips copy the source trip's values

- **Handoff**: Write `docs/handoff/step-1.md` listing: new Trip model fields, new schema fields, updated calculator signature, files modified.

**Gate**: `cd backend && venv/bin/pytest && cd ../frontend && npm run build`

## HITL checkpoints

None — this is a mechanical change with clear patterns. AFK-safe.

## Completion criteria

- All plan checkboxes marked complete
- `cd backend && venv/bin/pytest` passes
- `cd frontend && npm run build` succeeds
- 1 frontend component modified with no UI test coverage beyond build — consider a quick manual smoke test or agent-browser screenshot of the Trip Calculator after implementation
- Commit changes, update plan file and `docs/plans/INDEX.md` (move plan 33 to Completed)
