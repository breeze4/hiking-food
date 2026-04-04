# Plan 33: Configurable Trip Calorie/Weight Targets

Spec: [docs/specs/11-configurable-trip-targets.md](../specs/11-configurable-trip-targets.md)

## Changes

### Backend

- [x] Add columns to `Trip` model: `oz_per_day_low` (Float, default 19), `oz_per_day_high` (Float, default 24), `cal_per_oz` (Float, default 125)
- [x] Add migration to alter `trips` table with the three new columns
- [x] Update `TripCreate`, `TripUpdate`, `TripDetailRead` schemas to include the new fields
- [x] Update `compute_trip_targets()` to accept `oz_per_day_low`, `oz_per_day_high`, `cal_per_oz` as parameters instead of hardcoded constants
- [x] Update call site in `routers/trips.py` (summary endpoint) to pass trip's values
- [x] Update call site in `routers/daily_plan.py` to use trip's values for `cal_per_full_day`
- [x] Update `clone_trip` to copy the three new fields
- [x] Update tests in `test_calculator.py`

### Frontend

- [x] Update `TripCalculator.jsx`: add three new inputs (oz/day low, oz/day high, cal/oz) to the form state and save logic
- [x] Update `TripCalculator.jsx`: use form values instead of hardcoded 19/24/125 for display calculations
