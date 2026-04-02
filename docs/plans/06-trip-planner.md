# Issue #7: Trip Planner — CRUD, Calculator, Snack/Meal Selection, Summary

## Context
The trip planner is the core screen of the app. Users create trips, configure how many days they'll be out, select snacks and meals, and see a live summary comparing actual food weight/calories against targets. This issue brings together the ingredient, snack catalog, and recipe library built in issues #3-6.

The trip calculator uses the Skurka method: first day fraction + full days + last day fraction = total days, then 19-24 oz/day at 125 cal/oz to derive weight and calorie ranges. Meal weights are subtracted from the total to get daytime (snack) food targets.

## Assumptions
- Issues #2-6 are complete: scaffolding, ingredients CRUD, snack catalog CRUD, recipe library CRUD, seed data all exist
- All DB models already defined in `backend/models.py` (Trip, TripMeal, TripSnack)
- Backend router pattern established (routers/ directory, Pydantic schemas, registration in main.py)
- Frontend pattern established (pages/ directory, nav component, API calls to /api/*)

## Plan

### ✅ Step 1: Backend — Trip calculator as pure function with tests
Create `backend/calculator.py` with a pure function that takes first_day_fraction, full_days, last_day_fraction, and a list of meal weights, and returns a result dict with all computed ranges.

Algorithm:
- total_days = first_day_fraction + full_days + last_day_fraction
- total_weight_low = total_days * 19, total_weight_high = total_days * 24
- total_cal_low = total_weight_low * 125, total_cal_high = total_weight_high * 125
- meal_weight = sum of all meal weights
- meal_cal = meal_weight * 125
- daytime_weight_low = total_weight_low - meal_weight, daytime_weight_high = total_weight_high - meal_weight
- daytime_cal_low = daytime_weight_low * 125, daytime_cal_high = daytime_weight_high * 125

Write pytest tests in `backend/tests/test_calculator.py`:
- 7-day trip: 0.75 + 5 + 0.75 = 6.5 days -> 123.5-156 oz, 15437.5-19500 cal
- Same trip with meals: 6 breakfasts * 4.5oz + 6 dinners * 5.5oz = 60oz -> daytime 63.5-96 oz
- 1-day trip: 1 + 0 + 0 = 1 day -> 19-24 oz
- Zero first/last fractions: 0 + 3 + 0 = 3 days -> 57-72 oz

**Files**: `backend/calculator.py`, `backend/tests/test_calculator.py`
**Verify**: `pytest backend/tests/test_calculator.py` — all tests pass

### ✅ Step 2: Backend — Trip CRUD endpoints
Create `backend/schemas/trip.py` with:
- TripBase: name, first_day_fraction, full_days, last_day_fraction
- TripCreate(TripBase)
- TripUpdate: all fields optional
- TripResponse(TripBase): adds id

Create `backend/routers/trips.py` with:
- GET /api/trips — list all trips (id and name only, lightweight)
- GET /api/trips/{id} — full trip detail including calculator params
- POST /api/trips — create trip
- PUT /api/trips/{id} — update trip (name and/or calculator params)
- DELETE /api/trips/{id} — delete trip and cascade to trip_snacks/trip_meals

Register router in main.py.

**Files**: `backend/schemas/trip.py`, `backend/routers/trips.py`, `backend/main.py`
**Verify**: curl all CRUD endpoints, create/update/delete a trip

### ✅ Step 3: Backend — Trip snack management endpoints
Add to `backend/routers/trips.py` (or a sub-router):
- POST /api/trips/{id}/snacks — add snack to trip (catalog_item_id, servings)
- PUT /api/trips/{id}/snacks/{snack_id} — update servings, packed, trip_notes
- DELETE /api/trips/{id}/snacks/{snack_id} — remove snack from trip

GET /api/trips/{id} should include trip_snacks with joined snack catalog + ingredient data (name, weight_per_serving, calories_per_serving, computed totals).

**Files**: `backend/schemas/trip.py` (add TripSnack schemas), `backend/routers/trips.py`
**Verify**: curl to add a snack to a trip, update servings, verify GET includes snack details with computed columns

### ✅ Step 4: Backend — Trip meal management endpoints
Add to `backend/routers/trips.py`:
- POST /api/trips/{id}/meals — add meal to trip (recipe_id, quantity)
- PUT /api/trips/{id}/meals/{meal_id} — update quantity, packed
- DELETE /api/trips/{id}/meals/{meal_id} — remove meal from trip

GET /api/trips/{id} should include trip_meals with joined recipe data (name, category, total weight, total calories).

**Files**: `backend/schemas/trip.py` (add TripMeal schemas), `backend/routers/trips.py`
**Verify**: curl to add a meal, verify GET includes meal details with recipe weight/calories

### ✅ Step 5: Backend — Trip summary endpoint
Add GET /api/trips/{id}/summary that computes:
- Calculator targets (using calculator.py with trip params and meal weights)
- Snack totals: total weight, total calories, avg cal/oz
- Meal totals: total weight, total calories (from recipe ingredient sums * quantity)
- Combined totals: snacks + meals
- Per-day breakdown: combined totals / total_days
- Actual vs target comparison for snacks (daytime targets) and combined (total targets)

**Files**: `backend/routers/trips.py`, `backend/schemas/trip.py` (add TripSummary schema)
**Verify**: curl summary endpoint for a trip with snacks and meals, verify math matches calculator tests

### ✅ Step 6: Backend — Clone trip endpoint
Add POST /api/trips/{id}/clone:
- Creates a new trip with same calculator params, name suffixed with "(copy)"
- Copies all trip_snacks and trip_meals to the new trip
- Returns the new trip

**Files**: `backend/routers/trips.py`
**Verify**: Clone a trip, verify new trip has same snacks/meals/params, different id

### ✅ Step 7: Frontend — Trip selector and CRUD in header
Add trip management to the header/nav area:
- Dropdown listing all trips (GET /api/trips)
- Selecting a trip sets it as the active trip (React state/context)
- "New Trip" button -> creates trip via POST, selects it
- "Clone Trip" button -> POST /api/trips/{id}/clone, selects the clone
- "Delete Trip" button -> confirm dialog, DELETE, select another trip or show empty state

Store active trip id in React context or top-level state so child components can access it.

**Files**: `frontend/src/components/TripSelector.jsx` (new), `frontend/src/App.jsx` (integrate), `frontend/src/context/TripContext.jsx` (new, or equivalent state management)
**Verify**: Can create, select, clone, and delete trips via the UI. Active trip persists across nav.

### ✅ Step 8: Frontend — Trip calculator config panel
On the trip planner page, show editable inputs for the active trip's calculator params:
- First day fraction (number input, 0-1 range, 0.25 steps)
- Full days (integer input)
- Last day fraction (number input, 0-1 range, 0.25 steps)
- Display computed total_days
- Display recommended ranges (weight, calories) live as user edits
- Save changes via PUT /api/trips/{id} on change (debounced)

**Files**: `frontend/src/pages/TripPlanner.jsx` (new), `frontend/src/components/TripCalculator.jsx` (new), `frontend/src/App.jsx` (add route)
**Verify**: Edit calculator params, see computed ranges update live. Values persist after page reload.

### ✅ Step 9: Frontend — Snack selection table
Add snack selection to the trip planner page:
- "Add Snack" button/dropdown to pick from snack catalog (GET /api/snacks)
- Table showing trip snacks with columns: Name, Servings (stepper with 0.5 step, also typeable), Weight/Serving, Total Weight, Cal/Serving, Total Cal, Cal/Oz, Packed checkbox, Notes
- Changing servings calls PUT /api/trips/{id}/snacks/{snack_id}
- Decrementing to 0 removes the item (DELETE call, row disappears)
- Packed checkbox updates via PUT

**Files**: `frontend/src/components/SnackSelection.jsx` (new), `frontend/src/pages/TripPlanner.jsx` (integrate)
**Verify**: Add snacks, adjust servings, verify computed columns. Decrement to 0 removes row. Packed checkbox persists.

### ✅ Step 10: Frontend — Meal selection panel
Add meal selection to the trip planner page:
- "Add Meal" dropdown showing recipes grouped by category (breakfast/dinner)
- Table showing trip meals: Recipe Name, Category, Quantity (editable), Weight (per unit), Total Weight, Total Cal
- Repeats allowed (same recipe can be added multiple times or quantity incremented)
- Quantity change calls PUT, decrement to 0 removes

**Files**: `frontend/src/components/MealSelection.jsx` (new), `frontend/src/pages/TripPlanner.jsx` (integrate)
**Verify**: Add breakfast and dinner recipes, adjust quantities, see totals. Repeats work.

### ✅ Step 11: Frontend — Summary dashboard
Add summary dashboard to the trip planner page (sidebar or bottom panel):
- Fetch GET /api/trips/{id}/summary and display:
  - Snack totals (weight oz/lbs, calories) with actual vs target range
  - Meal totals (weight, calories)
  - Combined totals with actual vs target range
  - Per-day breakdown (weight/day, cal/day)
- Color coding: green when actual is within target range, yellow when outside
- Updates live when snacks/meals/calculator params change

**Files**: `frontend/src/components/TripSummary.jsx` (new), `frontend/src/pages/TripPlanner.jsx` (integrate)
**Verify**: Summary numbers match manual calculation. Color coding works. Changes to snacks/meals/calculator update summary immediately.

## Verification
1. Calculator tests pass: standard 7-day trip, meal subtraction, edge cases
2. Trip CRUD: create, read, update, delete all work
3. Trip clone: new trip has all snacks/meals copied
4. Snack selection: add from catalog, adjust servings with 0.5 steps, 0 removes, packed checkbox works
5. Meal selection: add recipes, adjust quantities, repeats work
6. Summary: snack totals + meal totals + combined match calculator targets
7. 7-day trip acceptance test: 0.75 + 5 + 0.75 = 6.5 days shows 123.5-156 oz recommended total
8. Color coding: green when in range, yellow when out
9. All existing pages (ingredients, snack catalog, recipe library) still work
10. Data persists across page reloads
