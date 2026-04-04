# Per-Section Meters & Summary Relayout

## Problem Statement

The summary dashboard currently lives in a sidebar, showing all budget meters (breakfast, dinner, snacks, combined) in one place. When working within a specific section (e.g. adjusting lunch snacks), you have to look over at the sidebar to see how your changes affect the budget. There's no inline visual feedback per section, and on mobile the sidebar is hidden entirely behind navigation.

## Solution

Move the summary to a full-width section at the top of the trip planner page (no longer a sidebar). Add inline calorie and weight meters to each of the five food sections (breakfast, dinner, lunch, snacks, drink mixes) so you can see budget status in context while working. The top summary retains a compact view of all categories plus combined totals for the full picture at a glance.

## User Stories

1. As a trip planner, I want to see per-section calorie and weight meters inline with each food section, so that I can see budget impact without looking elsewhere.
2. As a trip planner, I want the summary at the top of the page showing all categories in a compact grid, so that I get a full overview before diving into sections.
3. As a trip planner, I want combined total meters (cal + weight) in the top summary, so that I can see overall trip budget status.
4. As a trip planner, I want text stats (cal/day, oz/day, total days) in the top summary, so that I have the key reference numbers visible.
5. As a trip planner, I want the breakfast section header to show calorie and weight progress bars, so that I can see if I'm over or under on breakfasts.
6. As a trip planner, I want the dinner section header to show calorie and weight progress bars, so that I can see if I'm over or under on dinners.
7. As a trip planner, I want the lunch slot section header to show calorie and weight progress bars against the lunch slot target, so that I can budget lunch items visually.
8. As a trip planner, I want the snacks slot section header to show calorie and weight progress bars against the snack slot target, so that I can budget snack items visually.
9. As a trip planner, I want the drink mix section header to show calorie and weight progress bars plus a servings budget bar, so that I have full visibility into drink mix status.
10. As a trip planner, I want the meters to use the same color-coding system (green/yellow/orange/red based on deviation from target midpoint), so that the visual language is consistent everywhere.
11. As a trip planner, I want the top summary grid to show all five categories as rows with calorie and weight columns, so that I can compare categories at a glance.
12. As a trip planner, I want inline meters to stack vertically on mobile (cal on top, weight below), so that they remain readable on narrow screens.
13. As a trip planner, I want the top summary to scroll with the page (not be sticky), because per-section meters provide the contextual feedback I need while working.

## Implementation Decisions

### Layout Change

- Remove the sidebar summary card entirely
- Add a full-width summary section at the top of the trip planner, above all food sections
- Summary section scrolls with the page (not sticky)

### Top Summary Content

Three parts:
1. **Combined totals**: Two full-width ProgressMeter bars (total calories, total weight)
2. **Category grid**: A compact table with 5 rows (breakfast, dinner, lunch, snacks, drink mixes) and 2 columns (calories bar, weight bar). Each cell contains a small inline progress bar with actual/target numbers. Same color logic as existing ProgressMeter.
3. **Text stats**: cal/day, oz/day, total days — displayed compactly

### Inline Section Meters

Each section header gets meters using the existing ProgressMeter component (or a compact variant):
- **Breakfast**: cal + weight, targets from ±10% of per-recipe average × days (same logic as current summary)
- **Dinner**: cal + weight, same target approach as breakfast
- **Lunch slot**: cal + weight, targets from backend `slot_subtotals`
- **Snacks slot**: cal + weight, targets from backend `slot_subtotals`
- **Drink mixes**: cal + weight + servings. Cal/weight targets computed dynamically from selected mixes' per-serving averages × servings budget (`drink_mixes_per_day × total_days`). Servings bar uses existing budget logic.

### Drink Mix Cal/Weight Targets

Computed client-side from the selected drink mixes on the trip:
- Average cal per serving = sum of (each mix's cal_per_serving) / number of selected mixes
- Average weight per serving = sum of (each mix's weight_per_serving) / number of selected mixes
- Target = average per serving × drink_mixes_per_day × total_days
- Use ±10% for low/high range (consistent with meal targets)
- If no mixes selected, no target (meters show actual only or are hidden)

### Compact ProgressMeter Variant

The existing ProgressMeter works for full-width display. For the category grid and inline section meters, create a compact variant that:
- Has a shorter bar height
- Shows actual/target inline rather than below
- Omits the delta text in the grid (keep it for inline section meters)
- Uses the same color logic

### Mobile Layout

- Top summary grid: categories stack vertically, each category shows cal bar then weight bar
- Inline section meters: cal bar on top, weight bar below
- Drink mixes: cal, weight, servings — three rows stacked

### No Backend Changes

All data needed is already available from the summary endpoint:
- `slot_subtotals` for lunch/snacks targets and actuals
- `breakfast_calories`, `breakfast_weight`, `breakfast_count` for breakfast
- `dinner_calories`, `dinner_weight`, `dinner_count` for dinner
- `drink_mix_calories`, `drink_mix_weight` for drink mix actuals
- Per-trip-snack data for computing drink mix averages
- Combined totals and targets for overall meters

## Testing Decisions

This is primarily a frontend layout/UI change with no new backend logic. The existing ProgressMeter color logic is the most testable piece — it's already implemented and would just be reused.

- No new backend tests needed (no API changes)
- Manual visual testing across screen sizes (desktop wide, tablet, mobile) to verify layout and meter rendering
- Verify that meter values match the existing summary card values before removing the sidebar (sanity check during development)

## Out of Scope

- Sticky/pinned summary header — intentionally not sticky, per-section meters handle contextual feedback
- Backend API changes — everything needed is already available
- Configurable slot calorie split (40/60) — existing future feature, not part of this work
- Stacked/segmented bars showing category contributions to total — considered and rejected in favor of per-category rows

## Further Notes

- The drink mix cal/weight targets are approximate by design — they exist for visual consistency, not precision budgeting. The servings meter is the primary drink mix budget tool.
- The top summary is intentionally redundant with inline meters. Top summary = full picture at a glance. Inline = contextual feedback while editing.
