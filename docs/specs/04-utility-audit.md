# Utility Audit

GitHub Issue: #10

## Problem Statement

While prepping an actual trip, several usability issues surfaced: the morning/afternoon snack slot distinction creates unnecessary categorization friction, drink mix auto-allocation fights the user instead of helping, calorie indicators don't convey magnitude, recipe tables lack visual structure, and mobile layout has padding problems.

## Solution

Six changes that remove friction from trip planning: collapse snack slots to a simpler two-slot model, give drink mixes manual control with budget guidance, replace status badges with progress bars that show how far off-target you are, add zebra striping to tables that lack it, and fix mobile layout issues.

## User Stories

1. As a trip planner, I want a single "snacks" slot instead of separate morning/afternoon slots, so that I don't have to categorize snacks into time-of-day buckets that don't matter to me.
2. As a trip planner, I want snack slot options to be "Lunch" and "Snacks" with a 40/60 calorie split, so that my calorie budgets reflect how I actually eat on trail.
3. As a trip planner, I want existing morning_snack and afternoon_snack assignments migrated to the new "snacks" slot, so that my current trip data isn't broken by the change.
4. As a trip planner, I want the snack slot dropdown to always show human-readable names, so that I never see raw database values like "morning_snack".
5. As a trip planner, I want to manually set drink mix servings, so that I control exactly how many packets of each type I bring.
6. As a trip planner, I want drink mix servings to always be whole numbers, so that they match the reality of individual packets.
7. As a trip planner, I want the mixes/day setting to act as a budget indicator with a meter, so that I can see whether my manual selections are in the right ballpark without the system overwriting my choices.
8. As a trip planner, I want a new drink mix to start at 1 serving when added, so that I have a sensible default without auto-allocation.
9. As a trip planner, I want progress bars for calories and weight on each food category (snacks, breakfast, dinner), so that I can see at a glance how close I am to my targets.
10. As a trip planner, I want progress bars colored by how far off-target I am (green within 5%, yellow within 10%, orange within 20%, red beyond), so that I can quickly identify what needs tweaking.
11. As a trip planner, I want the progress bar to show the delta as text (e.g. "+10 oz", "-80 cal"), so that I know the exact amount I'm over or under.
12. As a trip planner, I want a cal/oz number displayed in the summary, so that I can assess overall food density.
13. As a trip planner, I want progress bars to cap visually at 100% even when over target, so that the layout doesn't break.
14. As a trip planner, I want zebra-striped rows in recipe ingredient tables, so that they're easier to scan like the other tables in the app.
15. As a mobile user, I want proper padding in the navigation menu, so that text isn't pressed against the left edge of the screen.
16. As a mobile user, I want all screens to have consistent padding, readable text, and no horizontal overflow, so that the app is usable on a phone.

## Implementation Decisions

### Slot simplification

- Replace the three-slot model (morning_snack, lunch, afternoon_snack) with two slots: `lunch` and `snacks`.
- Calorie split becomes 40% lunch / 60% snacks (was 25/40/35).
- DB migration: update all trip_snack rows where slot is `morning_snack` or `afternoon_snack` to `snacks`.
- Backend `CATEGORY_TO_SLOT` mapping updated: bars_energy, salty, sweet all map to `snacks`. Lunch stays `lunch`.
- Frontend `SLOTS` array becomes two entries. `SLOT_DEFAULT_CATEGORIES` for snacks includes bars_energy + salty + sweet.
- Slot calorie meters in TripSummary update to show two slots instead of three.
- The snake_case display bug is resolved by this change (fewer values, clean labels).
- The "snack search doesn't find items" issue is resolved by this change (no need to split one item across two slots).

### Drink mix changes

- Remove `_recalc_drink_mix_servings()` auto-allocation from the backend. The function and all call sites go away.
- `drink_mixes_per_day` on the trip remains as a budget reference, not a control input for auto-calculation.
- Drink mix servings become editable in the UI (same +/- controls as regular snacks, but stepping by 1 instead of 0.5).
- Backend enforces whole-number servings for drink_mix category items: round up any fractional value on write.
- When adding a drink mix to a trip, default servings = 1.
- Drink mix section shows a budget meter: "X of Y budget servings" where Y = mixes_per_day * total_days. Uses the same color thresholds as calorie meters.

### Calorie/weight meters

- Replace the current badge-based status indicators (below/in range/above) with progress bars.
- Three category sections: Breakfast, Dinner, Snacks. Each shows a calories progress bar and a weight progress bar.
- An overall cal/oz number is displayed (total calories / total weight across all categories).
- Progress bar fills relative to the target range midpoint. Bar caps at 100% visually.
- Delta shown as text next to the bar: "+10 oz", "-80 cal", or "on target".
- Color thresholds based on percentage deviation from target midpoint:
  - Green: within 5%
  - Yellow: within 10%
  - Orange: within 20%
  - Red: beyond 20%

### Zebra striping

- Add `even:bg-muted/50` to recipe ingredient table rows in recipe editing.
- Add `even:bg-muted/50` to meal selection table rows.
- Matches the pattern already used in snack selection and snack catalog tables.

### Mobile audit

- Fix navigation Sheet padding so text has proper left margin.
- Audit all screens for: horizontal overflow, text truncation on long names, touch target sizing, card/content padding consistency.
- Screens to audit: trip planner, snack selection, meal selection, recipe library, recipe edit, ingredient database, packing screen, trip summary.

## Testing Decisions

Good tests for this work verify external behavior through the API and UI, not internal implementation details.

- **Backend slot migration**: test that after migration, no trip_snack rows have morning_snack or afternoon_snack as slot values.
- **Backend drink mix rounding**: test that creating/updating a drink_mix trip snack with fractional servings results in a rounded-up whole number.
- **Backend auto-allocation removed**: test that updating trip days or mixes_per_day does NOT change existing drink mix servings.
- **Summary endpoint**: test that the summary returns two slot subtotals (lunch, snacks) with correct 40/60 split targets.
- Existing backend tests (pytest) provide the pattern for these.

No frontend unit tests — verify visually and via the mobile audit.

## Out of Scope

- Configurable slot calorie split per trip (future feature, stays in spec as-is).
- Snack ratings influencing sort order in the add panel.
- Packing screen redesign (user hasn't audited it yet, may file follow-up).
- Food planning agent updates (agent prompt references slots, but that's a separate plan update once slots are stable).

## Further Notes

- The food planning agent definition (plan 14) references the old three-slot model and will need its prompt updated after this work lands. Track as a separate task.
- The slot simplification is a data migration — back up the DB before running it on beebaby.
