# Configurable Trip Calorie/Weight Targets

## Problem
The Skurka method constants (19-24 oz/day, 125 cal/oz) are hardcoded in `backend/calculator.py` and duplicated in `TripCalculator.jsx`. Different trips may call for different targets — shorter/easier trips might use lower numbers, winter trips higher.

## Solution
Add three new columns to the `trips` table with the current Skurka defaults:
- `oz_per_day_low` (default 19)
- `oz_per_day_high` (default 24)
- `cal_per_oz` (default 125)

These appear in the Trip Calculator UI section alongside the existing day fraction inputs.

## Data Flow
- `compute_trip_targets()` accepts these three values as parameters instead of using hardcoded constants
- Trip summary endpoint passes them from the trip record
- Daily plan endpoint uses them for per-day calorie targets
- Frontend TripCalculator reads/writes them like the existing fields
- Frontend TripCalculator computes the display values using these instead of hardcoded 19/24/125

## Behavior
- New trips get the defaults (19, 24, 125)
- Cloned trips copy the source trip's values
- Existing trips with NULL columns use the defaults (handled in backend)
