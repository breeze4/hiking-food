import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from './App';
import {
  apiResponse, createApiMock, makeTripDetail, defaultTrips as trips,
} from './test/apiMock';

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

  test('a fresh visit to root lands on the last-selected trip, not the first', async () => {
    // Land on trip 2 first so the app remembers it.
    window.history.replaceState({}, '', '/hiking-food/trips/2');
    const first = render(<App />);
    expect(await screen.findByRole('heading', { name: 'Goat Rocks' })).toBeVisible();
    first.unmount();

    // Returning to the bare root should redirect to trip 2, not default to trip 1.
    window.history.replaceState({}, '', '/hiking-food/');
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'Goat Rocks' })).toBeVisible();
    expect(window.location.pathname).toBe('/hiking-food/trips/2');
  });

  test('editing a snack refreshes in place without unmounting the planner', async () => {
    window.history.replaceState({}, '', '/hiking-food/trips/1');
    const detail = makeTripDetail({
      id: 1,
      name: 'Wonderland Trail',
      snacks: [{
        id: 10, catalog_item_id: 5, ingredient_name: 'Trail Mix',
        category: 'salty', slot: 'snacks', servings: 2,
        weight_per_serving: 2, calories_per_serving: 250,
        total_weight: 4, total_calories: 500, calories_per_oz: 125, trip_notes: '',
      }],
    });
    let detailCalls = 0;
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      trips: [{ id: 1, name: 'Wonderland Trail' }],
      tripDetails: { 1: detail },
      handler: (path, method) => {
        if (method === 'GET' && path === '/hiking-food/api/trips/1') {
          detailCalls += 1;
          // Let the refresh triggered by the edit hang, so a collapse would be
          // observable: pre-fix, the detail was blanked and the whole planner
          // fell back to its placeholder.
          if (detailCalls >= 2) return new Promise(() => {});
        }
        return undefined;
      },
    })));
    render(<App />);

    const increase = await screen.findAllByRole('button', { name: 'Increase Trail Mix servings' });
    fireEvent.click(increase[0]);

    await waitFor(() => expect(detailCalls).toBeGreaterThanOrEqual(2));
    // Planner content is still mounted; the placeholder never appeared.
    expect(screen.getAllByRole('heading', { name: 'Wonderland Trail' }).length).toBeGreaterThan(0);
    expect(screen.queryByText('Select or create a trip to get started.')).not.toBeInTheDocument();
    expect(screen.getAllByText('Trail Mix').length).toBeGreaterThan(0);
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
    for (const link of screen.getAllByRole('link', { name: 'Trip Planner' })) {
      expect(link).toHaveAttribute('href', '/hiking-food/trips/1');
    }
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
