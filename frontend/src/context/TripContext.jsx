import {
  createContext, useState, useContext, useEffect, useCallback, useRef,
} from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { get, post, del } from '../api';
import { pathAfterTripSelection, readTripLocation, tripPath } from '../routes/tripRoutes';

const TripContext = createContext();

export function TripProvider({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const routeTrip = readTripLocation(location.pathname);
  const [trips, setTrips] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState(routeTrip?.tripId ?? null);
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

  useEffect(() => {
    activeTripIdRef.current = activeTripId;
  }, [activeTripId]);

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
    setTripDetail(null);
    try {
      const detail = await get(`/trips/${requestedTripId}`);
      if (activeTripIdRef.current === requestedTripId) setTripDetail(detail);
    } catch (err) {
      console.error('Failed to load trip detail', err);
      if (activeTripIdRef.current === requestedTripId) setTripDetail(null);
    }
  }, [activeTripId]);

  const loadSummary = useCallback(async () => {
    if (!activeTripId) { setSummary(null); return; }
    const requestedTripId = activeTripId;
    setSummary(null);
    try {
      const nextSummary = await get(`/trips/${requestedTripId}/summary`);
      if (activeTripIdRef.current === requestedTripId) setSummary(nextSummary);
    } catch (err) {
      console.error('Failed to load summary', err);
      if (activeTripIdRef.current === requestedTripId) setSummary(null);
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

  const createTrip = async (name) => {
    const trip = await post('/trips', { name, first_day_fraction: 1, full_days: 0, last_day_fraction: 0 });
    setTrips((current) => [...current, { id: trip.id, name: trip.name }]);
    activateTrip(trip.id);
    return trip;
  };

  const cloneTrip = async () => {
    if (!activeTripId) return;
    const clone = await post(`/trips/${activeTripId}/clone`);
    setTrips((current) => [...current, { id: clone.id, name: clone.name }]);
    activateTrip(clone.id);
    return clone;
  };

  const deleteTrip = async () => {
    if (!activeTripId) return;
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
  };

  const refreshTrip = useCallback(async () => {
    await loadTripDetail();
    await loadSummary();
  }, [loadTripDetail, loadSummary]);

  return (
    <TripContext.Provider value={{
      trips, tripsLoaded, activeTripId, tripDetail, summary,
      selectTrip, createTrip, cloneTrip, deleteTrip,
      refreshTrip, refreshTrips: loadTrips,
    }}>
      {children}
    </TripContext.Provider>
  );
}

export function useTrip() {
  return useContext(TripContext);
}
