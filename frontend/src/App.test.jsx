import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from './App';


const trips = [
  { id: 1, name: 'Wonderland Trail' },
  { id: 2, name: 'Goat Rocks' },
];

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

function apiResponse(url, options = {}) {
  const path = new URL(url, window.location.origin).pathname;
  if (options.method === 'DELETE' && path.match(/\/hiking-food\/api\/trips\/\d+$/)) {
    return jsonResponse(null, 204);
  }
  if (path === '/hiking-food/api/trips') return jsonResponse(trips);
  if (
    path === '/hiking-food/api/recipes'
    || path === '/hiking-food/api/snacks'
    || path === '/hiking-food/api/ingredients'
    || path === '/hiking-food/api/food-intake'
  ) {
    return jsonResponse([]);
  }
  if (path === '/hiking-food/api/recipes/42') {
    return jsonResponse({
      id: 42,
      name: 'Trail Porridge',
      category: 'breakfast',
      ingredients: [],
    });
  }
  if (path.match(/\/hiking-food\/api\/trips\/\d+\/daily-plan$/)) {
    return jsonResponse({
      days: [],
      unallocated: [],
      unallocated_summary: { count: 0, total_calories: 0, total_weight: 0 },
      warnings: [],
      macro_target: { protein_pct: 20, fat_pct: 30, carb_pct: 50 },
    });
  }
  if (path.match(/\/hiking-food\/api\/trips\/\d+\/summary$/)) {
    return jsonResponse({
      total_days: 1,
      total_cal: 2750,
      total_weight: 22,
      combined_calories: 0,
      combined_weight: 0,
      weight_per_day: 0,
      cal_per_day: 0,
      breakfast_weight: 0,
      breakfast_calories: 0,
      breakfast_count: 0,
      dinner_weight: 0,
      dinner_calories: 0,
      dinner_count: 0,
      daytime_weight: 0,
      drink_mix_weight: 0,
      drink_mix_calories: 0,
      slot_subtotals: {},
    });
  }
  const packingMatch = path.match(/\/hiking-food\/api\/trips\/(\d+)\/packing$/);
  if (packingMatch) {
    const trip = trips.find(({ id }) => id === Number(packingMatch[1]));
    return jsonResponse({ trip_name: trip?.name, meals: [], snacks: [] });
  }
  if (path.match(/\/hiking-food\/api\/trips\/\d+\/shopping-list$/)) {
    return jsonResponse({ items: [], essentials: [] });
  }
  const tripMatch = path.match(/\/hiking-food\/api\/trips\/(\d+)$/);
  if (tripMatch) {
    const trip = trips.find(({ id }) => id === Number(tripMatch[1]));
    return trip ? jsonResponse({
      ...trip,
      first_day_fraction: 1,
      full_days: 0,
      last_day_fraction: 0,
      drink_mixes_per_day: 2,
      oz_per_day: 22,
      cal_per_oz: 125,
      meals: [],
      snacks: [],
    }) : jsonResponse({ detail: 'Trip not found' }, 404);
  }
  throw new Error(`Unexpected API request: ${path}`);
}

describe('trip deep links', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/hiking-food/trips/2/daily-plan');
    vi.stubGlobal('fetch', vi.fn(apiResponse));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  test('a daily-plan URL makes its trip authoritative everywhere', async () => {
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Daily Plan' })).toBeVisible();
    await waitFor(() => {
      for (const selector of screen.getAllByLabelText('Active trip')) {
        expect(selector).toHaveValue('2');
      }
    });
    for (const link of screen.getAllByRole('link', { name: 'Daily Plan' })) {
      expect(link).toHaveAttribute('href', '/hiking-food/trips/2/daily-plan');
    }
    for (const link of screen.getAllByRole('link', { name: 'Packing' })) {
      expect(link).toHaveAttribute('href', '/hiking-food/trips/2/packing');
    }
  });

  test('switching trips preserves the daily-plan subroute', async () => {
    render(<App />);
    const selector = (await screen.findAllByLabelText('Active trip'))[0];

    fireEvent.change(selector, { target: { value: '1' } });

    await waitFor(() => {
      expect(window.location.pathname).toBe('/hiking-food/trips/1/daily-plan');
      for (const tripSelector of screen.getAllByLabelText('Active trip')) {
        expect(tripSelector).toHaveValue('1');
      }
    });
    expect(fetch.mock.calls.filter(([url]) => (
      new URL(url, window.location.origin).pathname === '/hiking-food/api/trips'
    ))).toHaveLength(1);
  });

  test('a planner URL loads and links to the same trip', async () => {
    window.history.replaceState({}, '', '/hiking-food/trips/2');

    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Goat Rocks' })).toBeVisible();
    for (const selector of screen.getAllByLabelText('Active trip')) {
      expect(selector).toHaveValue('2');
    }
    for (const link of screen.getAllByRole('link', { name: 'Trip Planner' })) {
      expect(link).toHaveAttribute('href', '/hiking-food/trips/2');
    }
  });

  test('packing deep links, trip switching, and back navigation keep trip identity', async () => {
    window.history.replaceState({}, '', '/hiking-food/trips/2/packing');
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'Packing: Goat Rocks' })).toBeVisible();

    fireEvent.change(screen.getAllByLabelText('Active trip')[0], {
      target: { value: '1' },
    });

    expect(await screen.findByRole('heading', { name: 'Packing: Wonderland Trail' })).toBeVisible();
    expect(window.location.pathname).toBe('/hiking-food/trips/1/packing');
    fireEvent.click(screen.getByRole('button', { name: 'Back to Planner' }));
    expect(await screen.findByRole('heading', { name: 'Wonderland Trail' })).toBeVisible();
    expect(window.location.pathname).toBe('/hiking-food/trips/1');
  });

  test('the legacy root redirects to the canonical selected-trip planner URL', async () => {
    window.history.replaceState({}, '', '/hiking-food/');

    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Wonderland Trail' })).toBeVisible();
    expect(window.location.pathname).toBe('/hiking-food/trips/1');
  });

  test('switching the selected trip on a global page keeps that page open', async () => {
    window.history.replaceState({}, '', '/hiking-food/recipes');
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'Recipes' })).toBeVisible();

    fireEvent.change(screen.getAllByLabelText('Active trip')[0], {
      target: { value: '2' },
    });

    await waitFor(() => {
      expect(window.location.pathname).toBe('/hiking-food/recipes');
      for (const link of screen.getAllByRole('link', { name: 'Trip Planner' })) {
        expect(link).toHaveAttribute('href', '/hiking-food/trips/2');
      }
      for (const link of screen.getAllByRole('link', { name: 'Daily Plan' })) {
        expect(link).toHaveAttribute('href', '/hiking-food/trips/2/daily-plan');
      }
    });
  });

  test('an unknown trip deep link shows a stable not-found boundary', async () => {
    window.history.replaceState({}, '', '/hiking-food/trips/999/packing');

    render(<App />);

    expect(await screen.findByText('Trip not found.')).toBeVisible();
    expect(window.location.pathname).toBe('/hiking-food/trips/999/packing');
    expect(fetch).not.toHaveBeenCalledWith(
      '/hiking-food/api/trips/999/packing',
      expect.anything(),
    );
  });

  test('an unknown subroute is reported without losing the trip URL', async () => {
    window.history.replaceState({}, '', '/hiking-food/trips/2/unknown');

    render(<App />);

    expect(await screen.findByText('Trip page not found.')).toBeVisible();
    expect(window.location.pathname).toBe('/hiking-food/trips/2/unknown');
  });

  test('the legacy packing URL redirects to the selected trip packing URL', async () => {
    window.history.replaceState({}, '', '/hiking-food/packing');

    render(<App />);

    expect(await screen.findByRole('heading', {
      name: 'Packing: Wonderland Trail',
    })).toBeVisible();
    expect(window.location.pathname).toBe('/hiking-food/trips/1/packing');
  });

  test.each([
    ['/recipes', 'Recipes'],
    ['/recipes/new', 'New Recipe'],
    ['/recipes/42', 'Edit: Trail Porridge'],
    ['/snacks', 'Snack Catalog'],
    ['/ingredients', 'Ingredients'],
    ['/intake', 'Food Intake'],
  ])('global deep link %s renders its page without redirecting', async (path, heading) => {
    window.history.replaceState({}, '', `/hiking-food${path}`);

    render(<App />);

    expect(await screen.findByRole('heading', { name: heading })).toBeVisible();
    expect(window.location.pathname).toBe(`/hiking-food${path}`);
  });

  test('deleting a trip continues the same subroute on the remaining trip', async () => {
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'Daily Plan' })).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    const deleteButtons = await screen.findAllByRole('button', { name: 'Delete' });
    fireEvent.click(deleteButtons.at(-1));

    await waitFor(() => {
      expect(window.location.pathname).toBe('/hiking-food/trips/1/daily-plan');
    });
    expect(await screen.findByRole('heading', { name: 'Daily Plan' })).toBeVisible();
  });

  test('a late response from the previous trip cannot overwrite the current route', async () => {
    window.history.replaceState({}, '', '/hiking-food/trips/2');
    let releaseTripTwo;
    vi.stubGlobal('fetch', vi.fn((url, options) => {
      const path = new URL(url, window.location.origin).pathname;
      if (path === '/hiking-food/api/trips/2') {
        return new Promise((resolve) => {
          releaseTripTwo = () => resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({
              ...trips[1], meals: [], snacks: [],
            }),
          });
        });
      }
      return apiResponse(url, options);
    }));
    render(<App />);
    await waitFor(() => expect(releaseTripTwo).toBeTypeOf('function'));

    fireEvent.change(screen.getAllByLabelText('Active trip')[0], {
      target: { value: '1' },
    });
    expect(await screen.findByRole('heading', { name: 'Wonderland Trail' })).toBeVisible();

    releaseTripTwo();
    await waitFor(() => {
      expect(window.location.pathname).toBe('/hiking-food/trips/1');
      expect(screen.queryByRole('heading', { name: 'Goat Rocks' })).not.toBeInTheDocument();
    });
  });
});
