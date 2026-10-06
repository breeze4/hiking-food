import '@testing-library/jest-dom/vitest';
import { configure } from '@testing-library/react';
import { afterEach } from 'vitest';

// The first render of <App /> takes over one second on a cloud pool worker,
// past the 1000 ms default for findBy* queries. A longer wait keeps those
// queries from failing on a slow worker; a query that never matches still fails.
configure({ asyncUtilTimeout: 5000 });

// The app remembers the last-selected trip in localStorage; clear it between
// tests so one test's selection can't change which trip another test lands on.
afterEach(() => {
  localStorage.clear();
});
