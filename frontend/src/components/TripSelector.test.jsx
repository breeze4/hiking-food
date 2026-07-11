import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import App from '../App';
import { createApiMock, jsonResponse } from '../test/apiMock';

beforeEach(() => {
  window.history.replaceState({}, '', '/hiking-food/recipes');
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('TripSelector trip mutations', () => {
  test('a failed create keeps the dialog open and shows an error', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      handler: (path, method) => {
        if (method === 'POST' && path === '/hiking-food/api/trips') {
          return jsonResponse({ detail: 'Create failed' }, 500);
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: 'New' }));
    fireEvent.change(await screen.findByPlaceholderText('Trip name'), {
      target: { value: 'Enchantments' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(await screen.findByText('Create failed')).toBeVisible();
    // Dialog stays open so the user can retry.
    expect(screen.getByRole('button', { name: 'Create' })).toBeVisible();
  });

  test('a failed delete surfaces an error', async () => {
    vi.stubGlobal('fetch', vi.fn(createApiMock({
      handler: (path, method) => {
        if (method === 'DELETE' && path === '/hiking-food/api/trips/1') {
          return jsonResponse({ detail: 'Delete failed' }, 500);
        }
        return undefined;
      },
    })));
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: 'Delete' }));
    const confirmDelete = (await screen.findAllByRole('button', { name: 'Delete' })).at(-1);
    fireEvent.click(confirmDelete);

    expect(await screen.findByText('Delete failed')).toBeVisible();
  });
});
