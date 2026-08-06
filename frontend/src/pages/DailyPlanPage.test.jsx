import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse, makeDailyPlan } from '../test/apiMock';

function snackItem(overrides = {}) {
  return {
    id: 500, name: 'Trail Mix', slot: 'afternoon_snacks', source_type: 'snack',
    source_id: 77, servings: 2, calories: 300, weight: 3, ...overrides,
  };
}

function initialPlan() {
  return makeDailyPlan({
    days: [{
      day_number: 1, day_type: 'full', target_calories: 2000,
      items: [snackItem()], macros: null,
    }],
    unallocated: [{
      name: 'Trail Mix', category: 'snacks', source_type: 'snack',
      source_id: 77, remaining_servings: 4,
    }],
    unallocated_summary: { count: 1, total_calories: 300, total_weight: 3 },
  });
}

function unitItem(overrides = {}) {
  return {
    id: 600, name: 'Trail Mix Bag', slot: 'morning_snacks', source_type: 'snack_unit',
    source_id: 12, category: 'bag', servings: 1, calories: 300, weight: 2, ...overrides,
  };
}

function unitPlan(overrides = {}) {
  return makeDailyPlan({
    days: [{
      day_number: 1, day_type: 'full', target_calories: 2000,
      items: [
        unitItem(),
        unitItem({ id: 601, name: 'Jerky Bag', source_id: 13, slot: 'afternoon_snacks', calories: 129, weight: 1.5 }),
      ],
      macros: null,
    }],
    ...overrides,
  });
}

beforeEach(() => {
  window.history.replaceState({}, '', '/hiking-food/trips/1/daily-plan');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('DailyPlanPage', () => {
  test('day-assign and per-item controls expose accessible names identifying the item', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({ dailyPlans: { 1: initialPlan() } })));
    render(<App />);

    expect(await screen.findByRole('button', { name: 'Assign Trail Mix to day 1' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Add half serving of Trail Mix' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Add serving of Trail Mix' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Remove Trail Mix' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Allocate ½ serving of Trail Mix' })).toBeVisible();
  });

  test('an assignment mutation updates the rendered plan from the response body', async () => {
    const updatedPlan = makeDailyPlan({
      days: [{
        day_number: 1, day_type: 'full', target_calories: 2000,
        items: [snackItem(), snackItem({ id: 501, name: 'Fresh Assignment', source_id: 78 })],
        macros: null,
      }],
      unallocated: [],
      unallocated_summary: { count: 0, total_calories: 0, total_weight: 0 },
    });
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      dailyPlans: { 1: initialPlan() },
      handler: (path, method) => {
        if (method === 'POST' && path === '/hiking-food/api/trips/1/daily-plan/assignments') {
          return jsonResponse(updatedPlan);
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: 'Assign Trail Mix to day 1' }));

    expect(await screen.findByText(/Fresh Assignment/)).toBeVisible();
  });

  test('a failed assignment surfaces a visible error and leaves the page usable', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      dailyPlans: { 1: initialPlan() },
      handler: (path, method) => {
        if (method === 'POST' && path === '/hiking-food/api/trips/1/daily-plan/assignments') {
          return jsonResponse({ detail: 'Assignment rejected' }, 500);
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: 'Assign Trail Mix to day 1' }));

    expect(await screen.findByText('Assignment rejected')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Assign Trail Mix to day 1' })).toBeEnabled();
  });
});

describe('DailyPlanPage snack units', () => {
  test('unit assignments render in both snack slots with their weight and calories', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({ dailyPlans: { 1: unitPlan() } })));
    render(<App />);

    expect(await screen.findByText('Morning Snacks')).toBeVisible();
    expect(screen.getByText('Afternoon Snacks')).toBeVisible();
    expect(screen.getByText(/Trail Mix Bag/)).toBeVisible();
    expect(screen.getByText('2.0 oz · 300 cal')).toBeVisible();
    expect(screen.getByText('1.5 oz · 129 cal')).toBeVisible();
  });

  test('a unit counts up by whole units and offers no half serving', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({ dailyPlans: { 1: unitPlan() } })));
    render(<App />);

    expect(await screen.findByRole('button', { name: 'Add unit of Trail Mix Bag' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Remove Trail Mix Bag' })).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Add half serving of Trail Mix Bag' })).toBeNull();
  });

  test('an unallocated unit is measured in units and assigns to a day', async () => {
    const assigned = unitPlan({
      days: [{
        day_number: 1, day_type: 'full', target_calories: 2000,
        items: [unitItem(), unitItem({ id: 602, name: 'Fig Bar', source_id: 14 })],
        macros: null,
      }],
    });
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      dailyPlans: {
        1: unitPlan({
          unallocated: [{
            name: 'Fig Bar', category: 'packaged', source_type: 'snack_unit',
            source_id: 14, remaining_servings: 2,
          }],
          unallocated_summary: { count: 1, total_calories: 500, total_weight: 4 },
        }),
      },
      handler: (path, method) => {
        if (method === 'POST' && path === '/hiking-food/api/trips/1/daily-plan/assignments') {
          return jsonResponse(assigned);
        }
        return undefined;
      },
    })));
    render(<App />);

    expect(await screen.findByText('2 units')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Allocate ½ serving of Fig Bar' })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Assign Fig Bar to day 1' }));

    // The day item carries the per-item controls; the pool row never did.
    expect(await screen.findByRole('button', { name: 'Add unit of Fig Bar' })).toBeVisible();
  });
});
