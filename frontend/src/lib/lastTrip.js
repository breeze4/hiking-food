// Remembers the trip the user last had open so returning to the app lands on
// it instead of the first trip in the list. Stored in localStorage; all access
// is guarded because storage can throw (private mode, disabled cookies).

const STORAGE_KEY = 'hiking-food:lastTripId';

export function readLastTripId() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    const id = Number(raw);
    return Number.isSafeInteger(id) && id > 0 ? id : null;
  } catch {
    return null;
  }
}

export function writeLastTripId(id) {
  try {
    if (id == null) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, String(id));
  } catch {
    // Ignore storage failures; remembering the trip is best-effort.
  }
}
