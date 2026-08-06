import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse, makeSnackUnitType } from '../test/apiMock';

const INGREDIENTS = [
  { id: 10, name: 'Almonds', calories_per_oz: 183 },
  { id: 11, name: 'M&Ms', calories_per_oz: 138 },
];

function trailMixBag(overrides = {}) {
  return makeSnackUnitType({
    id: 1,
    name: 'Trail Mix Bag',
    composition: [
      { id: 1, ingredient_id: 10, ingredient_name: 'Almonds', amount_oz: 1, calories: 183 },
      { id: 2, ingredient_id: 11, ingredient_name: 'M&Ms', amount_oz: 1, calories: 138 },
    ],
    weight_oz: 2,
    calories: 321,
    cal_per_oz: 160.5,
    ...overrides,
  });
}

beforeEach(() => {
  window.history.replaceState({}, '', '/hiking-food/snack-units');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('SnackUnitLibraryPage', () => {
  test('building a bag from two ingredients shows its derived weight and calories', async () => {
    const saved = [];
    let postBody = null;
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      ingredients: INGREDIENTS,
      snackUnitTypes: () => saved,
      handler: (path, method, options) => {
        if (method === 'POST' && path === '/hiking-food/api/snack-unit-types') {
          postBody = JSON.parse(options.body);
          // What the server would send back: the same bag, with derived values.
          saved.push(trailMixBag({ name: postBody.name }));
          return jsonResponse(saved[0], 201);
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: '+ Add Bag' }));
    fireEvent.change(screen.getByLabelText('Name'), {
      target: { value: 'Trail Mix Bag' },
    });

    fireEvent.change(screen.getByLabelText('Ingredient to add'), { target: { value: '10' } });
    fireEvent.change(screen.getByLabelText('Amount in ounces to add'), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));

    // One ingredient in: the running total is the composition so far.
    expect(screen.getByText('Bag total: 1 oz · 183 cal')).toBeVisible();

    fireEvent.change(screen.getByLabelText('Ingredient to add'), { target: { value: '11' } });
    fireEvent.change(screen.getByLabelText('Amount in ounces to add'), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));

    expect(screen.getByText('Bag total: 2 oz · 321 cal')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(postBody).not.toBeNull();
    });
    expect(postBody.name).toBe('Trail Mix Bag');
    expect(postBody.composition).toEqual([
      { ingredient_id: 10, amount_oz: 1 },
      { ingredient_id: 11, amount_oz: 1 },
    ]);
    // The saved bag is listed with the values the server derived.
    expect(await screen.findByRole('cell', { name: 'Almonds 1 oz + M&Ms 1 oz' })).toBeVisible();
  });

  test('a bag outside the weight tolerance is badged, an on-target bag is not', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      ingredients: INGREDIENTS,
      snackUnitTypes: [
        trailMixBag(),
        trailMixBag({
          id: 2, name: 'Big Nut Bag', weight_oz: 3, calories: 549, weight_warning: true,
        }),
      ],
    })));
    render(<App />);

    expect(await screen.findByRole('cell', { name: 'Big Nut Bag' })).toBeVisible();
    const badges = screen.getAllByText('Off target');
    expect(badges).toHaveLength(1);
    expect(badges[0]).toBeVisible();
  });

  test('a bag missing per-oz ingredient data is badged as partial', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      ingredients: INGREDIENTS,
      snackUnitTypes: [trailMixBag({ has_full_data: false })],
    })));
    render(<App />);

    expect(await screen.findByText('Partial data')).toBeVisible();
  });

  test('deleting a bag that a trip uses surfaces the conflict message', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      ingredients: INGREDIENTS,
      snackUnitTypes: [trailMixBag()],
      handler: (path, method) => {
        if (method === 'DELETE' && path === '/hiking-food/api/snack-unit-types/1') {
          return jsonResponse({
            detail: 'Cannot delete: snack unit type is used in trip snack selections',
          }, 409);
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: 'Delete Trail Mix Bag' }));
    fireEvent.click(screen.getAllByRole('button', { name: 'Delete' }).at(-1));

    expect(await screen.findByText(
      'Cannot delete: snack unit type is used in trip snack selections',
    )).toBeVisible();

    // The bag survives: it is still listed once the dialog is dismissed.
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(await screen.findByRole('cell', { name: 'Trail Mix Bag' })).toBeVisible();
  });

  test('editing a bag sends its whole composition back', async () => {
    let putBody = null;
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      ingredients: INGREDIENTS,
      snackUnitTypes: [trailMixBag()],
      handler: (path, method, options) => {
        if (method === 'PUT' && path === '/hiking-food/api/snack-unit-types/1') {
          putBody = JSON.parse(options.body);
          return jsonResponse({});
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: 'Edit Trail Mix Bag' }));
    fireEvent.change(screen.getByLabelText('Almonds amount in ounces'), {
      target: { value: '1.5' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(putBody).not.toBeNull();
    });
    expect(putBody.composition).toEqual([
      { ingredient_id: 10, amount_oz: 1.5 },
      { ingredient_id: 11, amount_oz: 1 },
    ]);
  });
});
