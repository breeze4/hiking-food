# 06 — Collapsible Category Grid

## Problem Statement

The trip planner page has nearly a full page of meters at the top: overall cal/weight, then a 5-row category grid (breakfast, dinner, lunch, snacks, drink mixes), then the meal section with its own inline meters. This is redundant and wastes vertical space, pushing actual planning controls below the fold.

## Solution

Make the 5-category grid in the trip summary collapsed by default. The overall total cal/weight meters remain always visible. Inline section meters (meals, snacks, lunch, drink mixes) remain unchanged — with the category grid collapsed, they become the primary per-section feedback.

## User Stories

1. As a trip planner, I want the summary section to be compact by default, so that I can see my planning controls without scrolling past a wall of meters.
2. As a trip planner, I want to expand the category grid when I need a cross-category overview, so that I can still drill into per-category detail when needed.
3. As a trip planner, I want the overall cal/weight meters always visible, so that I always have a high-level sense of where my plan stands.

## Implementation Decisions

- The 5-category grid (breakfast, dinner, lunch, snacks, drink mixes rows x cal/weight columns) gets wrapped in a collapsible section, collapsed by default.
- Collapse state does not need to persist across page loads — default to collapsed every time.
- The expand/collapse toggle should be a simple disclosure arrow or similar minimal affordance.
- No backend changes required.

## Testing Decisions

- No automated tests needed. This is a pure UI layout change.

## Out of Scope

- Removing any existing meters or sections.
- Changing the data or calculations behind the meters.
- Persisting collapse state.
