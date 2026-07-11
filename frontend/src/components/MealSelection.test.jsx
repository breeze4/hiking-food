import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse, makeTripDetail } from '../test/apiMock';

const recipes = [{ id: 42, name: 'Trail Porridge', category: 'breakfast' }];

function meal(overrides = {}) {
  return {
    id: 10,
    recipe_name: 'Trail Porridge',
    category: 'breakfast',
    quantity: 1,
    weight_per_unit: 5,
    total_weight: 5,
    total_calories: 500,
    ...overrides,
  };
}

function seedTrip(mealOverrides) {
  return { 1: makeTripDetail({ meals: [meal(mealOverrides)] }) };
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

describe('MealSelection', () => {
  test('quantity steppers expose accessible names that identify the meal', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({ recipes, tripDetails: seedTrip() })));
    render(<App />);

    expect(await screen.findByRole('button', { name: 'Increase Trail Porridge quantity' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Decrease Trail Porridge quantity' })).toBeVisible();
  });

  test('a successful quantity change refreshes the trip and renders the updated value', async () => {
    const tripDetails = seedTrip();
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      recipes,
      tripDetails,
      handler: (path, method, options) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1/meals/10') {
          tripDetails[1].meals[0].quantity = JSON.parse(options.body).quantity;
          return jsonResponse({});
        }
        return undefined;
      },
    })));
    render(<App />);

    const increase = await screen.findByRole('button', { name: 'Increase Trail Porridge quantity' });
    const getsBefore = countGetTripDetail();
    fireEvent.click(increase);

    await waitFor(() => expect(screen.getByText('2')).toBeVisible());
    expect(countGetTripDetail()).toBeGreaterThan(getsBefore);
  });

  test('a failed quantity change surfaces a visible error and leaves the app usable', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      recipes,
      tripDetails: seedTrip(),
      handler: (path, method) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1/meals/10') {
          return jsonResponse({ detail: 'Server exploded' }, 500);
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: 'Increase Trail Porridge quantity' }));

    expect(await screen.findByText('Server exploded')).toBeVisible();
    // Still usable: the control is present and re-enabled.
    expect(screen.getByRole('button', { name: 'Increase Trail Porridge quantity' })).toBeEnabled();
  });

  test('the stepper is disabled while its mutation is in flight', async () => {
    let releasePut;
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      recipes,
      tripDetails: seedTrip(),
      handler: (path, method) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1/meals/10') {
          return new Promise((resolve) => {
            releasePut = () => resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
          });
        }
        return undefined;
      },
    })));
    render(<App />);

    const increase = await screen.findByRole('button', { name: 'Increase Trail Porridge quantity' });
    fireEvent.click(increase);

    await waitFor(() => expect(increase).toBeDisabled());
    releasePut();
    await waitFor(() => expect(
      screen.getByRole('button', { name: 'Increase Trail Porridge quantity' }),
    ).toBeEnabled());
  });
});
