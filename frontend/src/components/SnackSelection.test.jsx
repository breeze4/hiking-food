import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse, makeTripDetail } from '../test/apiMock';

const catalog = [
  {
    id: 100, ingredient_name: 'Beef Jerky', category: 'lunch',
    weight_per_serving: 2, calories_per_serving: 150, calories_per_oz: 75,
  },
];

function lunchSnack(overrides = {}) {
  return {
    id: 20, catalog_item_id: 20, ingredient_name: 'Tuna Packet', category: 'lunch',
    slot: 'lunch', servings: 2, total_weight: 4, total_calories: 300,
    calories_per_oz: 75, trip_notes: '', ...overrides,
  };
}

function drinkMix(overrides = {}) {
  return {
    id: 30, catalog_item_id: 30, ingredient_name: 'Skratch Mix', category: 'drink_mix',
    slot: 'snacks', servings: 3, total_weight: 3, total_calories: 240, trip_notes: '', ...overrides,
  };
}

function seedTrip(snackOverrides) {
  return { 1: makeTripDetail({ snacks: [lunchSnack(snackOverrides), drinkMix()] }) };
}

function countGetTripDetail() {
  return fetch.mock.calls.filter(([url, options]) => (
    (options?.method ?? 'GET') === 'GET'
    && new URL(url, window.location.origin).pathname === '/hiking-food/api/trips/1'
  )).length;
}

beforeEach(() => {
  window.history.replaceState({}, '', '/hiking-food/trips/1');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('SnackSelection', () => {
  test('every per-snack control exposes an accessible name identifying the snack', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({ snacks: catalog, tripDetails: seedTrip() })));
    render(<App />);

    // Desktop + mobile both render, so the +/- and remove appear twice.
    expect((await screen.findAllByRole('button', { name: 'Increase Tuna Packet servings' })).length).toBe(2);
    expect(screen.getAllByRole('button', { name: 'Decrease Tuna Packet servings' }).length).toBe(2);
    expect(screen.getAllByRole('button', { name: 'Remove Tuna Packet' }).length).toBe(2);
    expect(screen.getAllByLabelText('Tuna Packet slot').length).toBe(2);
    // Desktop-only controls.
    expect(screen.getByRole('spinbutton', { name: 'Tuna Packet servings' })).toBeVisible();
    expect(screen.getByRole('textbox', { name: 'Tuna Packet notes' })).toBeVisible();

    // Drink mixes get the same treatment.
    expect(screen.getAllByRole('button', { name: 'Increase Skratch Mix servings' }).length).toBe(2);
    expect(screen.getAllByRole('button', { name: 'Remove Skratch Mix' }).length).toBe(2);
    expect(screen.getByRole('textbox', { name: 'Skratch Mix notes' })).toBeVisible();
  });

  test('a successful servings change refreshes the trip and renders the updated value', async () => {
    const tripDetails = seedTrip();
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      snacks: catalog,
      tripDetails,
      handler: (path, method, options) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1/snacks/20') {
          tripDetails[1].snacks[0].servings = JSON.parse(options.body).servings;
          return jsonResponse({});
        }
        return undefined;
      },
    })));
    render(<App />);

    const increase = (await screen.findAllByRole('button', { name: 'Increase Tuna Packet servings' }))[0];
    const getsBefore = countGetTripDetail();
    fireEvent.click(increase);

    await waitFor(() => expect(
      screen.getByRole('spinbutton', { name: 'Tuna Packet servings' }),
    ).toHaveValue(3));
    expect(countGetTripDetail()).toBeGreaterThan(getsBefore);
  });

  test('a failed servings change surfaces a visible error', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      snacks: catalog,
      tripDetails: seedTrip(),
      handler: (path, method) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1/snacks/20') {
          return jsonResponse({ detail: 'Snack update failed' }, 500);
        }
        return undefined;
      },
    })));
    render(<App />);

    const decrease = (await screen.findAllByRole('button', { name: 'Decrease Tuna Packet servings' }))[0];
    fireEvent.click(decrease);

    expect(await screen.findByText('Snack update failed')).toBeVisible();
  });

  test('per-snack controls disable while a mutation is in flight', async () => {
    let releasePut;
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      snacks: catalog,
      tripDetails: seedTrip(),
      handler: (path, method) => {
        if (method === 'DELETE' && path === '/hiking-food/api/trips/1/snacks/20') {
          return new Promise((resolve) => {
            releasePut = () => resolve({ ok: true, status: 204, json: () => Promise.resolve(null) });
          });
        }
        return undefined;
      },
    })));
    render(<App />);

    const remove = (await screen.findAllByRole('button', { name: 'Remove Tuna Packet' }))[0];
    fireEvent.click(remove);

    await waitFor(() => expect(remove).toBeDisabled());
    releasePut();
    await waitFor(() => expect(
      screen.getAllByRole('button', { name: 'Increase Tuna Packet servings' })[0],
    ).toBeEnabled());
  });

  test('catalog add buttons expose "Add <name>" and a successful add refreshes the trip', async () => {
    const tripDetails = seedTrip();
    let posted = false;
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      snacks: catalog,
      tripDetails,
      handler: (path, method) => {
        if (method === 'POST' && path === '/hiking-food/api/trips/1/snacks') {
          posted = true;
          return jsonResponse({});
        }
        return undefined;
      },
    })));
    render(<App />);

    // Open the Lunch slot's add panel (Drink Mixes is first, Lunch is second).
    const addButtons = await screen.findAllByRole('button', { name: '+ Add' });
    fireEvent.click(addButtons[1]);

    const addJerky = await screen.findByRole('button', { name: 'Add Beef Jerky' });
    const getsBefore = countGetTripDetail();
    fireEvent.click(addJerky);

    await waitFor(() => expect(posted).toBe(true));
    await waitFor(() => expect(countGetTripDetail()).toBeGreaterThan(getsBefore));
  });
});
