# Daily Plan — Bar Chart & Layout

## Parent spec

[docs/specs/09-daily-meal-plan.md](../specs/09-daily-meal-plan.md)

## What to build

Add a stacked bar chart showing calories per day by category at the top of the daily plan screen. Each bar is segmented by the 5 food categories using consistent app colors. A horizontal target line per day shows the calorie goal (scaled for partial days). Day detail sections are laid out side-by-side on desktop. Shortage warnings from the auto-fill are displayed visually.

## Type

AFK

## Blocked by

- Blocked by `25-daily-plan-manual-editing.md`

## User stories addressed

- User story 3 — stacked bar chart for daily calorie overview
- User story 4 — target calorie line per day
- User story 15 — all day details visible at once on desktop
- User story 16 — stacks cleanly on mobile

## Acceptance criteria

- [x] Stacked bar chart at top of daily plan with X = days, Y = calories
- [x] Bars segmented by 5 categories using consistent app color scheme
- [x] Horizontal target line per day, scaled for partial days
- [x] Day labels show "Day 1 (half)", "Day 2", etc.
- [x] Day detail sections laid out in a grid on desktop (all visible)
- [x] Layout stacks vertically on mobile
- [x] Drink mix shortage warnings displayed when applicable
- [x] Chart updates when assignments change (after manual edits)

## Tasks

- [x] Choose and install a charting library (or build with CSS/SVG if simple enough)
- [x] Build stacked bar chart component with category segments
- [x] Add target calorie line per day (accounting for partial day fractions)
- [x] Apply consistent category colors from elsewhere in the app
- [x] Implement responsive grid layout for day detail sections (multi-column desktop, stacked mobile)
- [x] Display shortage warnings from the auto-fill response
- [x] Ensure chart re-renders when assignment data changes
