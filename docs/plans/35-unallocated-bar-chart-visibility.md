# Plan 35 — Unallocated Bar Chart Visibility

Spec: `docs/specs/13-unallocated-bar-chart-visibility.md`
Issue: #12

## Summary

Show unallocated food totals prominently near the bar chart so the user can see plan completeness at a glance.

## Changes

### Backend: routers/daily_plan.py

- [x] **Add unallocated summary to response**: In `_build_daily_plan_response`, compute aggregate totals for the unallocated pool and add to the response:
  ```
  "unallocated_summary": {
    "count": len(unallocated),
    "total_calories": sum of remaining_servings * calories_per_serving,
    "total_weight": sum of remaining_servings * weight_per_serving
  }
  ```

### Frontend: DailyPlanPage.jsx

- [x] **Unallocated banner**: Add a summary line between the bar chart and the day cards. Show when `unallocated_summary.count > 0`:
  - Format: "3 items unallocated (420 cal · 6.2 oz)"
  - Style: warning-toned text (amber/orange), consistent with the existing warning style
  - When count is 0: show "All food allocated" in muted green text

### Tests

- [x] **Backend test**: Verify `unallocated_summary` fields are correct — count, calories, weight. Test with zero unallocated and with some unallocated.

## Review

(to be filled after implementation)
