import {
  createContext, useState, useContext, useEffect, useCallback, useRef,
} from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { get, post, del } from '../api';
import { useMutation } from '../hooks/useMutation';
import { pathAfterTripSelection, readTripLocation, tripPath } from '../routes/tripRoutes';
import { readLastTripId, writeLastTripId } from '../lib/lastTrip';

const TripContext = createContext();

export function TripProvider({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const routeTrip = readTripLocation(location.pathname);
  const [trips, setTrips] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState(routeTrip?.tripId ?? readLastTripId());
  const [tripsLoaded, setTripsLoaded] = useState(false);
  const [tripDetail, setTripDetail] = useState(null);
  const [summary, setSummary] = useState(null);
  const routeTripIsKnown = !tripsLoaded || trips.some(
    (trip) => trip.id === routeTrip?.tripId,
  );
  const activeTripId = routeTrip && routeTripIsKnown
    ? routeTrip.tripId
    : selectedTripId;
  const activeTripIdRef = useRef(activeTripId);
  // Which trip the current `summary` belongs to, so an in-place refresh can
  // keep it mounted (the summary projection carries no trip id of its own).
  const summaryTripIdRef = useRef(null);

  useEffect(() => {
    activeTripIdRef.current = activeTripId;
  }, [activeTripId]);

  // Remember the last trip the user was on so a fresh visit lands on it.
  // Only persist once trips have loaded, so an unrecognized stored id that
  // falls back to another trip doesn't overwrite the real last selection.
  useEffect(() => {
    if (tripsLoaded && activeTripId) writeLastTripId(activeTripId);
  }, [tripsLoaded, activeTripId]);

  const loadTrips = useCallback(async () => {
    try {
      const data = await get('/trips');
      setTrips(data);
      setSelectedTripId((currentId) => (
        data.some((trip) => trip.id === currentId) ? currentId : data[0]?.id ?? null
      ));
    } catch (err) {
      console.error('Failed to load trips', err);
    } finally {
      setTripsLoaded(true);
    }
  }, []);

  const loadTripDetail = useCallback(async () => {
    if (!activeTripId) {
      setTripDetail(null);
      return;
    }
    const requestedTripId = activeTripId;
    // Keep the current detail mounted while refreshing the same trip in place
    // (e.g. after a snack/meal edit); only clear it when switching to another
    // trip, so we don't flash the previous trip's data. Blanking on every
    // refresh collapsed the whole planner to a one-line placeholder, which
    // reset the page scroll to the top.
    setTripDetail((current) => (current?.id === requestedTripId ? current : null));
    try {
      const detail = await get(`/trips/${requestedTripId}`);
      if (activeTripIdRef.current === requestedTripId) setTripDetail(detail);
    } catch (err) {
      console.error('Failed to load trip detail', err);
      if (activeTripIdRef.current === requestedTripId) setTripDetail(null);
    }
  }, [activeTripId]);

  const loadSummary = useCallback(async () => {
    if (!activeTripId) { setSummary(null); summaryTripIdRef.current = null; return; }
    const requestedTripId = activeTripId;
    // Same as detail: keep the current summary (and its meters) in place during
    // a refresh, clearing only when the trip changes, so the meters don't flash
    // empty and shift the layout under the user's scroll.
    if (summaryTripIdRef.current !== requestedTripId) setSummary(null);
    try {
      const nextSummary = await get(`/trips/${requestedTripId}/summary`);
      if (activeTripIdRef.current === requestedTripId) {
        setSummary(nextSummary);
        summaryTripIdRef.current = requestedTripId;
      }
    } catch (err) {
      console.error('Failed to load summary', err);
      if (activeTripIdRef.current === requestedTripId) {
        setSummary(null);
        summaryTripIdRef.current = null;
      }
    }
  }, [activeTripId]);

  useEffect(() => { loadTrips(); }, [loadTrips]);
  useEffect(() => {
    if (routeTrip?.tripId && routeTripIsKnown) {
      setSelectedTripId(routeTrip.tripId);
    }
  }, [routeTrip?.tripId, routeTripIsKnown]);
  useEffect(() => { loadTripDetail(); }, [loadTripDetail]);
  useEffect(() => { loadSummary(); }, [loadSummary]);

  const activateTrip = useCallback((id) => {
    setSelectedTripId(id);
    const nextPath = pathAfterTripSelection(location.pathname, id);
    if (nextPath && nextPath !== location.pathname) navigate(nextPath);
  }, [location.pathname, navigate]);

  const selectTrip = (id) => activateTrip(id);

  // create/clone/delete share one mutation so the trip selector can expose
  // pending + error state; each still owns its own trip-list/navigation update.
  const tripMutation = useMutation((action) => action());

  const createTrip = (name) => tripMutation.run(async () => {
    const trip = await post('/trips', { name, first_day_fraction: 1, full_days: 0, last_day_fraction: 0 });
    setTrips((current) => [...current, { id: trip.id, name: trip.name }]);
    activateTrip(trip.id);
    return trip;
  });

  const cloneTrip = () => {
    if (!activeTripId) return Promise.resolve(undefined);
    return tripMutation.run(async () => {
      const clone = await post(`/trips/${activeTripId}/clone`);
      setTrips((current) => [...current, { id: clone.id, name: clone.name }]);
      activateTrip(clone.id);
      return clone;
    });
  };

  const deleteTrip = () => {
    if (!activeTripId) return Promise.resolve(undefined);
    return tripMutation.run(async () => {
      await del(`/trips/${activeTripId}`);
      const remaining = trips.filter((t) => t.id !== activeTripId);
      setTrips(remaining);
      const nextTripId = remaining[0]?.id ?? null;
      setSelectedTripId(nextTripId);
      const currentRoute = readTripLocation(location.pathname);
      if (currentRoute) {
        navigate(
          nextTripId ? tripPath(nextTripId, currentRoute.section) : '/',
          { replace: true },
        );
      }
      return true;
    });
  };

  const refreshTrip = useCallback(async () => {
    await loadTripDetail();
    await loadSummary();
  }, [loadTripDetail, loadSummary]);

  return (
    <TripContext.Provider value={{
      trips, tripsLoaded, activeTripId, tripDetail, summary,
      selectTrip, createTrip, cloneTrip, deleteTrip, tripMutation,
      refreshTrip, refreshTrips: loadTrips,
    }}>
      {children}
    </TripContext.Provider>
  );
}

export function useTrip() {
  return useContext(TripContext);
}
