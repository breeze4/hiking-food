## Problem Statement

The app tracks calories and weight for trip food planning, but has no visibility into macronutrient balance (protein, fat, carbs). A user can accidentally build a trip plan that's heavily skewed toward one macro — e.g., all carb-heavy snacks with little protein for recovery — and not notice until they're on the trail.

## Solution

Add protein, fat, and carb tracking (grams per oz) to the ingredient model. Macros roll up everywhere calories already do: per-ingredient, per-recipe, per-snack, per-day, per-trip. At item level, show grams. At aggregate levels (trip summary, daily plan), show percentage breakdown compared to a global macro target the user configures once.

Calories can be entered directly (e.g., coffee = 5 cal) or derived from macros when present (protein*4 + fat*9 + carb*4). Whichever the user most recently set wins. If all three macro fields are populated, calories are derived from them. If macros are null, the direct calories_per_oz value is used.

Macro data can be populated manually via the UI, or externally by an agent that researches values from USDA FoodData Central or package labels and writes them via the existing API.

## User Stories

1. As a trip planner, I want to see protein/fat/carb grams per oz on each ingredient, so that I can evaluate whether an ingredient is protein-heavy or carb-heavy.
2. As a trip planner, I want to see macro grams roll up on each recipe (total protein, fat, carb grams), so that I can compare breakfasts or dinners by macro balance.
3. As a trip planner, I want to see macro grams on each snack catalog item (per serving), so that I can choose snacks that fill a macro gap.
4. As a trip planner, I want to see a macro percentage breakdown on the trip summary (e.g., 22% protein / 35% fat / 43% carb), so that I know whether my overall plan is balanced.
5. As a trip planner, I want to set a global macro target ratio (e.g., 20% protein / 30% fat / 50% carb), so that the app can show me how my actual plan compares.
6. As a trip planner, I want to see actual vs. target macro percentages on the trip summary, so that I can identify imbalances before buying food.
7. As a trip planner, I want to see per-day macro breakdown on the daily plan, so that I can check whether individual days are balanced, not just the trip average.
8. As a trip planner, I want calories to be automatically derived from macros when I enter protein/fat/carb values, so that I don't have to calculate calories separately.
9. As a trip planner, I want to enter calories directly without macros for simple items (coffee, tea), so that I'm not forced to research macros for trivial items.
10. As a trip planner, I want to edit protein/fat/carb fields inline on the ingredients table, so that populating macro data follows the same workflow as editing other fields.
11. As a trip planner, I want an external agent to be able to populate macro data via the API, so that I don't have to manually research and enter values for every ingredient.
12. As a trip planner, I want to see which ingredients are missing macro data, so that I know what still needs to be researched.
13. As a trip planner, I want the macro percentage display to gracefully handle partial data (some ingredients have macros, some don't), so that I get useful information even before all ingredients are populated.
14. As a trip planner, I want the snack selection and meal selection views to show macro info, so that I can make macro-informed decisions when building a trip plan.

## Implementation Decisions

### Data Model

**Ingredient table** — add three nullable columns:
- `protein_per_oz` (REAL, grams)
- `fat_per_oz` (REAL, grams)
- `carb_per_oz` (REAL, grams)

**Calorie derivation rule**: If all three macro fields are non-null, `calories_per_oz` is computed as `protein*4 + fat*9 + carb*4`. If any macro field is null, the existing `calories_per_oz` value is used directly. On the API: when a client sets macro fields, the backend recomputes and stores `calories_per_oz`. When a client sets `calories_per_oz` directly, the backend nulls out the macro fields (they become unknown).

**App settings table** (new) — stores the global macro target:
- `macro_target_protein_pct` (REAL, default 20)
- `macro_target_fat_pct` (REAL, default 30)
- `macro_target_carb_pct` (REAL, default 50)

This is a single-row settings table. Not per-trip.

### API Changes

**Ingredient endpoints** — accept and return `protein_per_oz`, `fat_per_oz`, `carb_per_oz`. No new endpoints needed; the existing CRUD handles it.

**Settings endpoint** — new `GET /api/settings` and `PUT /api/settings` for the global macro targets.

**Trip summary endpoint** — add to existing response:
- `macro_actual`: `{protein_pct, fat_pct, carb_pct, protein_g, fat_g, carb_g}`
- `macro_target`: `{protein_pct, fat_pct, carb_pct}`

**Daily plan endpoint** — add per-day macro breakdown to each day object:
- `macros`: `{protein_g, fat_g, carb_g, protein_pct, fat_pct, carb_pct}`

**Recipe detail** — add macro totals to recipe response (protein_g, fat_g, carb_g total for the recipe).

**Snack catalog** — add macro per-serving to snack response (protein_per_serving, fat_per_serving, carb_per_serving, derived from ingredient macros * weight_per_serving / 16... no, weight_per_serving is already in oz, so: macro_per_serving = ingredient_macro_per_oz * weight_per_serving).

### Macro Rollup Logic

All macro rollups follow the same pattern as calorie rollups:
- **Recipe**: sum(ingredient.macro_per_oz * amount_oz) for each macro
- **Snack serving**: ingredient.macro_per_oz * weight_per_serving
- **Trip meal**: recipe macro totals * quantity
- **Trip snack**: snack macro per serving * servings
- **Trip summary**: sum all trip meal + trip snack macros, compute percentages from total macro grams using calorie equivalents (p*4, f*9, c*4)
- **Daily plan day**: sum macros of assigned items for that day

When an ingredient has null macros, it contributes zero to macro rollups but still contributes its calories_per_oz to calorie totals. The percentage breakdown is computed only from ingredients that have macro data. The UI should indicate when macro coverage is incomplete (e.g., "macros based on 85% of total calories").

### Frontend Changes

**Ingredients page**: Add protein, fat, carb columns to the table. Same inline editing pattern as existing columns.

**Recipe edit page**: Show macro totals alongside existing weight/calorie totals.

**Snack catalog page**: Show macro per-serving columns.

**Trip summary**: Add a macro balance section showing actual vs. target percentages. If macro data is incomplete, show coverage percentage.

**Daily plan**: Add per-day macro breakdown. Could be additional data in the day cards or integrated into the stacked bar chart.

**Settings**: A simple form somewhere (could be a modal from the header, or a dedicated settings page) for setting the three target percentages. Must sum to 100%.

### Partial Data Handling

The system must work gracefully when only some ingredients have macros:
- Calorie tracking continues to work exactly as before for ingredients without macros
- Macro percentages are computed from the subset of calories that have macro data
- The UI shows a "coverage" indicator: e.g., "Macro data covers 85% of trip calories"
- This encourages populating macros without blocking the workflow

## Testing Decisions

Good tests verify external behavior through public interfaces, not implementation details. Tests should answer "does the system produce the right output given this input?" not "does this internal function get called?"

### What to test

- **Macro rollup calculations**: Given ingredients with known macros, verify recipe totals, snack serving macros, trip summary macros, and daily plan day macros are correct. This is the core logic and the most likely place for bugs.
- **Calorie derivation**: Given macro values, verify calories_per_oz is computed correctly. Given direct calories with null macros, verify calories_per_oz is used as-is. Verify that setting macros recomputes calories, and setting calories directly nulls macros.
- **Partial data**: Given a mix of ingredients with and without macros, verify that calorie totals are correct for all items, macro percentages are computed from the subset with data, and coverage percentage is accurate.
- **Settings CRUD**: Verify the settings endpoint stores and returns macro targets, and that percentages must sum to 100.

### Prior art

Existing tests in `backend/tests/` use the FastAPI test client (`TestClient`) with an in-memory SQLite database. Follow the same pattern: create test data via API, then verify responses. See `test_daily_plan.py` for the most comprehensive example of testing computed rollups.

## Out of Scope

- Per-trip macro targets (global only for now)
- Fiber, sodium, or other micronutrients
- Automatic API lookup from USDA/Nutritionix built into the app UI (agents handle this externally)
- Frontend tests (no existing frontend test infrastructure)
- Macro-aware food planning agent logic (agent can read the data, but smart macro-balancing suggestions are a separate feature)

## Further Notes

- The USDA FoodData Central API (https://fdc.nal.usda.gov/api-guide) is free and covers most bulk hiking food ingredients. An external agent can search it and populate macro data via the ingredient API.
- The 4/4/9 calorie conversion (protein 4 cal/g, carb 4 cal/g, fat 9 cal/g) is standard and sufficient for this use case. Alcohol (7 cal/g) is out of scope.
- Default macro targets (20/30/50) are a reasonable starting point for hiking. The user sets this once and forgets it.
