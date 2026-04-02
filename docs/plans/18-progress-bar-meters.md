# Progress Bar Meters

## Parent spec

`docs/specs/04-utility-audit.md`

## What to build

Replace the badge-based status indicators in TripSummary with progress bars for calories and weight per food category (breakfast, dinner, snacks). Each bar fills relative to the target midpoint, is color-coded by deviation, shows delta text, and caps visually at 100%. Add an overall cal/oz number.

## Type

AFK

## Blocked by

- Blocked by `16-slot-simplification.md` (needs two-slot model for correct snack category grouping)

## User stories addressed

- User story 9: Progress bars for calories and weight per category
- User story 10: Color thresholds (green/yellow/orange/red)
- User story 11: Delta text on progress bars
- User story 12: Cal/oz number in summary
- User story 13: Visual cap at 100%

## Acceptance criteria

- [ ] Three category sections (Breakfast, Dinner, Snacks) each show calories and weight progress bars
- [ ] Progress bars fill relative to target range midpoint
- [ ] Bars cap visually at 100% even when over target
- [ ] Color thresholds: green (within 5%), yellow (10%), orange (20%), red (>20%)
- [ ] Delta text shown next to each bar: "+10 oz", "-80 cal", or "on target"
- [ ] Overall cal/oz number displayed in summary
- [ ] StatusBadge component removed or no longer used for calorie/weight indicators

## Tasks

- [ ] Create a reusable ProgressMeter component with fill %, color thresholds, delta text, and 100% cap
- [ ] Compute per-category (breakfast, dinner, snacks) actual vs target values in TripSummary
- [ ] Replace StatusBadge usage with ProgressMeter for each category's calories and weight
- [ ] Add overall cal/oz calculation and display (total calories / total weight)
- [ ] Verify color thresholds match spec: green ≤5%, yellow ≤10%, orange ≤20%, red >20%
- [ ] Visual check on mobile and desktop layouts
