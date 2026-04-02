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

### Notes
- Ingredient-level notes (catalog default)
- Trip-level note overrides per item (same ingredient can have different notes on different trips)

### Multi-Trip Support
- Save/load multiple trip plans
- New trip: choose blank or clone existing
- Trip selector in header

### Packed Checkbox
- Visual checklist only, does not affect totals

## Data Model (SQLite)

### ingredients
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| name | TEXT NOT NULL |
| calories_per_oz | REAL |
| notes | TEXT |

### snack_catalog
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| ingredient_id | INTEGER FK |
| weight_per_serving | REAL |
| calories_per_serving | REAL |
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

## Screens / Views
1. **Trip Planner** (main): Trip calculator config, snack table with servings, meal recipe selection, summary dashboard
2. **Packing Screen**: Recipe assembly checklists, snack packing checklist, actual weights, combined shopping list
3. **Recipe Library**: Browse/create/edit recipes
4. **Ingredient Database**: Add/edit/remove ingredients
5. **Trip Management**: Create/switch/delete/clone trips

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
- **Morning snack** (25% of remaining daily calories after meals)
- **Lunch** (40% of remaining daily calories)
- **Afternoon snack** (35% of remaining daily calories)
- **Dinner** — recipe from trip_meals
- **Drink mixes** — separate daily quantity, not tied to a slot

Snack items on a trip are assigned to a slot (morning_snack, lunch, afternoon_snack). The slot calorie split (25/40/35) is the default, configurable per trip in the future.

The UI shows per-slot calorie meters and a heatmap of which days have food allocated for each slot. As items are added/removed, meters update in real time.

## Food Planning Agent

A Claude Code agent that builds complete trip food plans via the API.

### How it works
1. User invokes from Claude Code, specifies which trip
2. Agent reads trip config (days, targets), recipe library, snack catalog, and preferences
3. Agent starts from current trip state and refines the whole plan — adds, removes, adjusts servings
4. Agent writes changes via API (trip_meals and trip_snacks endpoints)
5. User reviews in the app, gives feedback
6. Agent adjusts, loop until satisfied
7. Agent saves new preference learnings to memory

### Meal selection logic
- Breakfast: minimal variety (1-2 recipes repeated across the trip)
- Dinner: 2-3 unique recipes, no single recipe more than half the trip days
- Prefer recipes that share ingredients (tiebreaker, not primary driver)

### Snack selection logic
- Fills three slot buckets (morning snack, lunch, afternoon snack) plus drink mixes
- Slot calorie targets derived from: (total daily target - breakfast cal - dinner cal) x slot percentage
- Fewer unique items, more servings of each — avoids the variety/hoarding trap
- Drink mixes: configured as X per day (default 2), filled separately

### Preference system (3-tier, highest weight first)
1. App ratings (future feature)
2. Catalog notes (e.g. "Range bars aren't pleasant to eat")
3. Conversation memory (accumulated across sessions)

### V1 constraints
- Works with existing API — no app changes required
- Agent carries snack category and slot knowledge in its prompt/memory
- When app features (categories, slots, meters) are built, agent adopts the API

## Future Feature Requests

- Snack categories in data model (category column on snack_catalog)
- Meal slot assignment on trip_snacks (slot column)
- Per-slot calorie meters with heatmap showing days covered
- Drink mixes as daily quantity config on trips table
- Configurable slot calorie split per trip (default 25/40/35)
- Snack and meal ratings (1-5 or thumbs up/down)
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
