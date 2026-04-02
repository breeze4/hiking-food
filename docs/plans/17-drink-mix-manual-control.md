# Drink Mix Manual Control

## Parent spec

`docs/specs/04-utility-audit.md`

## What to build

Replace auto-allocated drink mix servings with manual control. Remove the recalculation function, make servings editable in the UI, enforce whole-number servings, default new mixes to 1 serving, and add a budget meter showing total servings vs the mixes_per_day * total_days budget.

## Type

AFK

## Blocked by

None - can start immediately

## User stories addressed

- User story 5: Manually set drink mix servings
- User story 6: Whole-number servings only
- User story 7: Budget meter for mixes/day
- User story 8: New drink mix starts at 1 serving

## Acceptance criteria

- [x] `_recalc_drink_mix_servings()` and all call sites removed from backend
- [x] Updating trip days or mixes_per_day does NOT change existing drink mix servings
- [x] Drink mix servings editable in UI with +/- controls stepping by 1
- [x] Backend rounds up fractional drink_mix servings to whole numbers on write
- [x] Adding a drink mix to a trip defaults to 1 serving
- [x] Drink mix section shows budget meter: "X of Y budget servings" with color thresholds
- [x] Backend tests verify: no auto-recalculation, fractional rounding, default serving value

## Tasks

- [x] Remove `_recalc_drink_mix_servings()` function and its call sites in `backend/routers/trips.py`
- [x] Add whole-number rounding for drink_mix category on trip_snack create/update endpoints
- [x] Set default servings = 1 for drink_mix items when added to a trip
- [x] Make drink mix servings editable in `frontend/src/components/SnackSelection.jsx` DrinkMixSection (reuse +/- pattern, step by 1)
- [x] Remove "Servings auto-calculated" message from drink mix UI
- [x] Add budget meter to drink mix section: total servings vs mixes_per_day * total_days, with green/yellow/orange/red color thresholds
- [x] Add backend tests: no recalc on trip update, fractional rounding, default=1
