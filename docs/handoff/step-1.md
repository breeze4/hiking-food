# Step 1: Configurable Trip Calorie/Weight Targets

## New Trip model fields

- `oz_per_day_low` (Float, default 19) — low end of daily oz target
- `oz_per_day_high` (Float, default 24) — high end of daily oz target
- `cal_per_oz` (Float, default 125) — calories per oz estimate

## New schema fields

- **TripCreate**: `oz_per_day_low: float = 19.0`, `oz_per_day_high: float = 24.0`, `cal_per_oz: float = 125.0`
- **TripUpdate**: all three as `Optional[float] = None`
- **TripDetailRead**: all three as `Optional[float]` with defaults matching model defaults

## Updated calculator signature

```python
def compute_trip_targets(first_day_fraction, full_days, last_day_fraction, meal_weights=None, oz_per_day_low=19, oz_per_day_high=24, cal_per_oz=125)
```

## Files modified

- `backend/models.py` — added 3 columns to Trip
- `backend/main.py` — added 3 migration lines in `_run_migrations()`
- `backend/schemas.py` — updated TripCreate, TripUpdate, TripDetailRead
- `backend/calculator.py` — parameterized constants
- `backend/routers/trips.py` — pass trip values to `compute_trip_targets`, copy fields in `clone_trip`, include in `_build_trip_detail`
- `backend/routers/daily_plan.py` — use trip values for `cal_per_full_day`
- `backend/tests/test_calculator.py` — added `test_custom_targets`
- `frontend/src/components/TripCalculator.jsx` — added 3 inputs, use form values for calculations
