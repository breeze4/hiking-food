# Orchestration Prompt: Macronutrient Tracking

## Project context

- Working directory: `/home/breeze/dev/hiking-food`
- Build: `cd frontend && npm run build`
- Test: `cd backend && venv/bin/pytest`
- Lint: none
- Spec: `docs/specs/10-macronutrient-tracking.md`
- App spec: `docs/specs/02-app-spec.md`

## Commit policy

Git commit after completing each plan. Not batched. No AI co-author in commit messages.

## Agent granularity rules

**Default grain: one agent per plan.** Each plan file maps to one implementation agent. Do not split a plan across multiple agents, and do not combine multiple plans into one agent.

Exceptions:
- **Pre-flight exploration** uses a lightweight `Explore` agent before an implementation agent when the target code is unfamiliar.
- **Large plans (10+ tasks)**: split at natural phase boundaries. Each sub-agent gets a contiguous slice. Never split mid-task.
- **Never go smaller than a plan.** Tasks within a plan share context — splitting them across agents loses that context.

When in doubt, keep work in fewer agents.

## Execution plan

All six steps are serial. Plans 28 and 29 have no blocked-by relationship to each other, but both modify `backend/schemas.py`, so they must run sequentially to avoid merge conflicts.

---

### Step 1 — Ingredient macro fields + calorie derivation

**Plan**: `docs/plans/27-ingredient-macro-fields.md`

**Agent briefing**:
- **Read first**: `docs/plans/27-ingredient-macro-fields.md`, `docs/specs/10-macronutrient-tracking.md`, `backend/models.py`, `backend/schemas.py`, `backend/routers/ingredients.py`, `frontend/src/pages/IngredientsPage.jsx`
- **Owns**: `backend/models.py` (Ingredient model), `backend/schemas.py` (Ingredient schemas), `backend/routers/ingredients.py`, `frontend/src/pages/IngredientsPage.jsx`, new migration script in `backend/`, `backend/tests/`
- **Must not touch**: other routers, other pages, `services/`, `calculator.py`
- **Follow the pattern in**: `backend/migrations/` — use the most recent migration script for column addition format. For inline editing columns, follow the existing pattern in `IngredientsPage.jsx` (the `on_hand`, `essentials`, `packing_method` columns).
- **Calorie derivation rule**: When all three macro fields are non-null on a create/update, compute `calories_per_oz = protein*4 + fat*9 + carb*4` and store it. When `calories_per_oz` is set directly without macros (or macros are null), store calories as-is and null out macros. When both macros AND calories are provided, macros win.
- **Do not**: modify how existing calorie data works for ingredients that don't have macros. Existing data must continue to work unchanged.
- **Done when**: migration runs cleanly, ingredient CRUD accepts/returns macro fields, calorie derivation works in both directions, IngredientsPage shows 3 new editable columns, tests pass covering all derivation cases.

**Gate**: `cd frontend && npm run build && cd ../backend && venv/bin/pytest`

**Commit**: "Add macronutrient fields to ingredients with calorie derivation"

---

### Step 2 — Recipe macro totals

**Plan**: `docs/plans/28-recipe-macro-totals.md`

**Agent briefing**:
- **Read first**: `docs/plans/28-recipe-macro-totals.md`, `backend/services/recipe_calc.py`, `backend/routers/recipes.py`, `backend/schemas.py`, `frontend/src/pages/RecipeEditPage.jsx`
- **Owns**: `backend/services/recipe_calc.py`, `backend/schemas.py` (recipe-related schemas), `backend/routers/recipes.py`, `frontend/src/pages/RecipeEditPage.jsx`, `backend/tests/`
- **Must not touch**: `backend/models.py`, `backend/routers/ingredients.py`, `backend/routers/trips.py`, `backend/routers/daily_plan.py`, other frontend pages
- **Follow the pattern in**: `backend/services/recipe_calc.py` — extend `compute_recipe_totals()` to return `protein_g`, `fat_g`, `carb_g` alongside existing `total_weight` and `total_calories`. Same summing pattern: `ingredient.macro_per_oz * amount_oz`.
- **Prior step context**: Step 1 added `protein_per_oz`, `fat_per_oz`, `carb_per_oz` to the Ingredient model and schema. These fields are nullable. Verify they exist on the model before using them.
- **Do not**: modify how `_get_recipe_totals()` works in `trips.py` or `daily_plan.py` — those will be updated in later steps. Only touch `recipe_calc.py` and the recipe router/pages.
- **Done when**: `compute_recipe_totals()` returns macro grams, recipe API responses include macros, RecipeEditPage shows macro totals next to weight/calories, tests cover full/partial/no macro data.

**Gate**: `cd frontend && npm run build && cd ../backend && venv/bin/pytest`

**Commit**: "Add macronutrient totals to recipes"

---

### Step 3 — Snack catalog macro per-serving

**Plan**: `docs/plans/29-snack-macro-per-serving.md`

**Agent briefing**:
- **Read first**: `docs/plans/29-snack-macro-per-serving.md`, `backend/routers/snacks.py`, `backend/routers/trips.py` (specifically `_build_trip_snack`), `backend/schemas.py`, `frontend/src/pages/SnackCatalogPage.jsx`
- **Owns**: `backend/routers/snacks.py`, `backend/routers/trips.py` (`_build_trip_snack` function only), `backend/schemas.py` (snack-related schemas), `frontend/src/pages/SnackCatalogPage.jsx`, `backend/tests/`
- **Must not touch**: `backend/models.py`, `backend/services/`, `backend/routers/daily_plan.py`, recipe files, other frontend pages
- **Follow the pattern in**: `backend/routers/snacks.py` — the existing response-building where ingredient data is joined. Macro per-serving = `ingredient.macro_per_oz * weight_per_serving`. Same null-propagation: if ingredient macros are null, snack macros are null.
- **Prior step context**: Step 1 added macro fields to Ingredient. Step 2 updated schemas.py with recipe macro fields. Read the current state of schemas.py before modifying — don't duplicate or conflict with Step 2's additions.
- **Do not**: modify `_build_trip_meal`, the summary endpoint, or daily plan code. Only snack-related response building.
- **Done when**: snack catalog API returns macro per-serving, `_build_trip_snack` includes macro per-serving, SnackCatalogPage shows macro columns, tests pass.

**Gate**: `cd frontend && npm run build && cd ../backend && venv/bin/pytest`

**Commit**: "Add macronutrient per-serving to snack catalog"

---

### Step 4 — Trip summary macro breakdown

**Plan**: `docs/plans/30-trip-summary-macros.md`

**Agent briefing**:
- **Read first**: `docs/plans/30-trip-summary-macros.md`, `backend/routers/trips.py` (specifically `get_trip_summary`), `backend/schemas.py` (TripSummaryRead), `frontend/src/components/TripSummary.jsx`
- **Owns**: `backend/routers/trips.py` (`get_trip_summary` function), `backend/schemas.py` (TripSummaryRead), `frontend/src/components/TripSummary.jsx`, `backend/tests/`
- **Must not touch**: `backend/models.py`, `backend/services/`, `backend/routers/daily_plan.py`, other trip router functions (CRUD, packing, shopping list), other frontend pages
- **Prior step context**: Steps 2-3 added macro fields to recipe totals and snack responses. In `get_trip_summary`, recipe macros come from `compute_recipe_totals()` (now returns `protein_g`, `fat_g`, `carb_g`). Snack macros come from `ingredient.macro_per_oz * weight_per_serving * servings`. Read `recipe_calc.py` and `_build_trip_snack` to verify the actual field names.
- **Aggregation logic**: Sum macro grams across all trip meals and snacks. Compute percentages using calorie equivalents: `protein_pct = (protein_g * 4) / total_macro_calories * 100`. Track `macro_coverage_pct` = calories from ingredients with macro data / total trip calories * 100.
- **Do not**: add macro targets to this step (that's step 5). This step only computes actuals and coverage.
- **Done when**: summary endpoint returns `macro_actual` and `macro_coverage_pct`, TripSummary shows macro percentage breakdown with coverage indicator, tests cover full/partial/no macro data.

**Gate**: `cd frontend && npm run build && cd ../backend && venv/bin/pytest`

**Commit**: "Add macronutrient breakdown to trip summary"

---

### Step 5 — App settings + macro targets

**Plan**: `docs/plans/31-app-settings-macro-targets.md`

**Agent briefing**:
- **Read first**: `docs/plans/31-app-settings-macro-targets.md`, `backend/models.py`, `backend/main.py`, `backend/routers/trips.py` (get_trip_summary), `frontend/src/components/TripSummary.jsx`, `frontend/src/App.jsx` (for header/layout structure)
- **Owns**: `backend/models.py` (new AppSettings model), new `backend/routers/settings.py`, `backend/main.py` (router registration), `backend/schemas.py`, new migration script, `backend/routers/trips.py` (get_trip_summary — add targets to response), `frontend/src/components/TripSummary.jsx` (actual vs target display), new settings UI component, `backend/tests/`
- **Must not touch**: `backend/routers/daily_plan.py`, ingredient/recipe/snack routers, `backend/services/`
- **Follow the pattern in**: `backend/routers/ingredients.py` — simple router structure for the new settings endpoint. For the settings table: single-row, auto-created on first GET if not present.
- **Prior step context**: Step 4 added `macro_actual` and `macro_coverage_pct` to the trip summary response. This step adds `macro_target` alongside it so the frontend can show the comparison.
- **Settings UI**: keep it simple — a modal accessible from the app header, or a small settings page. Three number inputs that must sum to 100. Defaults: 20/30/50 (protein/fat/carb).
- **Do not**: add settings to the daily plan yet (that's step 6).
- **Done when**: settings table exists with defaults, GET/PUT /api/settings works, validation rejects percentages not summing to 100, trip summary shows actual vs target, settings UI allows editing targets, tests pass.

**Gate**: `cd frontend && npm run build && cd ../backend && venv/bin/pytest`

**Commit**: "Add app settings with macro targets and actual-vs-target display"

---

### Step 6 — Daily plan day macros

**Plan**: `docs/plans/32-daily-plan-macros.md`

**Agent briefing**:
- **Read first**: `docs/plans/32-daily-plan-macros.md`, `backend/routers/daily_plan.py` (specifically `_build_daily_plan_response`), `frontend/src/pages/DailyPlanPage.jsx`
- **Owns**: `backend/routers/daily_plan.py`, `frontend/src/pages/DailyPlanPage.jsx`, `backend/tests/`
- **Must not touch**: `backend/models.py`, `backend/routers/trips.py`, `backend/routers/settings.py`, `backend/services/`, other frontend pages
- **Prior step context**: Steps 2-3 added macros to recipe totals and snack info. Step 5 added the settings table and router. In `_build_daily_plan_response`, `meal_info` dicts come from `compute_recipe_totals()` (has `protein_g`, `fat_g`, `carb_g`). `snack_info` dicts need macro per-serving computed from ingredient macros. Settings come from `GET /api/settings` or direct DB query. Read the actual code to verify field names before using them.
- **Per-day computation**: For each day, sum macro grams from assigned items. Compute per-day percentages using calorie equivalents. Include `macro_target` from app settings in the response.
- **Follow the pattern in**: the existing day-object structure in `_build_daily_plan_response` — add `macros` dict alongside existing `target_calories`, `items`, etc.
- **Do not**: modify the auto-fill algorithm or assignment CRUD logic. Only the response building and frontend display.
- **Done when**: daily plan day objects include `macros` with grams and percentages, response includes `macro_target`, DailyPlanPage shows per-day macro info in day cards, tests cover per-day computation with mixed data.

**Gate**: `cd frontend && npm run build && cd ../backend && venv/bin/pytest`

**Commit**: "Add per-day macronutrient breakdown to daily plan"

---

## HITL checkpoints

None. All plans are AFK.

## Completion criteria

- All plan acceptance criteria met (plans 27-32)
- `cd frontend && npm run build && cd ../backend && venv/bin/pytest` passes
- Macro fields visible on ingredients, recipes, snacks, trip summary, and daily plan
- Calorie derivation works bidirectionally
- App settings store and serve macro targets
- Trip summary and daily plan show actual vs target percentages
- Partial data handled gracefully with coverage indicator
