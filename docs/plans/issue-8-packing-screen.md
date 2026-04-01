# Issue #8: Packing Screen

## Context
The packing screen is a dedicated packing-day view for use at home with a Chromebook and kitchen scale. It lets the user work through a trip's meals and snacks, checking off items as they're assembled/packed and recording actual measured weights. It also provides a combined shopping list aggregating all ingredients across the trip.

This depends on issues #2-7 being complete (scaffolding, ingredients, snack catalog, recipes, trip planner with meal/snack selection). The `trip_meals` and `trip_snacks` tables already have `packed` and `actual_weight_oz` columns from the original schema.

## Plan

### Step 1: Backend — PATCH endpoint for trip meals
Add `PATCH /api/trips/{trip_id}/meals/{meal_id}` to update `packed` (bool) and `actual_weight_oz` (float, nullable) on a trip_meal record.

- Pydantic schema: `TripMealPack` with both fields optional
- Validate meal belongs to the given trip
- Return updated record

**Files**: `backend/schemas/trip.py` (or new `packing.py`), `backend/routers/trips.py`
**Verify**: curl PATCH to toggle packed and set weight, confirm persistence

### Step 2: Backend — PATCH endpoint for trip snacks
Add `PATCH /api/trips/{trip_id}/snacks/{snack_id}` to update `packed` (bool) and `actual_weight_oz` (float, nullable) on a trip_snack record.

- Same pattern as step 1
- Validate snack belongs to the given trip

**Files**: `backend/schemas/trip.py`, `backend/routers/trips.py`
**Verify**: curl PATCH to toggle packed and set weight, confirm persistence

### Step 3: Backend — Shopping list endpoint
Add `GET /api/trips/{trip_id}/shopping-list` that aggregates all ingredients across the trip.

Aggregation logic:
- For each trip_meal: look up recipe -> recipe_ingredients -> for each ingredient, accumulate `amount_oz * trip_meal.quantity`
- For each trip_snack: look up catalog_item -> ingredient, accumulate `servings * weight_per_serving`
- Group by ingredient, sum total oz needed
- Return list sorted by ingredient name: `[{ingredient_id, ingredient_name, total_oz}]`

**Files**: `backend/routers/trips.py`
**Verify**: With a trip that has overlapping ingredients across meals/snacks, confirm amounts aggregate correctly

### Step 4: Frontend — Add packing screen route
Add `/trips/:tripId/packing` route and a nav link/button from the trip planner page to reach it. Render a placeholder component.

**Files**: `frontend/src/App.jsx` (router), `frontend/src/pages/PackingScreen.jsx` (placeholder), trip planner page (add link)
**Verify**: Navigate to packing screen from trip planner, see placeholder, back navigation works

### Step 5: Frontend — Recipe assembly section
Build the recipe assembly section of the packing screen:
- Fetch trip meals with recipe details (name, ingredient list with amounts, at-home prep)
- For each meal: display recipe name, ingredient list with target amounts in oz, at-home prep text
- If quantity > 1, show quantity and multiply ingredient amounts in display
- Checkbox to mark as packed (calls PATCH endpoint)
- Numeric input for actual weight (calls PATCH endpoint on blur/change)

**Files**: `frontend/src/pages/PackingScreen.jsx` (or extract `RecipeAssembly` component)
**Verify**: Meals display with ingredient breakdowns, can check packed, can enter actual weight, values persist on reload

### Step 6: Frontend — Snack packing section
Build the snack packing section:
- Fetch trip snacks with catalog/ingredient details
- For each snack: show ingredient name, target weight (servings × weight_per_serving), target calories
- Checkbox to mark as packed (calls PATCH endpoint)
- Numeric input for actual weight (calls PATCH endpoint)

**Files**: `frontend/src/pages/PackingScreen.jsx` (or extract `SnackPacking` component)
**Verify**: Snacks display with target weights, can check packed, can enter actual weight, values persist on reload

### Step 7: Frontend — Combined shopping list section
Build the shopping list section:
- Fetch from `GET /api/trips/{trip_id}/shopping-list`
- Display table: ingredient name, total oz needed
- Sorted by ingredient name

**Files**: `frontend/src/pages/PackingScreen.jsx` (or extract `ShoppingList` component)
**Verify**: Shopping list shows aggregated ingredients, amounts are correct (e.g., 2 recipes each using 1oz oats = 2oz oats listed), snack items included

## Files Summary

**Create**:
- `frontend/src/pages/PackingScreen.jsx`

**Modify**:
- `backend/schemas/trip.py` — add packing-related schemas
- `backend/routers/trips.py` — add PATCH meal, PATCH snack, GET shopping-list endpoints
- `frontend/src/App.jsx` — add route for packing screen
- Trip planner page — add navigation link to packing screen

## Verification
1. PATCH trip meal: toggling packed and setting actual_weight_oz persists across requests
2. PATCH trip snack: same as above
3. Shopping list: ingredients that appear in multiple recipes aggregate correctly
4. Shopping list: snack items included with correct total (servings × weight_per_serving)
5. Packing screen: recipe assembly shows ingredient list and at-home prep for each meal
6. Packing screen: quantity > 1 meals show multiplied ingredient amounts
7. Packing screen: snack section shows target weights
8. Packing screen: all checkboxes and weight inputs persist on page reload
9. Packing screen: packed checkboxes do not affect trip summary totals (visual only)
10. Trip planner page still works normally
