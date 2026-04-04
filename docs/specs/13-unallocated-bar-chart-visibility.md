# 13 — Unallocated Bar Chart Visibility

## Problem Statement

The stacked bar chart at the top of the daily plan shows calories per day by category, but doesn't indicate how much food is unallocated. The user has to scroll to the bottom unallocated pool to see what's left. This makes it hard to tell at a glance whether the plan is complete or if significant food is still unassigned.

## Solution

Show unallocated calories prominently near the bar chart so the user can immediately see the plan's completeness without scrolling.

## User Stories

1. As a trip planner, I want to see total unallocated calories near the bar chart, so that I know at a glance whether my plan is complete.
2. As a trip planner, I want to understand how much food is unassigned relative to what's assigned, so that I can decide whether to keep distributing or accept the gap.

## Implementation Decisions

### Unallocated Summary Banner

Add a summary line above or below the bar chart showing:
- "X cal / Y oz unallocated" (or "All food allocated" when zero)
- Color-coded: neutral when zero, warning color when significant unallocated food remains

This is simpler and more useful than trying to encode unallocated into the chart itself (which would be confusing — unallocated food doesn't belong to any day).

### Unallocated Item Count

Include the count of unallocated items: "3 items (420 cal / 6.2 oz) unallocated" so the user knows the scale.

## Out of Scope

- Adding an "unallocated" bar segment to the chart (misleading — it's not a day)
- Changing the chart's target lines based on unallocated amounts
- Auto-distributing unallocated food
