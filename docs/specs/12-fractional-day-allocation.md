# 12 — Fractional Day Allocation

## Problem Statement

Some items — especially drink mixes like Carnation Breakfast Essentials — need to be split across days (e.g., 0.5 servings per day). The backend already supports fractional servings (FLOAT column), but the UI only allows adding whole servings from the unallocated pool. The "Add to Day" buttons always send `servings: 1`, and the increment button on existing assignments also adds +1. There's no way to allocate half a serving to a day.

## Solution

Add fractional serving support to the day plan UI. When adding an item from the unallocated pool or incrementing an existing assignment, the user can choose a fractional amount. Keep the common case (whole servings) fast while making fractions accessible.

## User Stories

1. As a trip planner, I want to add 0.5 servings of a drink mix to a day, so that I can split a packet across two days.
2. As a trip planner, I want to see the fractional serving amount displayed on each day's item, so that I know how much I'm allocating.
3. As a trip planner, I want the unallocated pool to correctly show fractional remaining amounts, so that I can see what's left to distribute.

## Implementation Decisions

### Adding from Unallocated Pool

Replace the bare day-number buttons with a small popover or inline control that lets the user pick a serving amount before confirming. Default to 1 serving, but offer 0.5 as a preset and allow typing a custom value.

Interaction flow:
1. User clicks a day number button on an unallocated item
2. If the item has >= 1 remaining serving, allocate 1 serving immediately (current behavior, fast path)
3. If the item has < 1 remaining serving, allocate the remaining amount immediately
4. To allocate a fractional amount when >= 1 remains: long-press or secondary action (e.g., a "..." menu or holding shift) opens a serving picker

Alternative (simpler): Add a small toggle or dropdown near the unallocated item that sets the "allocation amount" (1, 0.5, or custom). When toggled to 0.5, all day buttons for that item allocate 0.5.

### Incrementing Existing Assignments

The existing "+" button on day items increments by 1. Add the same fractional option: default +1, with a way to do +0.5.

### Display

Show fractional servings with one decimal place: "x0.5", "x1.5". Already partially handled — the frontend shows "xN" for servings > 1, just needs to handle non-integers.

## Out of Scope

- Auto-fill algorithm changes (it already handles fractional distribution)
- Arbitrary precision — 0.5 increments cover the use case
- Changing total trip servings from the day plan screen
