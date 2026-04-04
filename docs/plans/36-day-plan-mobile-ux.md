# Plan 36 — Day Plan Mobile UX

Spec: `docs/specs/14-day-plan-mobile-ux.md`
Issue: #12

## Summary

Make day plan action buttons (remove, increment) usable on touch devices where hover doesn't exist. Improve tap target sizes for the unallocated day-picker buttons.

## Changes

### Frontend: DailyPlanPage.jsx

- [x] **Always-visible actions on touch devices**: The remove "×" and increment "+" buttons currently use `opacity-0 group-hover:opacity-100`. Add a media query override so they're always visible on touch devices. Use Tailwind's approach: replace `opacity-0 group-hover:opacity-100` with a class pattern that shows buttons on touch. Simplest approach: `opacity-0 group-hover:opacity-100 touch:opacity-100` via a custom utility, or use `@media (hover: none)` in CSS.

  Concrete change: Add to the app's global CSS (or a Tailwind plugin):
  ```css
  @media (hover: none) {
    .touch-visible { opacity: 1 !important; }
  }
  ```
  Then add `touch-visible` class alongside the existing opacity classes on both buttons.

- [x] **Reduce visual noise on mobile**: Since buttons are always visible on mobile, use reduced opacity (e.g., `opacity-60`) rather than full opacity, so they don't dominate the layout. Full opacity on tap/active.

- [x] **Larger tap targets for day-picker buttons**: The unallocated section's day buttons are `h-6 w-8` (24x32px). On mobile, increase to at least `h-9 w-10` (36x40px). Use responsive classes: `h-6 w-8 sm:h-6 sm:w-8` as the desktop size, `h-9 w-10` as the base (mobile-first).

- [x] **Larger tap targets for item action buttons**: The "+" and "×" buttons in day cards are bare `<button>` elements with `px-1`. On mobile, add padding to meet ~40px minimum. Use `p-2 sm:px-1 sm:py-0` or similar.

### Tests

- [x] **Visual verification**: Check on mobile viewport that buttons are visible without hover and tap targets are usable.

## Review

(to be filled after implementation)
