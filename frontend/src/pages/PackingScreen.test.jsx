import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse, makePackingUnit } from '../test/apiMock';

function packing() {
  return {
    trip_name: 'Wonderland Trail',
    meals: [],
    snacks: [{
      id: 50, ingredient_name: 'Nuts', slot: 'lunch', packed: false,
      servings: 2, target_weight: 2, target_calories: 200, actual_weight_oz: null,
    }],
  };
}

// A structured trip's packing detail: the legacy sections plus a units section.
function structuredPacking(units = [makePackingUnit()]) {
  return { trip_name: 'Olympics 2026', meals: [], snacks: [], units };
}

function requestBody(method, path) {
  const call = fetch.mock.calls.find(([url, options]) => (
    options?.method === method
    && new URL(url, window.location.origin).pathname === path
  ));
  return call ? JSON.parse(call[1].body) : null;
}

beforeEach(() => {
  window.history.replaceState({}, '', '/hiking-food/trips/1/packing');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('PackingScreen', () => {
  test('recipe assembly shows per-serving amounts with a per-baggie multiplier', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      packings: {
        1: {
          trip_name: 'Wonderland Trail',
          meals: [{
            id: 7, recipe_name: 'Granola', category: 'breakfast', quantity: 4,
            at_home_prep: null, packed: false, actual_weight_oz: null,
            ingredients: [{
              name: 'Rolled Oats', amount_oz: 4, total_oz: 16,
              essentials: false, packing_method: 'bag',
            }],
          }],
          snacks: [],
        },
      },
    })));
    render(<App />);

    expect(await screen.findByText('Assemble 4 baggies — per-serving amounts below.')).toBeVisible();
    // Per-serving amount is shown, not the 16oz combined total.
    expect(screen.getByRole('cell', { name: '4' })).toBeVisible();
    expect(screen.getByRole('cell', { name: '×4 = 16' })).toBeVisible();
  });

  test('a failed pack toggle shows an inline error without blanking the page', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      packings: { 1: packing() },
      handler: (path, method) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1/snacks/50') {
          return jsonResponse({ detail: 'Pack failed' }, 500);
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('checkbox', { name: 'Nuts packed' }));

    expect(await screen.findByText('Pack failed')).toBeVisible();
    // Page is still rendered (not replaced by a full-page error).
    expect(screen.getByRole('heading', { name: 'Packing: Wonderland Trail' })).toBeVisible();
  });

  test('the pack toggle disables while its mutation is in flight', async () => {
    let releasePut;
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      packings: { 1: packing() },
      handler: (path, method) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1/snacks/50') {
          return new Promise((resolve) => {
            releasePut = () => resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
          });
        }
        return undefined;
      },
    })));
    render(<App />);

    const checkbox = await screen.findByRole('checkbox', { name: 'Nuts packed' });
    fireEvent.click(checkbox);

    // base-ui Checkbox reflects disabled via aria-disabled rather than a native attribute.
    await waitFor(() => expect(
      screen.getByRole('checkbox', { name: 'Nuts packed' }),
    ).toHaveAttribute('aria-disabled', 'true'));
    releasePut();
    await waitFor(() => expect(
      screen.getByRole('checkbox', { name: 'Nuts packed' }),
    ).not.toHaveAttribute('aria-disabled', 'true'));
  });
});

describe('PackingScreen snack unit assembly', () => {
  test('a unit group reads as make N of a type at the trip target', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      packings: { 1: structuredPacking() },
    })));
    render(<App />);

    expect(await screen.findByText('Make 6 × Trail Mix Bag @ 2 oz')).toBeVisible();
    // The bag recipe, so packing day does not need the unit library open.
    expect(screen.getByText('1 oz Almonds + 1 oz M&Ms')).toBeVisible();
    expect(screen.getByText('0/1 packed')).toBeVisible();
  });

  test('checking off a group packs every selection behind it', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      packings: {
        1: structuredPacking([makePackingUnit({
          count: 6,
          selections: [
            { id: 50, quantity: 4, packed: false, actual_weight_oz: null },
            { id: 51, quantity: 2, packed: false, actual_weight_oz: null },
          ],
        })]),
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('checkbox', { name: 'Trail Mix Bag units packed' }));

    await waitFor(() => expect(
      requestBody('PUT', '/hiking-food/api/trips/1/snack-units/50'),
    ).toEqual({ packed: true }));
    expect(requestBody('PUT', '/hiking-food/api/trips/1/snack-units/51')).toEqual({ packed: true });
  });

  test('an actual unit weight saves against the selection', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      packings: { 1: structuredPacking() },
    })));
    render(<App />);

    const weight = await screen.findByRole('spinbutton', {
      name: 'Trail Mix Bag unit actual weight',
    });
    fireEvent.blur(weight, { target: { value: '2.1' } });

    await waitFor(() => expect(
      requestBody('PUT', '/hiking-food/api/trips/1/snack-units/50'),
    ).toEqual({ actual_weight_oz: 2.1 }));
  });

  test('a unit off the trip target is badged', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      packings: {
        1: structuredPacking([makePackingUnit({ unit_weight: 3, weight_warning: true })]),
      },
    })));
    render(<App />);

    expect(await screen.findByText('Off target')).toBeVisible();
  });

  test('a legacy trip has no unit assembly section', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({ packings: { 1: packing() } })));
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Snack Packing' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Snack Unit Assembly' })).toBeNull();
  });
});
