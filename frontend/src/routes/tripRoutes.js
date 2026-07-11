const TRIP_ROUTE = /^\/trips\/(\d+)(?:\/([^/]+))?\/?$/;

export function readTripLocation(pathname) {
  const match = TRIP_ROUTE.exec(pathname);
  if (!match) return null;
  return {
    tripId: Number(match[1]),
    section: match[2] || 'planner',
  };
}

export function tripPath(tripId, section = 'planner') {
  const base = `/trips/${tripId}`;
  return section === 'planner' ? base : `${base}/${section}`;
}

export function pathAfterTripSelection(pathname, tripId) {
  const current = readTripLocation(pathname);
  return current ? tripPath(tripId, current.section) : null;
}
