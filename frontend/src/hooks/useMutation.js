import { useState } from 'react';

// Standardizes mutation STATE (pending/error) around an async mutation.
// It does not dictate the refresh mechanism — the caller's function still owns
// whatever refetch/response-body update it needs. `run` resolves to the
// mutation result on success and to `undefined` on failure (the rejection is
// captured in `error`, never rethrown), so call sites stay try/catch-free.
export function useMutation(mutationFn) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  // `run` is recreated each render and closes over the current mutationFn, so
  // it always calls the latest closure. Nothing depends on its identity.
  const run = async (...args) => {
    setPending(true);
    setError(null);
    try {
      return await mutationFn(...args);
    } catch (err) {
      setError(err);
      return undefined;
    } finally {
      setPending(false);
    }
  };

  return { run, pending, error };
}
