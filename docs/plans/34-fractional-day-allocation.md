# Plan 34 — Fractional Day Allocation

Spec: `docs/specs/12-fractional-day-allocation.md`
Issue: #12

## Summary

Allow allocating fractional servings (especially 0.5) from the unallocated pool and via the increment button on day items.

## Changes

### Frontend: DailyPlanPage.jsx

- [x] **Serving amount toggle on unallocated items**: Add a small toggle next to each unallocated item's day buttons. Two states: "1" and "½". Default is "1". When set to "½", day buttons allocate 0.5 servings instead of 1. Use a simple `<Button>` that toggles between the two values.

- [x] **Auto-detect fractional remaining**: When an unallocated item has `remaining_servings < 1`, auto-set the allocation amount to match the remaining (e.g., 0.5 remaining → allocate 0.5). The toggle reflects this.

- [x] **Pass fractional servings to addToDay**: Update `addToDay()` to accept a servings parameter instead of hardcoded `servings: 1`. Read from the toggle state per item.

- [x] **Fractional increment button**: Update `incrementServings()` to respect the same toggle. When toggle is "½", increment by 0.5 instead of 1. Or simpler: add a second "½" button next to the existing "+" on day items.

- [x] **Display fractional servings**: Update the serving display (`×${item.servings}`) to show fractional values: "×0.5", "×1.5", etc. Currently only shows when `servings > 1` — also show when servings is fractional (e.g., 0.5).

### Backend

No backend changes needed. The API already accepts float servings on both create and update endpoints.

### Tests

- [x] **Frontend behavior**: Verify toggle switches between 1 and 0.5, day buttons send correct servings value, display shows fractional amounts.

## Review

(to be filled after implementation)
