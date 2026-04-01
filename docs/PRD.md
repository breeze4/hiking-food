## Problem Statement

Planning food for multi-day backpacking trips currently lives in a Google Sheet. The sheet tracks a catalog of snack foods with per-serving weight and calorie data, lets you select items and set serving counts for a specific trip, and computes totals (weight, calories, cal/oz, per-day stats). A separate section estimates meal weights. A calculator sheet recommends how much food to bring based on trip length.

This workflow has several problems:
- The sheet is clunky on mobile, which is where you'd use it while packing or shopping.
- Recipes (from Skurka's Backpacking Recipes book and custom creations) aren't tracked in the sheet at all — meal weights are just lump estimates.
- There's no connection between recipe ingredients and the snack catalog, so you can't generate a combined shopping list or see true total weight across everything.
- The "packed" checklist and actual-weight tracking are afterthoughts in the sheet layout.
- Multi-trip support means duplicating tabs and manually maintaining them.

## Solution

A self-hosted web app (Python/FastAPI backend, React frontend, SQLite database) running on a home Linux mini PC ("beebaby") accessible via Tailscale. Single-user, no auth needed.

The app replaces the sheet with five connected screens:

1. **Trip Planner** — The main screen. Configure trip length, select snack items with serving counts, pick breakfast/dinner recipes, and see a live summary dashboard comparing your actual food weight/calories against recommended ranges.

2. **Packing Screen** — A packing-day workflow. Shows recipe assembly checklists (ingredient lists with target amounts and at-home prep instructions), snack packing checklists, actual weight recording, and a combined shopping list aggregated across all recipes and snacks.

3. **Recipe Library** — Browse, create, and edit breakfast/dinner recipes. Pre-seeded with 12 Skurka recipes extracted from the PDF. Each recipe has an ingredient list with amounts in oz, at-home prep instructions, and computed totals.

4. **Ingredient Database** — Master list of ingredients shared between recipes and the snack catalog. Each ingredient has a name, calories per oz, and optional notes.

5. **Trip Management** — Create new trips (blank or cloned from existing), switch between trips, delete old ones.

Key design principle: ingredients are the shared foundation. Recipes reference ingredients with specific amounts. Snack catalog items reference ingredients with serving sizes. This shared pool enables the combined shopping list and accurate total-weight computation.

## User Stories

1. As a backpacker, I want to see a list of all my snack food options with per-serving weight, calories, and cal/oz, so that I can make informed choices about what to bring.
2. As a backpacker, I want to add snack items to a trip and set serving counts in 0.5 increments, so that I can plan exactly how much of each item to bring.
3. As a backpacker, I want items to disappear from the trip view when I set servings to 0, so that the trip list only shows what I'm actually bringing.
4. As a backpacker, I want to see running totals of total weight (oz and lbs), total calories, and average cal/oz for my selected snacks, so that I know if I'm in the right range.
5. As a backpacker, I want a trip calculator that takes my trip length (first day fraction, full days, last day fraction) and shows recommended food weight and calorie ranges, so that I know how much food to target.
6. As a backpacker, I want the calculator to subtract my selected meal weights from the total recommendation and show the remaining "daytime food" target, so that I know how many snacks to bring.
7. As a backpacker, I want per-category calorie targets (snacks vs meals) displayed as low/high ranges, so that I can see if each category is on track independently.
8. As a backpacker, I want a summary dashboard showing actual vs target for weight and calories, broken down per-day, so that I have a complete picture at a glance.
9. As a backpacker, I want to browse a recipe library organized by category (breakfast/dinner), so that I can pick meals for my trip.
10. As a backpacker, I want to select N breakfast recipes and N dinner recipes for a trip with quantities (repeats allowed), so that I can plan my meal lineup.
11. As a backpacker, I want recipe totals (weight, calories, cal/oz) computed automatically from ingredient amounts, so that I don't have to calculate them manually.
12. As a backpacker, I want to create new recipes from scratch with a name, category, ingredient list with amounts in oz, and at-home prep instructions, so that I can add my own meals.
13. As a backpacker, I want to edit existing recipes (change ingredients, amounts, instructions), so that I can tweak recipes to my preferences.
14. As a backpacker, I want the 12 Skurka recipes pre-loaded with all their ingredients and amounts, so that I have a solid starting point.
15. As a backpacker, I want recipes to be fully independent once imported (no link back to the original), so that my edits don't conflict with anything.
16. As a backpacker, I want a shared ingredient database used by both recipes and snack catalog items, so that the same ingredient (e.g., honey) is defined once.
17. As a backpacker, I want to add, edit, and remove ingredients from the master database, so that I can maintain accurate nutritional data.
18. As a backpacker, I want a packing screen that shows each selected recipe's ingredient list with target amounts and at-home prep instructions, so that I can assemble meals at home.
19. As a backpacker, I want to check off each recipe as assembled and record its actual measured weight, so that I can track packing progress.
20. As a backpacker, I want a snack packing checklist with target amounts and checkboxes, so that I can check off items as they go in the bag.
21. As a backpacker, I want to record actual measured weights for snack items, so that the summary can reflect reality vs plan.
22. As a backpacker, I want packed checkboxes to be visual only (not affecting totals), so that my weight/calorie numbers always reflect the full plan.
23. As a backpacker, I want a combined shopping list that aggregates all ingredients across all selected recipes and snacks for the trip, so that I can shop in one pass.
24. As a backpacker, I want to save multiple trip plans, so that I can plan different trips without losing previous ones.
25. As a backpacker, I want to create a new trip by cloning an existing one, so that I can start from a proven food list and adjust.
26. As a backpacker, I want to switch between trips via a selector in the header, so that navigation is quick.
27. As a backpacker, I want notes on ingredients (catalog-level defaults) and trip-level note overrides, so that I can annotate items differently per trip.
28. As a backpacker, I want sortable columns in the snack table and ingredient table, so that I can organize by weight, calories, or name.
29. As a backpacker, I want the app to work well on mobile (phone/tablet), so that I can use it while shopping or packing.
30. As a backpacker, I want the app accessible from any of my devices via Tailscale, so that I can plan from my laptop and pack with my Chromebook.
31. As a backpacker, I want lunches treated as snack catalog items (not recipes), so that I can assemble them flexibly from my snack list.
32. As a backpacker, I want the Utah 2026 trip pre-loaded with my current snack selections and serving counts, so that I can pick up where the Google Sheet left off.

## Implementation Decisions

### Architecture
- **Backend**: Python + FastAPI serving a REST API, with SQLAlchemy ORM and SQLite database. Single file database, zero-config.
- **Frontend**: React + Vite SPA. Communicates with backend via fetch API.
- **Hosting**: Self-hosted on "beebaby" Linux mini PC, accessed via Tailscale. No authentication layer — Tailscale network provides access control.
- **Single-user**: No user model, no sessions, no auth. One database serves one person.

### Data Model
- **Shared ingredient database**: The foundation. Every ingredient has a name, calories_per_oz, and optional notes. Both recipes and snack catalog items reference ingredients by FK.
- **Snack catalog**: Wraps an ingredient with a serving size (weight_per_serving, calories_per_serving). The calories_per_serving can be derived from ingredient cal/oz × weight, or overridden.
- **Recipes**: Name, category (breakfast|dinner), prep_instructions, notes. Related recipe_ingredients table holds ingredient_id + amount_oz per recipe.
- **Trips**: Name + calculator inputs (first_day_fraction, full_days, last_day_fraction). Related trip_meals (recipe_id, quantity, packed, actual_weight_oz) and trip_snacks (catalog_item_id, servings, packed, actual_weight_oz, trip_notes).

### Key Modules
1. **Ingredient Store** — CRUD for ingredients. Foundation layer.
2. **Snack Catalog** — CRUD for snack items referencing ingredients.
3. **Recipe Engine** — CRUD for recipes with nested ingredient lists. Computes weight/calorie/cal-per-oz totals from ingredient data.
4. **Trip Planner** — Trip CRUD, calculator computations, snack/meal selection, summary aggregation.
5. **Packing Manager** — Packed status, actual weights, recipe assembly checklists, shopping list aggregation.
6. **Trip Calculator** — Pure computation module. Takes trip length inputs + meal weights, produces recommended ranges (19-24 oz/day, 125 cal/oz assumption).

### Interaction Details
- Servings use 0.5 increments with stepper buttons (also typeable).
- Setting servings to 0 removes the item from the trip view.
- New trips can be blank or cloned from an existing trip.
- Meal selection is "pick N recipes with quantities" (not per-day assignment). Repeats allowed.
- Packed checkbox is visual only — totals always reflect all selected items.
- Summary shows actual vs target as ranges (low/high), color-coded (green if in range).
- Combined shopping list sums ingredient amounts across all recipes + all snacks for the trip.

### Seed Data
- 12 Skurka recipes (6 breakfasts, 6 dinners) extracted from PDF with full ingredient lists and amounts.
- All ingredients from both the Skurka recipes and the Utah 2026 Google Sheet.
- Utah 2026 trip with current snack selections and serving counts (matching the spreadsheet: ~103 oz snacks, ~11,745 cal).

## Testing Decisions

### What Makes a Good Test
Tests should verify external behavior through public interfaces, not implementation details. A test should answer: "does this module produce the correct output given this input?" Tests should not depend on database internals, specific SQL queries, or React component structure.

### Modules to Test

**Trip Calculator** (pure computation):
- Input: trip length params (first_day_fraction, full_days, last_day_fraction) + meal weights
- Output: total days, recommended weight range, recommended calorie range, daytime food targets
- Test cases: standard 7-day trip matching the spreadsheet (123.5-156 oz), edge cases (1-day trip, 0 first/last day fractions), verify subtraction of meal weights

**Recipe Engine** (computation + data):
- Verify total weight = sum of ingredient amounts
- Verify total calories = sum of (ingredient amount_oz × ingredient calories_per_oz)
- Verify cal/oz = total calories / total weight
- Test with known Skurka recipe data (e.g., Quickstart Cereal: 4.5 oz, 617 cal, 137 cal/oz)
- Test adding/removing ingredients updates totals correctly

### Prior Art
No existing tests in the codebase (greenfield project). Tests will use pytest for the backend.

## Out of Scope

- **User authentication / multi-user**: Tailscale handles access. No user model.
- **Recipe build/meal-prep system**: The spec mentions a future "build section with recipes and stuff" for meals. For now, meals are recipes with ingredient lists and at-home prep text — not a full meal-prep workflow with step-by-step instructions.
- **Per-day meal assignment**: Meals are selected as "N of recipe X" for the trip, not assigned to specific days.
- **Allergy/dietary tracking**: Skurka recipes include allergy info, but the app will not track or filter by allergens.
- **Data export/import**: With a real database on a persistent server, JSON export/import is unnecessary.
- **Offline/PWA support**: The app requires network access to beebaby via Tailscale.
- **Field prep instructions**: Only at-home prep instructions are stored. Field cooking instructions stay in the original Skurka PDF.

## Further Notes

- The Skurka recipe PDF (skurka-recipe-book.pdf, 52 pages) is in the project root. It contains 12 recipes with structured ingredient tables that can be extracted programmatically for seed data.
- The Utah 2026 Google Sheet data has been captured as CSV and analyzed. The spreadsheet totals (~103 oz, ~11,745 cal, ~114 cal/oz for snacks) serve as verification targets for the seed data.
- The Skurka calculator spreadsheet has also been captured. Its formula (trip days × oz/day range, minus provided meal weights = daytime food target) is the basis for the Trip Calculator module.
- Lunches are explicitly not recipes. They're assembled from snack catalog items (tortillas, PB, jerky, etc.) and budgeted as part of "daytime food" in the calculator.
- The meal recipe system is designed with a clean seam for a future "recipe build" feature that could add step-by-step assembly instructions, ingredient substitution tracking, and batch prep workflows.
