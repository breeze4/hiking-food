# Issue #5: Recipe Library — CRUD API + Browse/Edit UI

## Context
The recipe library holds breakfast and dinner recipes, each with a nested ingredient list and computed nutritional totals. Recipes are a core building block — trip meal selection (later issues) pulls from this library. This issue adds the full CRUD backend with a computation engine for totals, plus a frontend for browsing by category and editing recipes with their ingredient lists.

## Assumptions
- Issue #2 (scaffolding) is done: backend runs, all DB tables exist including `recipes` and `recipe_ingredients`
- Issue #3 (ingredients) is done: `backend/routers/ingredients.py` with full CRUD, ingredient schemas exist
- Issue #4 (snack catalog) is done: established the `backend/schemas/` directory pattern with per-entity schema files
- The `recipes` table has columns: id, name, category, at_home_prep, field_prep, notes
- The `recipe_ingredients` table has columns: id, recipe_id, ingredient_id, amount_oz
- Frontend has a working nav, api client (`frontend/src/api.js`), and page routing pattern

## Plan

### Step 1: Backend — Pydantic schemas for recipes
Create `backend/schemas/recipe.py` with:
- `RecipeIngredientCreate`: ingredient_id (int), amount_oz (float)
- `RecipeIngredientResponse`: id, ingredient_id, ingredient_name (str), amount_oz, calories (computed: amount_oz × ingredient.calories_per_oz)
- `RecipeBase`: name (str), category (str, validated to breakfast|dinner), at_home_prep (optional str), field_prep (optional str), notes (optional str)
- `RecipeCreate(RecipeBase)`: adds ingredients list of RecipeIngredientCreate
- `RecipeUpdate`: all fields optional, includes optional ingredients list
- `RecipeListResponse`: id, name, category, total_weight, total_calories, cal_per_oz (summary for list view)
- `RecipeDetailResponse(RecipeBase)`: id, ingredients list of RecipeIngredientResponse, total_weight, total_calories, cal_per_oz

**Files**: `backend/schemas/recipe.py`
**Verify**: Backend starts without errors.

### Step 2: Backend — Recipe computation logic
Create `backend/services/recipe_calc.py` with pure functions:
- `compute_recipe_totals(ingredients_with_cal_per_oz)` → returns total_weight, total_calories, cal_per_oz
- total_weight = sum of amount_oz across all recipe ingredients
- total_calories = sum of (amount_oz × ingredient.calories_per_oz) for each ingredient
- cal_per_oz = total_calories / total_weight (0 if total_weight is 0)

Keep this as standalone functions with no DB dependency so it's easy to unit test.

**Files**: `backend/services/__init__.py`, `backend/services/recipe_calc.py`
**Verify**: Backend starts without errors.

### Step 3: Backend — Unit tests for recipe computation
Write pytest tests in `backend/tests/test_recipe_calc.py`:
- Empty ingredients list → all zeros
- Single ingredient → totals match that ingredient's contribution
- Known Skurka data: Quickstart Cereal (4.5 oz total, 617 cal, ~137 cal/oz)
- Multiple ingredients with different cal/oz values

**Files**: `backend/tests/__init__.py`, `backend/tests/test_recipe_calc.py`
**Verify**: `pytest backend/tests/test_recipe_calc.py` — all tests pass.

### Step 4: Backend — CRUD router for recipes
Create `backend/routers/recipes.py` with:
- `GET /api/recipes` — list all recipes with computed totals, optional query param `?category=breakfast|dinner` for filtering
- `GET /api/recipes/{id}` — full detail with nested ingredient list and computed totals, 404 if not found
- `POST /api/recipes` — create recipe with nested ingredients in one request, validate all ingredient_ids exist, return full detail response
- `PUT /api/recipes/{id}` — update recipe fields and/or replace ingredient list, 404 if not found
- `DELETE /api/recipes/{id}` — delete recipe and cascade delete its recipe_ingredients, 404 if not found. If recipe is referenced by trip_meals, return 409 with message.

Register router in `backend/main.py`.

**Files**: `backend/routers/recipes.py`, `backend/main.py`
**Verify**: curl all five endpoints. Create a recipe with ingredients, confirm GET returns correct computed totals. Confirm category filter works on list endpoint.

### Step 5: Frontend — Recipe list page with category tabs
Create `frontend/src/pages/RecipesPage.jsx`:
- Add route `/recipes` and nav link
- Fetch `GET /api/recipes` on mount
- Category filter tabs: All / Breakfast / Dinner (client-side filter or query param)
- Table/card list showing: name, category, total weight, total calories, cal/oz
- Click a recipe to navigate to detail/edit view

**Files**: `frontend/src/pages/RecipesPage.jsx`, `frontend/src/App.jsx` (add route + nav)
**Verify**: Navigate to /recipes, see empty state. Create a recipe via curl, refresh, see it in the list. Category tabs filter correctly.

### Step 6: Frontend — Recipe detail/edit page (metadata only)
Create `frontend/src/pages/RecipeEditPage.jsx`:
- Route: `/recipes/:id` for editing, `/recipes/new` for creating
- Form fields: name, category (dropdown: breakfast/dinner), at_home_prep (textarea), field_prep (textarea), notes (textarea)
- Save button calls POST (new) or PUT (edit)
- Back/cancel navigates to recipe list
- No ingredient editing yet — just the recipe metadata

**Files**: `frontend/src/pages/RecipeEditPage.jsx`, `frontend/src/App.jsx` (add routes)
**Verify**: Create a new recipe via the UI with name and category. Edit an existing recipe's prep instructions. Changes persist on reload.

### Step 7: Frontend — Ingredient list editor within recipe
Add ingredient management to `RecipeEditPage.jsx`:
- Display current ingredients as a list: ingredient name, amount_oz, computed calories for that line
- "Add ingredient" row: dropdown of available ingredients (fetched from `GET /api/ingredients`), amount_oz input
- Remove button per ingredient row
- Computed totals displayed below the list: total weight, total calories, cal/oz
- Totals update live as ingredients are added/changed/removed (compute client-side for responsiveness)
- Save sends full ingredient list with the PUT/POST request

**Files**: `frontend/src/pages/RecipeEditPage.jsx` (or extract an `IngredientListEditor` component)
**Verify**: Add ingredients to a recipe, see totals update. Remove an ingredient, totals update. Save, reload, ingredients and totals persist correctly. Verify against Skurka test data if available.

### Step 8: Frontend — Delete recipe
Add delete button on RecipeEditPage (or recipe list):
- Confirm dialog before delete
- Calls `DELETE /api/recipes/{id}`
- If 409 (used in active trips), show warning message
- On success, navigate back to recipe list

**Files**: `frontend/src/pages/RecipeEditPage.jsx` (or `RecipesPage.jsx`)
**Verify**: Delete a recipe not used in any trip — removed from list. Attempt delete of a recipe referenced by trip_meals (seed via curl) — see 409 warning.

## Files Summary

| Action | Path |
|--------|------|
| Create | `backend/schemas/recipe.py` |
| Create | `backend/services/__init__.py` |
| Create | `backend/services/recipe_calc.py` |
| Create | `backend/tests/__init__.py` |
| Create | `backend/tests/test_recipe_calc.py` |
| Create | `backend/routers/recipes.py` |
| Modify | `backend/main.py` |
| Create | `frontend/src/pages/RecipesPage.jsx` |
| Create | `frontend/src/pages/RecipeEditPage.jsx` |
| Modify | `frontend/src/App.jsx` |

## Verification
1. `pytest backend/tests/test_recipe_calc.py` — all computation tests pass including Skurka reference data
2. Backend: all five CRUD endpoints respond correctly via curl
3. GET /api/recipes returns computed totals matching manual calculation
4. GET /api/recipes?category=breakfast filters correctly
5. POST creates recipe with nested ingredients in one request
6. Frontend: recipe list page displays recipes, category tabs filter
7. Frontend: can create a new recipe with metadata via form
8. Frontend: can add/remove ingredients with live-updating totals
9. Frontend: can edit all fields of existing recipe
10. Frontend: delete works with trip-reference protection (409)
11. Data persists across full page reloads
