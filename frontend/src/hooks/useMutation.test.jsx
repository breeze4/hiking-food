import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { useMutation } from './useMutation';

describe('useMutation', () => {
  test('pending is true while the mutation is in flight and false after it resolves', async () => {
    let release;
    const mutationFn = () => new Promise((resolve) => { release = resolve; });
    const { result } = renderHook(() => useMutation(mutationFn));

    expect(result.current.pending).toBe(false);

    let runPromise;
    act(() => { runPromise = result.current.run(); });
    await waitFor(() => expect(result.current.pending).toBe(true));

    await act(async () => {
      release('ok');
      await runPromise;
    });

    expect(result.current.pending).toBe(false);
    expect(result.current.error).toBe(null);
  });

  test('run resolves to the mutation result on success', async () => {
    const { result } = renderHook(() => useMutation(async (n) => n * 2));

    let value;
    await act(async () => { value = await result.current.run(21); });

    expect(value).toBe(42);
    expect(result.current.error).toBe(null);
  });

  test('error is set on rejection and run resolves to undefined', async () => {
    const failure = new Error('nope');
    const { result } = renderHook(() => useMutation(async () => { throw failure; }));

    let value = 'unset';
    await act(async () => { value = await result.current.run(); });

    expect(value).toBeUndefined();
    expect(result.current.error).toBe(failure);
    expect(result.current.pending).toBe(false);
  });

  test('error clears on retry', async () => {
    let shouldFail = true;
    const { result } = renderHook(() => useMutation(async () => {
      if (shouldFail) throw new Error('first attempt fails');
      return 'ok';
    }));

    await act(async () => { await result.current.run(); });
    expect(result.current.error).toBeInstanceOf(Error);

    shouldFail = false;
    await act(async () => { await result.current.run(); });
    expect(result.current.error).toBe(null);
  });
});
