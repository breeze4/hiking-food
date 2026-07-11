import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse } from '../test/apiMock';

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

beforeEach(() => {
  window.history.replaceState({}, '', '/hiking-food/trips/1/packing');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('PackingScreen', () => {
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
