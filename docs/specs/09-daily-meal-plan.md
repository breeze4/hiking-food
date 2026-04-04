# 09 — Daily Meal Plan

## Problem Statement

The trip planner works at the aggregate level — total servings, total calories, total weight. There's no way to see how food distributes across individual days. The user wants a gut-check: do I have enough food for each day? When do I run out of a snack? Are my partial days handled correctly? Without a per-day view, overpacking some days and underpacking others is invisible.

## Solution

A new screen that shows a day-by-day breakdown of all trip food. An auto-fill algorithm distributes food across days using sensible heuristics. The user can manually adjust assignments. A stacked bar chart provides a visual overview, with detailed item lists per day and an unallocated pool for remaining servings.

## User Stories

1. As a trip planner, I want to see my food distributed across each day of the trip, so that I can verify I have enough for every day.
2. As a trip planner, I want an auto-fill algorithm to distribute food using sensible defaults, so that I don't have to manually assign every item.
3. As a trip planner, I want to see a stacked bar chart showing calories per day by category, so that I get a quick visual gut-check on daily balance.
4. As a trip planner, I want a target calorie line on each day's bar, so that I can see which days are over or under target.
5. As a trip planner, I want partial days (first and last) to have proportionally reduced targets, so that half-days aren't flagged as underpacked.
6. As a trip planner, I want to remove an item from a day, returning it to the unallocated pool, so that I can adjust the distribution.
7. As a trip planner, I want to add a snack serving to a day that already has that snack, so that I can double up when it makes sense.
8. As a trip planner, I want to add items from the unallocated pool to a specific day using a day picker, so that I can manually place food where I want it.
9. As a trip planner, I want meals to only appear once per day (no doubling up), so that the plan reflects reality.
10. As a trip planner, I want a reset button that re-runs auto-fill after confirmation, so that I can start fresh if my manual edits went sideways.
11. As a trip planner, I want to see when an item runs out across the trip, so that I know "mixed nuts last 3 days then I'm out."
12. As a trip planner, I want breakfast drink mixes (coffee, carnation, greens) excluded from the first partial day, so that the plan reflects arriving mid-day.
13. As a trip planner, I want dinner drink mixes (tea) excluded from the last partial day, so that the plan reflects hiking out.
14. As a trip planner, I want the daily planner to flag when there aren't enough drink mixes to cover all eligible days, so that I know to add more or accept the gap.
15. As a trip planner, I want all day detail sections visible at once on desktop, so that I can work hands-on without clicking to drill in.
16. As a trip planner, I want the layout to stack cleanly on mobile without special treatment, so that it's usable from my phone even if desktop is the primary experience.

## Implementation Decisions

### Data Model

New table `trip_day_assignments`:

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY | |
| trip_id | INTEGER FK | |
| day_number | INTEGER | 1-based. Day 1 = first partial day |
| slot | TEXT | breakfast, breakfast_drinks, morning_snacks, lunch, afternoon_snacks, dinner, evening_drinks, all_day_drinks |
| source_type | TEXT | meal or snack |
| source_id | INTEGER | trip_meal.id or trip_snack.id |
| servings | REAL | For snacks: how many servings assigned to this day/slot. For meals: always 1 |

Day numbering: for a trip with 0.5 + 2 + 0.5 days, there are 4 days. Day 1 is the first half day, days 2-3 are full days, day 4 is the last half day. Target calories per day scale by the day's fraction.

### Slot Rules by Day Type

| Slot | First partial | Full day | Last partial |
|------|--------------|----------|-------------|
| breakfast | No | Yes | Yes |
| breakfast_drinks | No | Yes | Yes |
| morning_snacks | No | Yes | Yes |
| lunch | No | Yes | No |
| afternoon_snacks | Yes | Yes | No |
| dinner | Yes | Yes | No |
| evening_drinks | Yes | Yes | No |
| all_day_drinks | Yes | Yes | Yes |

### Auto-Fill Algorithm

**Meals (breakfast and dinner):**
1. Sort meals by weight descending (heaviest first).
2. Assign to eligible days in order (earliest day first). Each meal appears on exactly one day. If a trip_meal has quantity > 1, it has multiple servings to distribute — each serving goes to one day, still heaviest-first, earliest-day-first.
3. If more eligible days than meals, later days go without (they'll show as empty in that slot).

**Snacks (lunch, morning, afternoon):**
1. Sort snack items by weight per serving descending (heaviest first).
2. For each snack item, distribute 1 serving per eligible day, earliest day first, until servings run out.
3. Assign to slot based on existing trip_snack.slot: `lunch` -> lunch slot, `snacks` -> morning_snacks or afternoon_snacks (alternate, or fill morning first then afternoon).
4. After all items distributed, check if any day is still significantly under its calorie target — no auto-correction, just visible in the bar chart.

**Drink mixes:**
1. Group by drink_mix_type (breakfast, dinner, all_day).
2. For each group, identify eligible days per the slot rules table.
3. Distribute evenly across eligible days: 1 serving per eligible day, cycling through items if multiple drink mixes of the same type exist.
4. If total servings < eligible days, flag a warning ("not enough X to cover all days").

### Screen Layout

1. **Stacked bar chart** at top. X-axis = days (labeled "Day 1 (half)", "Day 2", etc.). Y-axis = calories. Stacked segments colored by the 5 categories (breakfast, dinner, lunch, snacks, drink mixes). Horizontal target line per day.
2. **Day detail sections** below the chart, all visible. Each day shows:
   - Day label and target calories
   - List of assigned items grouped by slot
   - Each item: name, calories, weight, remove button
   - Snacks: add button to increase servings on that day
   - Meals: remove only, no add/double-up
3. **Unallocated pool** at the bottom or side. Shows items with remaining unassigned servings. Each item has "Add to day" button that opens a day picker (numbered buttons 1, 2, 3... for each day).
4. **Reset to auto-fill** button with confirmation dialog.

### API Endpoints

- `GET /api/trips/{trip_id}/daily-plan` — returns all day assignments grouped by day, plus unallocated items and warnings
- `POST /api/trips/{trip_id}/daily-plan/auto-fill` — runs the auto-fill algorithm, replaces all existing assignments
- `POST /api/trips/{trip_id}/daily-plan/assignments` — add an item to a day/slot
- `DELETE /api/trips/{trip_id}/daily-plan/assignments/{id}` — remove an assignment (returns servings to pool)
- `PATCH /api/trips/{trip_id}/daily-plan/assignments/{id}` — update servings on an existing assignment

### Relationship to Trip Planner

- The daily plan screen is read-only with respect to total food quantities. You cannot add new food items here — only distribute what exists in trip_meals and trip_snacks.
- To add more food, go back to the trip planner.
- Changes on the trip planner (adding/removing meals or snacks, changing serving counts) may invalidate the daily plan. The daily plan should detect this and prompt for re-autofill or show warnings about orphaned assignments.

## Testing Decisions

Comprehensive test suite for the auto-fill algorithm. This is the core logic with real edge cases. Tests should verify external behavior (the resulting assignments), not internal implementation details.

**Test areas:**

- Meal distribution: correct days for breakfast vs dinner, heaviest-first ordering, quantity > 1 meals spread across days
- Partial day rules: first partial gets no breakfast/morning items, last partial gets no dinner/afternoon items
- Snack distribution: 1 serving per item per day, heaviest first, earliest day first, respects slot assignment
- Drink mix distribution: correct subcategory-to-slot mapping, even distribution, shortage warnings
- Edge cases: more meals than days, more days than meals, zero servings, single-day trip (one full day), trip that's all partial days (half + half), snack with 1 serving on a 5-day trip
- Reset: auto-fill clears previous assignments and rebuilds from scratch
- Unallocated pool: correctly shows remaining servings after partial distribution

Prior art: existing backend pytest suite.

## Out of Scope

- Per-day editing of food quantities (total servings managed on trip planner only).
- Moving items between days (remove from one, add to another via pool).
- Persisting collapse state or chart preferences.
- Optimizing for mobile editing experience (desktop-first, mobile just stacks).
- Automatic rebalancing after manual edits.

## Further Notes

- Depends on spec 08 (drink mix subcategories) for correct drink mix distribution.
- The stacked bar chart should use the same category color scheme used elsewhere in the app for consistency.
- The auto-fill algorithm is deterministic — same inputs always produce the same output, making it testable and predictable.
