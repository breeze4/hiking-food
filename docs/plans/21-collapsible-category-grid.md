# Collapsible Category Grid

## Parent spec

[docs/specs/06-collapsible-category-grid.md](../specs/06-collapsible-category-grid.md)

## What to build

Wrap the 5-category breakdown grid (breakfast, dinner, lunch, snacks, drink mixes × cal/weight) in a collapsible section, collapsed by default. The overall total cal/weight meters at the top of the summary remain always visible. Clicking a disclosure toggle expands/collapses the grid. No persistence of collapse state needed.

## Type

AFK

## Blocked by

None — can start immediately

## User stories addressed

- User story 1 — compact summary by default
- User story 2 — expand category grid when needed
- User story 3 — overall meters always visible

## Acceptance criteria

- [x] Category grid is collapsed by default on page load
- [x] Clicking the toggle expands the grid, clicking again collapses it
- [x] Overall cal/weight meters remain visible regardless of collapse state
- [x] Inline section meters (meals, snacks, lunch, drink mixes) are unaffected
- [x] Toggle affordance is visually clear (disclosure arrow or similar)

## Tasks

- [x] Identify the category grid component in TripSummary
- [x] Wrap the grid in a collapsible container with local React state (default collapsed)
- [x] Add a disclosure toggle (chevron icon + label like "Category Breakdown")
- [x] Verify overall meters and inline section meters are unaffected
- [x] Test on mobile layout
