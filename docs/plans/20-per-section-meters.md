# Plan 20: Per-Section Meters & Summary Relayout

**Spec**: [05-per-section-meters.md](../specs/05-per-section-meters.md)

## Overview

Move summary from sidebar to full-width top section. Add inline calorie + weight meters to each food section header. Extract ProgressMeter to its own module with a compact variant.

## Phase 1: Lift summary data into TripContext

Currently `TripSummary` fetches `/trips/{id}/summary` in its own `useEffect`. Multiple components will now need this data (section meters + top summary). Add `summary` to `TripContext` so it's fetched once and available everywhere.

- [x] Add `summary` state + fetch to `TripContext`
- [x] Re-fetch summary whenever `tripDetail` changes (same trigger as current)
- [x] Remove local fetch from `TripSummary`, consume from context instead

## Phase 2: Extract ProgressMeter to shared module

- [x] Move `ProgressMeter` from `TripSummary.jsx` into `frontend/src/components/ProgressMeter.jsx`
- [x] Add a `compact` prop: when true, shorter bar height (h-1.5 vs h-2), actual/target shown inline with label row, omits delta text
- [x] Export both `ProgressMeter` and the `CategorySection` helper (renamed if needed)
- [x] Update `TripSummary` imports

## Phase 3: Restructure TripPlannerPage layout

- [x] Remove the two-column flex layout (left content + right sidebar)
- [x] Remove the mobile-only `TripSummary` at bottom
- [x] Insert `TripSummary` as full-width section between `TripCalculator` and `MealSelection`
- [x] All sections now stack vertically full-width

## Phase 4: Redesign TripSummary as top summary section

Replace the sidebar card with a full-width summary containing three parts:

- [x] **Combined totals**: Two full-width `ProgressMeter` bars (total calories, total weight) + lbs conversion + per-day stats
- [x] **Category grid**: Table with 5 rows (breakfast, dinner, lunch, snacks, drink mixes) × 2 columns (cal bar, weight bar) using compact ProgressMeter
- [x] **Text stats**: cal/day, oz/day, cal/oz — displayed inline
- [x] Mobile: category grid stacks vertically (each category = cal bar then weight bar)

Target computations for the grid rows:
- Breakfast/dinner: same ±10% of per-unit-average × days logic (existing `CategorySection`)
- Lunch/snacks: cal targets from `slot_subtotals`; weight targets = `(daytime_weight - drink_mix_weight) × slot_pct` with ±10%
- Drink mixes: cal/weight targets from average per-serving × budget servings (computed client-side from trip snacks data)

## Phase 5: Add inline meters to MealSelection header

- [x] Read `summary` from `useTrip()` context
- [x] Below the "Meals" title/badge, render two compact ProgressMeters for breakfast (cal + weight) using the CategorySection target logic
- [x] Render two compact ProgressMeters for dinner (cal + weight)
- [x] Stack vertically on mobile

## Phase 6: Add inline meters to SnackSelection section headers

- [x] Read `summary` from `useTrip()` context
- [x] **DrinkMixSection header**: Add cal + weight + servings meters. Cal/weight targets = average per-serving across selected mixes × budget. Servings meter uses existing budget logic. Replace the text-only budget line.
- [x] **SlotSection header** (lunch, snacks): Add cal + weight meters. Cal targets from `slot_subtotals`. Weight targets computed as `(daytime_weight - drink_mix_weight) × slot_pct` with ±10% band.
- [x] Stack meters vertically on mobile

## Notes

- No backend changes needed — all data available from existing summary endpoint
- Slot weight targets: backend only provides cal targets in `slot_subtotals`. Weight targets for lunch (40%) and snacks (60%) are computed client-side from `daytime_weight_low/high - drink_mix_weight` × percentage.
- Drink mix cal/weight targets: approximate by design. If no mixes selected, hide those meters.

## Review

All phases implemented. Changes:

1. **TripContext** (`frontend/src/context/TripContext.jsx`): Added `summary` state, `loadSummary` callback, and bundled it into `refreshTrip` so summary updates alongside trip detail.
2. **ProgressMeter** (`frontend/src/components/ProgressMeter.jsx`): New shared module. Supports `compact` prop for shorter bars with inline actual/target text.
3. **TripPlannerPage** (`frontend/src/pages/TripPlannerPage.jsx`): Removed two-column sidebar layout. Now single-column: Calculator → Summary → Meals → Snacks.
4. **TripSummary** (`frontend/src/components/TripSummary.jsx`): Full-width card with combined total meters, text stats, and 5-row category grid (breakfast, dinner, lunch, snacks, drink mixes) with compact cal + weight bars. Desktop shows grid columns; mobile stacks.
5. **MealSelection** (`frontend/src/components/MealSelection.jsx`): Added `MealMeters` component showing breakfast and dinner cal/weight bars below the card header.
6. **SnackSelection** (`frontend/src/components/SnackSelection.jsx`): Added `SlotMeters` (cal + weight per slot) and `DrinkMixMeters` (cal + weight + servings) to section headers. Removed old text-only budget line from drink mixes.
