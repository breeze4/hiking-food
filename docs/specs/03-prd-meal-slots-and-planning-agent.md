# PRD: Meal Slots, Snack Categories, and Food Planning Agent

## Problem Statement

Planning food for a multi-day backpacking trip is a manual, error-prone process. The current app lets you pick meals and snacks, but treats all snacks as a flat list with no structure. This leads to:

- **No concept of when food gets eaten** — snacks aren't organized by time of day, so there's no way to see if lunch is covered but morning snacks aren't
- **Too much snack variety** — the natural tendency is to add many different items, which makes prep harder, leads to hoarding scarce items on trail, and means you run out of things you like while having leftovers of things you don't
- **No automated planning** — every trip is built from scratch by manually adding items and tweaking servings until the calorie targets look right, with no way to leverage preferences from past trips
- **No preference tracking** — there's no way to record which foods you like or dislike, so you repeat the same discovery process each trip
- **Drink mixes are treated as snacks** — they're daily essentials with a fixed quantity, not discretionary snacks, but they're managed the same way

## Solution

Three interconnected features that structure the food planning workflow:

1. **Snack categories** — classify every snack catalog item into one of five categories (drink_mix, lunch, salty, sweet, bars_energy) so the app and agent understand what role each item plays
2. **Meal slots** — organize a hiking day into structured time slots (breakfast, morning snack, lunch, afternoon snack, dinner, drink mixes) with calorie targets per slot derived from the trip calculator, and per-slot meters showing coverage
3. **Food planning agent** — a CLI agent that reads the trip config and snack/recipe catalog, builds a complete food plan via the API, and iterates based on user feedback, learning preferences over time

## User Stories

1. As a hiker, I want each snack in my catalog to have a category (drink mix, lunch, salty, sweet, bars/energy) so I can see what role it plays in my day
2. As a hiker, I want to filter snacks by category when browsing the catalog or adding snacks to a trip
3. As a hiker, I want snacks on my trip assigned to time-of-day slots (morning snack, lunch, afternoon snack) so I can see what I'm eating when
4. As a hiker, I want new snacks to auto-assign to a default slot based on their category (e.g. bars → morning, sweet → afternoon)
5. As a hiker, I want to reassign a snack to a different slot if I want to eat it at a different time
6. As a hiker, I want each slot to show a calorie meter (target vs actual) so I can see at a glance which slots are under or over
7. As a hiker, I want the slot calorie targets to automatically adjust based on my breakfast and dinner selections — snack slots split whatever calories remain
8. As a hiker, I want to see a heatmap showing how many days each slot covers, so I can spot gaps (e.g. "morning snack covers 5/7 days")
9. As a hiker, I want the meters to update in real time as I add/remove snacks or change servings
10. As a hiker, I want drink mixes handled separately with a "per day" config (default 2/day) rather than manual serving math
11. As a hiker, I want changing the drink mixes/day number to auto-recalculate servings for all drink mix items on the trip
12. As a hiker, I want drink mixes shown in their own section, not mixed in with snack slots
13. As a hiker, I want to rate snacks and recipes (1-5) so my preferences are recorded for future planning
14. As a hiker, I want to see ratings when browsing the catalog, recipe list, and add-snack search panel
15. As a hiker, I want to invoke a planning agent from the CLI that reads my trip and builds a complete food plan
16. As a hiker, I want the agent to start from my current trip state and refine it (not wipe it clean) so existing good choices are preserved
17. As a hiker, I want the agent to flag anomalies it finds (e.g. "22 snacks but no meals", "afternoon slot 3x over target") before making changes
18. As a hiker, I want the agent to select breakfasts (1-2 recipes, repeated) and dinners (2-3 unique, no one recipe > half the trip)
19. As a hiker, I want the agent to balance dinner variety by type (noodle-based, rice/bean, rice/dehydrated meat)
20. As a hiker, I want the agent to prefer fewer unique snack items with more servings each, so I don't hoard scarce items on trail
21. As a hiker, I want the agent to front-load good food — not save treats for later days
22. As a hiker, I want the agent to prefer recipes that share ingredients to minimize my shopping list (as a tiebreaker, not primary driver)
23. As a hiker, I want the agent to read my catalog notes and conversation memory as preference signals
24. As a hiker, I want to review the agent's plan in the app, give feedback, and have the agent adjust
25. As a hiker, I want the agent to remember my preferences across sessions so it gets better over time
26. As a hiker, I want the agent to work today with the existing API, before snack categories or meal slots are built into the app

## Implementation Decisions

### Snack categories
- Add `category` TEXT column to `snack_catalog` table with values: `drink_mix`, `lunch`, `salty`, `sweet`, `bars_energy`
- Expose in all snack API responses, accept on create/update
- Add optional `?category=` query filter to `GET /api/snacks`
- Show in snack catalog page and add-snack search panel
- Seed script assigns categories to all existing items

### Meal slots
- Add `slot` TEXT column to `trip_snacks` table with values: `morning_snack`, `lunch`, `afternoon_snack`
- Auto-assign default slot based on category when adding a snack to a trip:
  - drink_mix → handled separately (not a slot)
  - lunch → lunch
  - salty → afternoon_snack
  - sweet → afternoon_snack
  - bars_energy → morning_snack
- Summary endpoint returns per-slot subtotals (weight, calories, days covered)
- Slot calorie targets: (total daily target - breakfast cal - dinner cal) * slot percentage
- Default split: morning 25%, lunch 40%, afternoon 35% (configurable per trip in the future)
- Trip planner renders three slot sections instead of one flat snack table

### Drink mix config
- Add `drink_mixes_per_day` INTEGER column to `trips` table (default 2)
- Changing the value auto-recalculates servings for all drink_mix category snacks on the trip
- Drink mixes rendered in their own section, separate from slot sections
- Summary endpoint breaks out drink mix totals separately

### Per-slot calorie meters
- Per-slot meters in the summary panel showing target vs actual with green/amber status
- Days covered = slot actual calories / (daily remaining calories * slot percentage)
- Heatmap visualization showing coverage per slot
- Mobile: simplify heatmap to text ("5/7 days")

### Ratings
- Add `rating` INTEGER column (nullable, 1-5) to both `snack_catalog` and `recipes` tables
- Show in catalog, recipe list, add-snack panel, recipe edit page
- Reusable star rating component

### Food planning agent
- Custom agent definition file for the hiking-food project
- Talks to beebaby:8000 API directly
- V1 carries snack category and slot knowledge in its system prompt (no app dependency)
- Workflow: read current state → flag anomalies → propose changes → write via API → summarize → iterate on feedback → save preference learnings to memory
- Meal logic: 1-2 breakfasts repeated, 2-3 dinners balanced by type, no single recipe > half the trip, ingredient overlap as tiebreaker
- Snack logic: fill slot buckets to calorie targets, fewer items with more servings, enough multiples to eliminate hoarding instinct, front-load good food
- Preference reading: ratings (highest, future) > catalog notes > conversation memory

### Schema changes summary
- `snack_catalog`: add `category` TEXT, add `rating` INTEGER
- `trip_snacks`: add `slot` TEXT
- `trips`: add `drink_mixes_per_day` INTEGER
- `recipes`: add `rating` INTEGER

## Testing Decisions

### What makes a good test
- Test external behavior through the API, not implementation details
- Verify computed values (slot targets, days covered) against known inputs
- Test the category-to-slot default mapping
- Test drink mix auto-recalculation

### Modules to test
- **Summary endpoint** — per-slot calorie targets, per-slot actuals, days covered computation. This is the most logic-heavy area and the core feedback loop. Test with known trip configs and snack selections, verify the math.
- **Drink mix auto-calculation** — changing drink_mixes_per_day correctly updates servings for all drink_mix snacks. Test edge cases: 0/day, changing when no drink mixes exist, changing when some exist.
- **Category-to-slot default mapping** — adding a snack to a trip assigns the correct default slot based on its category.
- **Snack/recipe CRUD with new fields** — category, slot, rating fields are accepted, persisted, and returned correctly.

### Prior art
- Existing backend tests in `backend/tests/` using pytest
- Existing patterns: test via API calls against a test database

## Out of Scope

- Web-based chat UI for the planning agent (CLI only for now)
- Template/component-based recipe system (fixed recipes only)
- Per-day food assignment (slots are per-trip pools, not per-day schedules)
- Configurable slot calorie split in the UI (default 25/40/35, configurable later)
- Plan alternates / swap options within a proposed plan
- Per-day drink mix variation (same quantity every day)

## Further Notes

### Design interview
Full transcript of the design session is at `docs/sessions/2026-04-01-food-planning-agent-design.md`. All decisions above trace back to specific user responses in that session.

### Key user insight: snack hoarding psychology
The user identified a specific behavioral pattern: when a snack item is scarce (only 1-2 servings on the trip), they hoard it and save it for later, leading to a worse trail experience. The solution is deliberate: stock enough servings of each item that scarcity anxiety doesn't kick in. This directly informs the agent's "fewer items, more servings" strategy and should be treated as a hard constraint, not a soft preference.

### Packing format
All meals are packed into individual ziplocks. This doesn't change the data model but is relevant context for the packing screen workflow.

### Implementation plans
Six implementation plans already exist in `docs/plans/`:
- `10-snack-categories.md` — stories 1-2
- `11-meal-slots.md` — stories 3-5, 7
- `12-drink-mix-config.md` — stories 10-12
- `13-slot-calorie-meters.md` — stories 6, 8-9
- `14-food-planning-agent.md` — stories 15-26
- `15-ratings.md` — stories 13-14

Dependency order: 10 → 11 → 12, 13 (parallel). Plans 14 and 15 can start immediately.
