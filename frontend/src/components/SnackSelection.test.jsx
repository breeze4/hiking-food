import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import {
  createApiMock, jsonResponse, makeSnackUnitType, makeSummary, makeTripDetail,
  makeTripSnackUnit,
} from '../test/apiMock';

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

// --- Structured snack units ---

const bar = {
  id: 100, ingredient_name: 'Energy Bar', category: 'bars_energy',
  weight_per_serving: 2, calories_per_serving: 250, calories_per_oz: 125,
};

const bagUnit = makeTripSnackUnit({
  id: 50, unit_type_id: 1, kind: 'bag', name: 'Trail Mix Bag', quantity: 4,
  total_weight: 8, total_calories: 1200,
});

const barUnit = makeTripSnackUnit({
  id: 51, unit_type_id: null, catalog_item_id: 100, kind: 'packaged',
  name: 'Energy Bar', quantity: 8, weight_oz: 2, calories: 250,
  total_weight: 16, total_calories: 2000,
});

function structuredSummary(overrides = {}) {
  return makeSummary({
    snack_units: { quota: 14, filled: 12, per_day: [2, 4, 4, 2] },
    slot_subtotals: {
      lunch: { weight: 0, calories: 0, target_cal: 800, target_cal_low: 720, target_cal_high: 880, days_covered: 0 },
      snacks: { weight: 24, calories: 3200 },
    },
    ...overrides,
  });
}

function structuredMock({ units = [bagUnit, barUnit], summary, ...rest } = {}) {
  return createApiMock({
    snacks: [bar],
    snackUnitTypes: [makeSnackUnitType({ id: 1, name: 'Trail Mix Bag' })],
    tripDetails: { 1: makeTripDetail({ snack_units: units }) },
    summaries: { 1: summary ?? structuredSummary() },
    ...rest,
  });
}

function requestBody(method, path) {
  const call = fetch.mock.calls.find(([url, options]) => (
    options?.method === method
    && new URL(url, window.location.origin).pathname === path
  ));
  return call ? JSON.parse(call[1].body) : null;
}

describe('SnackSelection structured units', () => {
  test('the units meter reads filled against the trip quota', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock()));
    render(<App />);

    const meter = await screen.findByRole('progressbar', { name: 'Units filled' });
    expect(meter).toHaveAttribute('aria-valuenow', '12');
    expect(meter).toHaveAttribute('aria-valuemax', '14');
    // Weight and calories stay as secondary readouts under the meter.
    expect(screen.getAllByText(/24 oz · 3200 cal/)[0]).toBeVisible();
    expect(screen.getByText(/2 \+ 4 \+ 4 \+ 2 by day/)).toBeVisible();
    expect(screen.queryByText('Complete')).toBeNull();
  });

  test('the units meter reads complete once the quota is filled', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock({
      summary: structuredSummary({
        snack_units: { quota: 14, filled: 14, per_day: [2, 4, 4, 2] },
      }),
    })));
    render(<App />);

    const meter = await screen.findByRole('progressbar', { name: 'Units filled' });
    expect(meter).toHaveAttribute('aria-valuenow', '14');
    expect(screen.getAllByText('Complete').length).toBeGreaterThan(0);
  });

  test('the add panel offers library bags and packaged snacks', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock({ units: [] })));
    render(<App />);

    // Sections in order: Drink Mixes, Lunch, Snack Units.
    const addButtons = await screen.findAllByRole('button', { name: '+ Add' });
    fireEvent.click(addButtons[addButtons.length - 1]);

    fireEvent.click(await screen.findByRole('button', { name: 'Add Trail Mix Bag' }));
    await waitFor(() => expect(
      requestBody('POST', '/hiking-food/api/trips/1/snack-units'),
    ).toEqual({ unit_type_id: 1 }));
  });

  test('adding a packaged snack posts a catalog unit selection', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock({ units: [] })));
    render(<App />);

    const addButtons = await screen.findAllByRole('button', { name: '+ Add' });
    fireEvent.click(addButtons[addButtons.length - 1]);

    fireEvent.click(await screen.findByRole('button', { name: 'Add Energy Bar' }));
    await waitFor(() => expect(
      requestBody('POST', '/hiking-food/api/trips/1/snack-units'),
    ).toEqual({ catalog_item_id: 100 }));
  });

  test('the quantity stepper saves the new unit count', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock()));
    render(<App />);

    const increase = (await screen.findAllByRole('button', {
      name: 'Increase Trail Mix Bag units',
    }))[0];
    const getsBefore = countGetTripDetail();
    fireEvent.click(increase);

    await waitFor(() => expect(
      requestBody('PUT', '/hiking-food/api/trips/1/snack-units/50'),
    ).toEqual({ quantity: 5 }));
    await waitFor(() => expect(countGetTripDetail()).toBeGreaterThan(getsBefore));
  });

  test('a unit outside the trip tolerance is badged', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock({
      units: [
        makeTripSnackUnit({ id: 50, name: 'Trail Mix Bag', weight_warning: false }),
        makeTripSnackUnit({
          id: 52, unit_type_id: 2, name: 'Big Bag', weight_oz: 3,
          total_weight: 3, weight_warning: true,
        }),
      ],
    })));
    render(<App />);

    // Desktop table and mobile card both render the badge for the heavy bag.
    expect((await screen.findAllByText('Off target')).length).toBe(2);
  });

  test('a unit can be marked packed with its actual weight', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock()));
    render(<App />);

    const packed = (await screen.findAllByRole('checkbox', {
      name: 'Trail Mix Bag packed',
    }))[0];
    fireEvent.click(packed);
    await waitFor(() => expect(
      requestBody('PUT', '/hiking-food/api/trips/1/snack-units/50'),
    ).toEqual({ packed: true }));

    const weight = screen.getByRole('spinbutton', { name: 'Trail Mix Bag actual weight' });
    fireEvent.blur(weight, { target: { value: '2.3' } });
    await waitFor(() => expect(fetch.mock.calls.some(([url, options]) => (
      options?.method === 'PUT'
      && new URL(url, window.location.origin).pathname === '/hiking-food/api/trips/1/snack-units/50'
      && JSON.parse(options.body).actual_weight_oz === 2.3
    ))).toBe(true));
  });

  test('removing a unit deletes the selection', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock()));
    render(<App />);

    const remove = (await screen.findAllByRole('button', { name: 'Remove Trail Mix Bag' }))[0];
    fireEvent.click(remove);

    await waitFor(() => expect(fetch.mock.calls.some(([url, options]) => (
      options?.method === 'DELETE'
      && new URL(url, window.location.origin).pathname === '/hiking-food/api/trips/1/snack-units/50'
    ))).toBe(true));
  });

  test('the trip summary meters units instead of a snack calorie band', async () => {
    vi.stubGlobal('fetch', vi.fn(structuredMock()));
    render(<App />);

    const meter = await screen.findByRole('progressbar', { name: 'Snack units filled' });
    expect(meter).toHaveAttribute('aria-valuenow', '12');
    expect(meter).toHaveAttribute('aria-valuemax', '14');
  });

  test('a legacy trip keeps the snacks slot and shows no unit section', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      snacks: [bar],
      tripDetails: {
        1: makeTripDetail({ snack_model: 'legacy', snacks: [lunchSnack()] }),
      },
      summaries: {
        1: makeSummary({
          slot_subtotals: {
            lunch: { weight: 0, calories: 0, target_cal: 800, target_cal_low: 720, target_cal_high: 880, days_covered: 0 },
            snacks: { weight: 0, calories: 0, target_cal: 1200, target_cal_low: 1080, target_cal_high: 1320, days_covered: 0 },
          },
        }),
      },
    })));
    render(<App />);

    // The snacks slot still steers by its 60% calorie band.
    expect(await screen.findByText('0 / 1,200 cal')).toBeVisible();
    // The nav keeps its link to the library; the planner grows no unit section.
    expect(screen.queryByRole('heading', { name: 'Snack Units' })).toBeNull();
    expect(screen.queryByRole('progressbar', { name: 'Units filled' })).toBeNull();
    expect(screen.queryByRole('progressbar', { name: 'Snack units filled' })).toBeNull();
    // Both slot sections still offer their add panels.
    expect(screen.getAllByRole('button', { name: '+ Add' }).length).toBe(3);
  });
});
