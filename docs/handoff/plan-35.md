# Plan 35: Unallocated Bar Chart Visibility

## Response field
- `unallocated_summary` added to the daily plan API response, containing `count`, `total_calories`, `total_weight`

## Banner location in JSX
- `frontend/src/pages/DailyPlanPage.jsx`, between the `<StackedBarChart>` and the day cards grid div

## Test function
- `test_unallocated_summary` in `backend/tests/test_daily_plan.py`
