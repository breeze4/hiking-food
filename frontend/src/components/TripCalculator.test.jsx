import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse, makeTripDetail } from '../test/apiMock';

beforeEach(() => {
  window.history.replaceState({}, '', '/hiking-food/trips/1');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('TripCalculator', () => {
  test('a failed debounced save surfaces a visible error', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      handler: (path, method) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1') {
          return jsonResponse({ detail: 'Save failed' }, 500);
        }
        return undefined;
      },
    })));
    render(<App />);

    const firstDay = await screen.findByLabelText('First day');
    fireEvent.change(firstDay, { target: { value: '0.5' } });

    expect(await screen.findByText('Save failed', {}, { timeout: 2000 })).toBeVisible();
  });

  test('inputs disable while a save is in flight, then re-enable', async () => {
    let releaseSave;
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      handler: (path, method) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1') {
          return new Promise((resolve) => {
            releaseSave = () => resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
          });
        }
        return undefined;
      },
    })));
    render(<App />);

    const firstDay = await screen.findByLabelText('First day');
    fireEvent.change(firstDay, { target: { value: '0.5' } });

    await waitFor(() => expect(screen.getByLabelText('First day')).toBeDisabled(), { timeout: 2000 });
    releaseSave();
    await waitFor(() => expect(screen.getByLabelText('First day')).toBeEnabled());
  });

  test('a structured trip shows its snack unit configuration', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      tripDetails: {
        1: makeTripDetail({ snack_model: 'structured', snacks_per_day: 4, oz_per_snack: 2 }),
      },
    })));
    render(<App />);

    expect(await screen.findByLabelText('Snacks/day')).toHaveValue(4);
    expect(screen.getByLabelText('Oz/snack')).toHaveValue(2);
    expect(screen.getByText('Structured')).toBeVisible();
  });

  test('a legacy trip hides the snack unit configuration', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      tripDetails: {
        1: makeTripDetail({ snack_model: 'legacy', snacks_per_day: 4, oz_per_snack: 2 }),
      },
    })));
    render(<App />);

    expect(await screen.findByLabelText('First day')).toBeVisible();
    expect(screen.getByText('Legacy')).toBeVisible();
    expect(screen.queryByLabelText('Snacks/day')).toBeNull();
    expect(screen.queryByLabelText('Oz/snack')).toBeNull();
  });

  test('editing snacks per day saves the new value', async () => {
    const saved = [];
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      tripDetails: { 1: makeTripDetail({ snack_model: 'structured' }) },
      handler: (path, method, options) => {
        if (method === 'PUT' && path === '/hiking-food/api/trips/1') {
          saved.push(JSON.parse(options.body));
          return jsonResponse({});
        }
        return undefined;
      },
    })));
    render(<App />);

    const snacksPerDay = await screen.findByLabelText('Snacks/day');
    fireEvent.change(snacksPerDay, { target: { value: '6' } });

    await waitFor(() => expect(saved).toHaveLength(1), { timeout: 2000 });
    expect(saved[0].snacks_per_day).toBe(6);
    expect(saved[0].snack_model).toBeUndefined();
  });
});
