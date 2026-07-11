import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse } from '../test/apiMock';

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
});
