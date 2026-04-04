# Trip Summary Macro Breakdown

## Parent spec

`docs/specs/10-macronutrient-tracking.md`

## What to build

Aggregate macro grams across all trip meals and snacks in the trip summary endpoint. Compute percentage breakdown (using p*4, f*9, c*4 calorie equivalents). Track what percentage of total calories have macro data (coverage indicator). Display actual macro percentages in the trip summary UI.

## Type

AFK

## Blocked by

- Blocked by `28-recipe-macro-totals.md`
- Blocked by `29-snack-macro-per-serving.md`

## User stories addressed

- User story 4: See macro percentage breakdown on trip summary
- User story 6: See actual vs target macro percentages on trip summary
- User story 13: Gracefully handle partial data with coverage indicator

## Acceptance criteria

- [ ] Summary endpoint returns `macro_actual: {protein_g, fat_g, carb_g, protein_pct, fat_pct, carb_pct}`
- [ ] Percentages computed from macro calorie equivalents (p*4 / total_macro_cal, etc.)
- [ ] Summary endpoint returns `macro_coverage_pct` — what % of total trip calories come from ingredients with macro data
- [ ] When no ingredients have macro data, macro fields are null (not zero)
- [ ] Trip summary UI shows macro percentage breakdown
- [ ] Trip summary UI shows coverage indicator when coverage < 100% (e.g., "Based on 85% of calories")
- [ ] Tests verify aggregation across meals + snacks, partial data coverage, and all-null case

## Pattern exemplar

- Follow the pattern in: `backend/routers/trips.py` `get_trip_summary()` — extend the existing summary computation
- Follow the pattern in: `frontend/src/components/TripSummary.jsx` — where summary data is displayed

## Tasks

- [ ] Extend `get_trip_summary()` to aggregate macro grams from trip meals and snacks
- [ ] Compute macro percentages and coverage percentage
- [ ] Update TripSummaryRead schema with macro fields
- [ ] Update TripSummary component to display macro breakdown and coverage
- [ ] Write tests for macro aggregation (full data, partial data, no data)
