import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';

// The app remembers the last-selected trip in localStorage; clear it between
// tests so one test's selection can't change which trip another test lands on.
afterEach(() => {
  localStorage.clear();
});
