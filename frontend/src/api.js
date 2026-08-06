const BASE_URL = '/hiking-food/api';

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };

  const res = await fetch(url, config);

  if (res.status === 204) return null;

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const error = new Error(body.detail || `Request failed: ${res.status}`);
    error.status = res.status;
    throw error;
  }

  return res.json();
}

export function get(path) {
  return request(path);
}

export function post(path, data) {
  return request(path, { method: 'POST', body: JSON.stringify(data) });
}

export function put(path, data) {
  return request(path, { method: 'PUT', body: JSON.stringify(data) });
}

export function patch(path, data) {
  return request(path, { method: 'PATCH', body: data ? JSON.stringify(data) : undefined });
}

export function del(path) {
  return request(path, { method: 'DELETE' });
}

// --- Snack unit type library ---
// The library is read by the planner as well as its own page, so the endpoint
// path lives here once. Responses already carry derived weight/calories/macros;
// callers never recompute composition math.

const SNACK_UNIT_TYPES = '/snack-unit-types';

export function listSnackUnitTypes() {
  return get(SNACK_UNIT_TYPES);
}

export function createSnackUnitType(data) {
  return post(SNACK_UNIT_TYPES, data);
}

export function updateSnackUnitType(id, data) {
  return put(`${SNACK_UNIT_TYPES}/${id}`, data);
}

export function deleteSnackUnitType(id) {
  return del(`${SNACK_UNIT_TYPES}/${id}`);
}
