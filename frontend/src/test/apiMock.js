// Shared fetch-mock helpers for the whole-App render tests.
//
// `createApiMock(config)` builds a `fetch` implementation with sane default
// responses for every read endpoint and success responses for every mutation,
// so a test only has to describe the slices it cares about. `apiResponse` is
// the zero-config default used by `App.test.jsx`; keeping it here lets new test
// files reuse the same seed data and routing.

export function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

export const defaultTrips = [
  { id: 1, name: 'Wonderland Trail' },
  { id: 2, name: 'Goat Rocks' },
];

const DEFAULT_RECIPES_BY_ID = {
  42: {
    id: 42,
    name: 'Trail Porridge',
    category: 'breakfast',
    ingredients: [],
  },
};

// A trip-detail projection with every field the planner components read.
export function makeTripDetail(overrides = {}) {
  return {
    id: 1,
    name: 'Wonderland Trail',
    first_day_fraction: 1,
    full_days: 0,
    last_day_fraction: 0,
    drink_mixes_per_day: 2,
    oz_per_day: 22,
    cal_per_oz: 125,
    snack_model: 'structured',
    snacks_per_day: 4,
    oz_per_snack: 2,
    meals: [],
    snacks: [],
    snack_units: [],
    ...overrides,
  };
}

// A trip snack unit selection as the trip detail returns it: the resolved unit
// values plus the per-trip quantity, packing record, and tolerance flag.
export function makeTripSnackUnit(overrides = {}) {
  return {
    id: 50,
    catalog_item_id: null,
    unit_type_id: 1,
    kind: 'bag',
    name: 'Trail Mix Bag',
    quantity: 1,
    weight_oz: 2,
    calories: 300,
    cal_per_oz: 150,
    protein_g: 8,
    fat_g: 20,
    carb_g: 26,
    total_weight: 2,
    total_calories: 300,
    weight_warning: false,
    has_full_data: true,
    packed: false,
    actual_weight_oz: null,
    trip_notes: null,
    ...overrides,
  };
}

// A snack unit type (bag) as the library endpoint returns it: composition plus
// every derived value. `snackUnitTypes` accepts an array or a function, so a
// test can return a different library on the refetch after a mutation.
export function makeSnackUnitType(overrides = {}) {
  return {
    id: 1,
    name: 'Trail Mix Bag',
    notes: null,
    composition: [],
    weight_oz: 2,
    calories: 300,
    cal_per_oz: 150,
    protein_g: 8,
    fat_g: 20,
    carb_g: 26,
    weight_warning: false,
    has_full_data: true,
    ...overrides,
  };
}

export function makeSummary(overrides = {}) {
  return {
    total_days: 1,
    total_cal: 2750,
    total_weight: 22,
    combined_calories: 0,
    combined_weight: 0,
    weight_per_day: 0,
    cal_per_day: 0,
    breakfast_weight: 0,
    breakfast_calories: 0,
    breakfast_count: 0,
    dinner_weight: 0,
    dinner_calories: 0,
    dinner_count: 0,
    daytime_weight: 0,
    drink_mix_weight: 0,
    drink_mix_calories: 0,
    slot_subtotals: {},
    ...overrides,
  };
}

export function makeDailyPlan(overrides = {}) {
  return {
    days: [],
    unallocated: [],
    unallocated_summary: { count: 0, total_calories: 0, total_weight: 0 },
    warnings: [],
    macro_target: { protein_pct: 20, fat_pct: 30, carb_pct: 50 },
    ...overrides,
  };
}

export function createApiMock(config = {}) {
  const {
    trips = defaultTrips,
    tripDetails = {}, // { [id]: full detail object }
    recipes = [], // GET /recipes list
    snacks = [], // GET /snacks catalog
    snackUnitTypes = [], // GET /snack-unit-types library
    ingredients = [],
    foodIntake = [],
    recipesById = DEFAULT_RECIPES_BY_ID,
    summaries = {}, // { [id]: summary }
    dailyPlans = {}, // { [id]: plan }
    packings = {}, // { [id]: packing object }
    shoppingLists = {}, // { [id]: shopping-list object }
    // handler(path, method, options) => Response | undefined.
    // Return a jsonResponse to intercept; return undefined to fall through
    // to the default routing below. Runs for every request, reads included.
    handler,
  } = config;

  let nextTripId = Math.max(0, ...trips.map((t) => t.id)) + 1;

  return function apiMock(url, options = {}) {
    const path = new URL(url, window.location.origin).pathname;
    const method = options.method || 'GET';

    if (handler) {
      const custom = handler(path, method, options);
      if (custom !== undefined) return custom;
    }

    // --- Mutations: default to success ---
    if (method === 'DELETE' && path.match(/\/hiking-food\/api\/trips\/\d+$/)) {
      return jsonResponse(null, 204);
    }
    if (method === 'POST' && path === '/hiking-food/api/trips') {
      const body = options.body ? JSON.parse(options.body) : {};
      return jsonResponse({ id: nextTripId++, name: body.name });
    }
    const cloneMatch = path.match(/\/hiking-food\/api\/trips\/(\d+)\/clone$/);
    if (method === 'POST' && cloneMatch) {
      const source = trips.find(({ id }) => id === Number(cloneMatch[1]));
      return jsonResponse({ id: nextTripId++, name: `${source?.name ?? 'Trip'} (copy)` });
    }
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      // Daily-plan mutations return a plan body; others return an opaque OK.
      if (path.match(/\/daily-plan/)) {
        const idMatch = path.match(/\/trips\/(\d+)\//);
        const id = idMatch ? Number(idMatch[1]) : null;
        return jsonResponse(dailyPlans[id] ?? makeDailyPlan());
      }
      if (method === 'DELETE') return jsonResponse(null, 204);
      return jsonResponse({});
    }

    // --- Reads ---
    if (path === '/hiking-food/api/trips') return jsonResponse(trips);
    if (path === '/hiking-food/api/recipes') return jsonResponse(recipes);
    if (path === '/hiking-food/api/snacks') return jsonResponse(snacks);
    if (path === '/hiking-food/api/snack-unit-types') {
      return jsonResponse(typeof snackUnitTypes === 'function' ? snackUnitTypes() : snackUnitTypes);
    }
    if (path === '/hiking-food/api/ingredients') return jsonResponse(ingredients);
    if (path === '/hiking-food/api/food-intake') return jsonResponse(foodIntake);

    const recipeMatch = path.match(/\/hiking-food\/api\/recipes\/(\d+)$/);
    if (recipeMatch && recipesById[recipeMatch[1]]) {
      return jsonResponse(recipesById[recipeMatch[1]]);
    }

    const dailyPlanMatch = path.match(/\/hiking-food\/api\/trips\/(\d+)\/daily-plan$/);
    if (dailyPlanMatch) {
      return jsonResponse(dailyPlans[Number(dailyPlanMatch[1])] ?? makeDailyPlan());
    }

    const summaryMatch = path.match(/\/hiking-food\/api\/trips\/(\d+)\/summary$/);
    if (summaryMatch) {
      return jsonResponse(summaries[Number(summaryMatch[1])] ?? makeSummary());
    }

    const packingMatch = path.match(/\/hiking-food\/api\/trips\/(\d+)\/packing$/);
    if (packingMatch) {
      const id = Number(packingMatch[1]);
      if (packings[id]) return jsonResponse(packings[id]);
      const trip = trips.find(({ id: tripId }) => tripId === id);
      return jsonResponse({ trip_name: trip?.name, meals: [], snacks: [] });
    }

    if (path.match(/\/hiking-food\/api\/trips\/\d+\/shopping-list$/)) {
      const id = Number(path.match(/\/trips\/(\d+)\//)[1]);
      return jsonResponse(shoppingLists[id] ?? { items: [], essentials: [] });
    }

    const tripMatch = path.match(/\/hiking-food\/api\/trips\/(\d+)$/);
    if (tripMatch) {
      const id = Number(tripMatch[1]);
      if (tripDetails[id]) return jsonResponse(tripDetails[id]);
      const trip = trips.find(({ id: tripId }) => tripId === id);
      return trip
        ? jsonResponse(makeTripDetail({ ...trip }))
        : jsonResponse({ detail: 'Trip not found' }, 404);
    }

    throw new Error(`Unexpected API request: ${method} ${path}`);
  };
}

// Zero-config default matching the original App.test.jsx behavior.
export const apiResponse = createApiMock();
