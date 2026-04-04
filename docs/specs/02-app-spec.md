# Hiking Food Planner

## Purpose
A mobile-friendly web app for planning backpacking trip food. Replaces a Google Sheets workflow with better UX for browsing ingredients, building recipes, selecting snacks, and tracking packing progress.

## Tech Stack
- **Backend**: Python + FastAPI + SQLite
- **Frontend**: React + Vite
- **Hosting**: Self-hosted on Linux mini PC "beebaby", accessed via Tailscale
- **Auth**: None (Tailscale network handles access)
- Single-user app

## Core Concepts

### Ingredient Database (shared)
Master list of ingredients used by both recipes and snack items. Each ingredient has:
- Name
- Calories per oz
- Optional notes

This is the single source of truth. Recipes reference ingredients with specific amounts. Snack items on a trip are ingredients with a serving size and count.

### Snack Catalog
Wraps ingredients with serving-size info for trip planning:
- References an ingredient from the database
- Weight per serving (oz)
- Calories per serving (derived: weight x ingredient cal/oz, or overridden)
- Optional notes

### Recipe Library
Recipes for breakfasts and dinners. Each recipe has:
- Name
- Category (breakfast or dinner)
- Ingredients list (each: ingredient reference, amount in oz)
- At-home prep instructions (free text)
- Field prep instructions (free text)
- Computed: total weight, total calories, cal/oz

Recipes can be imported from Skurka's book as starters, then tweaked. They can also be created from scratch. Once imported, recipes are fully independent (no link to original).

### Trip Plan
For a specific trip, the user configures:

**Trip Calculator** (built-in, based on Skurka calculator):
- First day fraction, full days, last day fraction -> total days
- Computes recommended food weight/day (low: 19oz, high: 24oz)
- Computes recommended calories (assuming 125 cal/oz)
- Subtracts provided meals -> daytime food targets
- Shows low/high range for all recommendations

**Meal Selection**:
- Pick N breakfast recipes and N dinner recipes from the library
- Repeats allowed
- Counts and avg weights derived from selected recipes
- Per-category calorie targets (meals vs snacks) shown as ranges

**Snack Selection**:
- Pick items from the snack catalog, set serving counts (0.5 increments)
- Items with 0 servings are hidden from trip view (catalog only)
- Decrementing to 0 removes item from trip

**Lunches**: Not recipes. Assembled from snack catalog items. Budgeted as part of "daytime food" alongside snacks.

### Computed Fields (per snack item)
- Total weight = servings x weight per serving
- Total calories = servings x calories per serving
- Calories per oz = calories per serving / weight per serving

### Summary Dashboard
- Total snack weight (oz and lbs) -- actual vs target range
- Total snack calories -- actual vs target range
- Average cal/oz
- Meal weight/calories (from selected recipes)
- Combined totals (meals + snacks)
- Per-day breakdown (weight/day, calories/day)
- Per-category targets: snacks vs meals, each with low/high range

### Packing Screen
A dedicated view for packing day (at home with Chromebook + scale):

**Recipe Assembly**:
- For each selected recipe, show ingredient list with target amounts
- At-home prep instructions visible
- Check off each recipe as assembled
- Record actual measured weight per recipe

**Snack Packing**:
- List of snack items with target amounts
- Check off as packed
- Record actual measured weight per item

**Combined Shopping List**:
- All ingredients aggregated across all selected recipes + snacks
- Total amount needed for each ingredient across the whole trip
- Sorted: need-to-buy first, then on-hand; alphabetical within groups
- Essentials hidden by default (collapsed section at bottom for verification)
- On-hand toggle directly on the list for prep sessions
- Packing method shown per ingredient
- See `docs/specs/07-shopping-list-enhancements.md` for full spec

### Notes
- Ingredient-level notes (catalog default)
- Trip-level note overrides per item (same ingredient can have different notes on different trips)

### Multi-Trip Support
- Save/load multiple trip plans
- New trip: choose blank or clone existing
- Trip selector in header

### Packed Checkbox
- Visual checklist only, does not affect totals

### Packing Format
- Recipes are packed into individual ziplocks (one per meal)
- Packing screen workflow assumes ziplock-based assembly

## Data Model (SQLite)

### ingredients
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| name | TEXT NOT NULL |
| calories_per_oz | REAL |
| notes | TEXT |
| on_hand | BOOLEAN DEFAULT FALSE |
| essentials | BOOLEAN DEFAULT FALSE |
| packing_method | TEXT (by_weight\|by_count\|single_serving\|baggies\|full_item) |

### snack_catalog
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| ingredient_id | INTEGER FK |
| weight_per_serving | REAL |
| calories_per_serving | REAL |
| category | TEXT (drink_mix\|lunch\|salty\|sweet\|bars_energy) |
| drink_mix_type | TEXT (breakfast\|dinner\|all_day) |
| notes | TEXT |

### recipes
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| name | TEXT NOT NULL |
| category | TEXT (breakfast\|dinner) |
| at_home_prep | TEXT |
| field_prep | TEXT |
| notes | TEXT |

### recipe_ingredients
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| recipe_id | INTEGER FK |
| ingredient_id | INTEGER FK |
| amount_oz | REAL |

### trips
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| name | TEXT NOT NULL |
| first_day_fraction | REAL |
| full_days | INTEGER |
| last_day_fraction | REAL |

### trip_meals
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| trip_id | INTEGER FK |
| recipe_id | INTEGER FK |
| quantity | INTEGER DEFAULT 1 |
| packed | BOOLEAN DEFAULT FALSE |
| actual_weight_oz | REAL |

### trip_snacks
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| trip_id | INTEGER FK |
| catalog_item_id | INTEGER FK |
| servings | REAL |
| packed | BOOLEAN DEFAULT FALSE |
| actual_weight_oz | REAL |
| trip_notes | TEXT |

### trip_day_assignments
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| trip_id | INTEGER FK |
| day_number | INTEGER |
| slot | TEXT (breakfast\|breakfast_drinks\|morning_snacks\|lunch\|afternoon_snacks\|dinner\|evening_drinks\|all_day_drinks) |
| source_type | TEXT (meal\|snack) |
| source_id | INTEGER |
| servings | REAL |

## Screens / Views
1. **Trip Planner** (main): Trip calculator config, snack table with servings, meal recipe selection, summary dashboard
2. **Daily Meal Plan**: Day-by-day food distribution with stacked bar chart, per-day item lists, unallocated pool, auto-fill algorithm. See `docs/specs/09-daily-meal-plan.md`.
3. **Packing Screen**: Recipe assembly checklists, snack packing checklist, actual weights, combined shopping list
4. **Recipe Library**: Browse/create/edit recipes
5. **Ingredient Database**: Add/edit/remove ingredients (plus essentials flag, packing method)
6. **Trip Management**: Create/switch/delete/clone trips

## Pre-loaded Data
- All Skurka recipes (6 breakfasts, 6 dinners) with ingredients
- All ingredients from Utah 2026 sheet + Skurka recipes
- Utah 2026 trip with current snack selections and serving counts

## Snack Categories

Five categories for snack catalog items:
- **Drink mixes**: Electrolytes, greens, coffee/tea — daily quantity config (default 2/day)
- **Lunch**: Tortillas, PB, cheese, couscous, tuna/chicken packets, pita chips — assembled meals
- **Salty**: Goldfish, chips, pretzels, jerky, quest chips, babybel
- **Sweet**: Cookies, candy, chocolate, fruit snacks, donettes, Pop Tarts
- **Bars/Energy**: Kind bars, Clif bars, RX bars, Honey Stingers, Larabars

Categories are stored on the snack_catalog table. Used by the meal slot system and the planning agent.

## Meal Slots

Each hiking day has structured time slots for food:
- **Breakfast** — recipe from trip_meals
- **Lunch** (40% of remaining daily calories after meals)
- **Snacks** (60% of remaining daily calories after meals)
- **Dinner** — recipe from trip_meals
- **Drink mixes** — daily budget quantity, manually allocated

Snack items on a trip are assigned to a slot (`lunch` or `snacks`). The slot calorie split (40/60) is the default, configurable per trip in the future.

### Drink Mixes
- `drink_mixes_per_day` on the trip is a budget indicator, not an auto-fill control
- Servings are manually set per item, always whole numbers (packets)
- New drink mixes added to a trip start at 1 serving
- UI shows a budget meter: current total vs mixes_per_day * total_days
- Each drink mix has a `drink_mix_type`: `breakfast` (coffee, carnation, greens), `dinner` (tea), or `all_day` (electrolytes). Used by the daily meal plan for time-of-day distribution. See `docs/specs/08-drink-mix-subcategories.md`.

### Summary Meters
The UI shows per-category progress bars for calories and weight (snacks, breakfast, dinner). Each bar:
- Fills relative to target range midpoint, caps at 100%
- Color-coded by deviation: green (within 5%), yellow (10%), orange (20%), red (>20%)
- Shows delta text: "+10 oz", "-80 cal"
- Overall cal/oz number displayed across all categories

### Per-Section Meters & Summary Layout
Summary lives at the top of the trip planner as a full-width section (not sidebar), containing:
- Combined total meters (cal + weight) — always visible
- Compact category grid: 5 rows (breakfast, dinner, lunch, snacks, drink mixes) × 2 columns (cal bar, weight bar) — **collapsed by default**, expandable
- Text stats (cal/day, oz/day, total days)

Each food section also has inline meters in its header:
- Breakfast/dinner: cal + weight bars, targets from ±10% of per-recipe average × days
- Lunch/snacks: cal + weight bars, targets from backend slot_subtotals
- Drink mixes: cal + weight bars (dynamic targets from selected mixes' averages × budget) + servings bar

On mobile, meters stack vertically. See `docs/specs/05-per-section-meters.md` and `docs/specs/06-collapsible-category-grid.md` for full specs.

## Food Planning Agent

A Claude Code agent that builds complete trip food plans via the API.

### How it works
1. User invokes from Claude Code, specifies which trip
2. Agent reads trip config (days, targets), recipe library, snack catalog, and preferences
3. Agent starts from current trip state and refines the whole plan — adds, removes, adjusts servings
4. Agent flags anomalies it finds (e.g. "you have 22 snacks but no meals", "afternoon slot is 3x over target", mismatched serving counts)
5. Agent writes changes via API (trip_meals and trip_snacks endpoints)
6. User reviews in the app, gives feedback
7. Agent adjusts, loop until satisfied
8. Agent saves new preference learnings to memory

### Meal selection logic
- Breakfast: minimal variety (1-2 recipes repeated across the trip)
- Dinner: 2-3 unique recipes, no single recipe more than half the trip days
- Dinner variety by type: balance across noodle-based, rice/bean, rice/dehydrated meat (or whatever types exist in the library)
- Prefer recipes that share ingredients (tiebreaker, not primary driver)

### Snack selection logic
- Fills two slot buckets (lunch, snacks) plus drink mixes
- Slot calorie targets derived from: (total daily target - breakfast cal - dinner cal) x slot percentage
- Fewer unique items, more servings of each — enough of each item that you don't feel the need to hoard them (scarcity of an item causes hoarding; multiples remove that instinct)
- Front-load the good food — don't save treats for later days, eat well from day one
- Drink mixes: configured as X per day (default 2), filled separately

### Preference system (3-tier, highest weight first)
1. App ratings (future feature)
2. Catalog notes (e.g. "Range bars aren't pleasant to eat")
3. Conversation memory (accumulated across sessions)

### V1 constraints
- Works with existing API — no app changes required
- Agent carries snack category and slot knowledge in its prompt/memory
- When app features (categories, slots, meters) are built, agent adopts the API

## Macronutrient Tracking

Protein, fat, and carb tracking at the ingredient level, rolling up through recipes, snacks, trips, and daily plans. See `docs/specs/10-macronutrient-tracking.md` for full spec.

- Ingredients have optional `protein_per_oz`, `fat_per_oz`, `carb_per_oz` (grams)
- When all three macros are set, `calories_per_oz` is derived (p*4 + f*9 + c*4). When macros are null, direct `calories_per_oz` is used.
- Macros roll up everywhere calories do: recipes, snack servings, trip summary, daily plan
- At item level: show grams. At aggregate level: show percentage breakdown vs. global target
- Global macro target (e.g., 20% protein / 30% fat / 50% carb) stored in app settings, not per-trip
- Partial data handled gracefully: macro percentages computed from the subset of calories with macro data, with coverage indicator
- Data populated via manual UI entry or external agent using USDA FoodData Central API

## Future Feature Requests

- ~~Snack categories in data model (category column on snack_catalog)~~ (done)
- ~~Meal slot assignment on trip_snacks (slot column)~~ (done, simplified to lunch/snacks)
- ~~Per-slot calorie meters with heatmap showing days covered~~ (done, replaced with progress bars)
- ~~Drink mixes as daily quantity config on trips table~~ (done, budget indicator with manual servings)
- Configurable slot calorie split per trip (default 40/60)
- ~~Snack and meal ratings (1-5 or thumbs up/down)~~ (done)
- Plan alternates — swap options within a proposed plan

## Deployment

### Target
Self-hosted on "beebaby" (Linux mini PC), accessible via Tailscale. Develop on ARVELLAT, deploy via rsync + SSH.

### How it runs
- Single process: uvicorn serves FastAPI (API + built React static files) on port 8000
- systemd service `hiking-food` auto-starts on boot, restarts on crash
- SQLite database at `backend/hiking_food.db`

### First-time setup on beebaby
```
ssh beebaby 'bash -s' < deploy/setup.sh
./deploy/deploy.sh
```

### Deploy updates
```
./deploy/deploy.sh
```
This rsyncs code to beebaby, installs deps, builds frontend, restarts the service.

### Access
`http://beebaby:8000` from any Tailscale-connected device.
