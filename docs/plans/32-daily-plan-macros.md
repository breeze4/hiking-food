# Daily Plan Day Macros

## Parent spec

`docs/specs/10-macronutrient-tracking.md`

## What to build

Add per-day macro breakdown to the daily plan. Each day object in the daily plan response includes total macro grams and percentages for the items assigned to that day. Daily plan UI shows per-day macro info in day cards, with actual vs target from app settings. Coverage indicator when partial data.

## Type

AFK

## Blocked by

- Blocked by `28-recipe-macro-totals.md`
- Blocked by `29-snack-macro-per-serving.md`
- Blocked by `31-app-settings-macro-targets.md`

## User stories addressed

- User story 7: See per-day macro breakdown on daily plan
- User story 13: Gracefully handle partial data

## Acceptance criteria

- [ ] Daily plan day objects include `macros: {protein_g, fat_g, carb_g, protein_pct, fat_pct, carb_pct}`
- [ ] Daily plan response includes `macro_target` from app settings
- [ ] Macro percentages computed per-day from assigned items' macro contributions
- [ ] Days with no macro data show null macros (not zero)
- [ ] Daily plan UI shows macro breakdown per day card (grams and/or percentages)
- [ ] Daily plan UI shows actual vs target comparison
- [ ] Coverage indicator when some assigned items lack macro data
- [ ] Tests verify per-day macro computation with mixed data

## Pattern exemplar

- Follow the pattern in: `backend/routers/daily_plan.py` `_build_daily_plan_response()` — extend the existing day-building logic
- Follow the pattern in: `frontend/src/pages/DailyPlanPage.jsx` — day card rendering in the grid

## Tasks

- [ ] Extend `_build_daily_plan_response()` to compute per-day macro grams and percentages
- [ ] Include macro targets from app settings in response
- [ ] Update daily plan day card UI to show macro breakdown
- [ ] Add actual vs target indicator per day
- [ ] Write tests for per-day macro computation (full, partial, empty data)
