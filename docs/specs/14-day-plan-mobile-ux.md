# 14 — Day Plan Mobile UX

## Problem Statement

The day plan's item action buttons (remove "x", increment "+") only appear on hover. This works on desktop but is invisible on mobile/touch devices — the user reported not being able to remove items from days at all. The allocation day-picker buttons in the unallocated section are also small and hard to tap on mobile.

## Solution

Make all interactive controls visible and usable on touch devices without hover. Keep the desktop experience clean (hover-reveal is fine there), but ensure mobile always has access to actions.

## User Stories

1. As a mobile user, I want to see remove and increment buttons on day plan items without hovering, so that I can manage allocations from my phone.
2. As a mobile user, I want tap targets large enough to use reliably, so that I don't mis-tap when adjusting allocations.

## Implementation Decisions

### Always-Visible Actions on Mobile

Use CSS media queries or touch detection to make action buttons always visible on small screens / touch devices. On desktop, keep the current hover-reveal behavior.

Approach: Use `@media (hover: none)` to target touch devices. When hover is unavailable, show buttons at reduced opacity or in a compact inline layout that's always visible.

### Tap Target Sizing

The day-picker buttons in the unallocated section (currently `h-6 w-8`) are small for touch. On mobile, increase to at least 44x44px tap targets (Apple HIG minimum).

### Layout Adjustments

On mobile, the day-picker buttons could wrap to multiple rows if there are many days. Ensure wrapping doesn't break the layout. Consider a horizontal scroll or grid layout for the day buttons on mobile.

## Out of Scope

- Swipe gestures for remove/move actions
- Drag-and-drop between days
- Mobile-specific navigation patterns (bottom sheets, etc.)
