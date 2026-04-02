import { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { get, post, del } from '../api';

const TripContext = createContext();

export function TripProvider({ children }) {
  const [trips, setTrips] = useState([]);
  const [activeTripId, setActiveTripId] = useState(null);
  const [tripDetail, setTripDetail] = useState(null);
  const [summary, setSummary] = useState(null);

  const loadTrips = useCallback(async () => {
    try {
      const data = await get('/trips');
      setTrips(data);
      if (data.length > 0 && !activeTripId) {
        setActiveTripId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load trips', err);
    }
  }, [activeTripId]);

  const loadTripDetail = useCallback(async () => {
    if (!activeTripId) {
      setTripDetail(null);
      return;
    }
    try {
      setTripDetail(await get(`/trips/${activeTripId}`));
    } catch (err) {
      console.error('Failed to load trip detail', err);
    }
  }, [activeTripId]);

  const loadSummary = useCallback(async () => {
    if (!activeTripId) { setSummary(null); return; }
    try {
      setSummary(await get(`/trips/${activeTripId}/summary`));
    } catch (err) {
      console.error('Failed to load summary', err);
    }
  }, [activeTripId]);

  useEffect(() => { loadTrips(); }, []);
  useEffect(() => { loadTripDetail(); }, [activeTripId]);
  useEffect(() => { loadSummary(); }, [activeTripId]);

  const selectTrip = (id) => setActiveTripId(id);

  const createTrip = async (name) => {
    const trip = await post('/trips', { name, first_day_fraction: 1, full_days: 0, last_day_fraction: 0 });
    setTrips([...trips, { id: trip.id, name: trip.name }]);
    setActiveTripId(trip.id);
    return trip;
  };

  const cloneTrip = async () => {
    if (!activeTripId) return;
    const clone = await post(`/trips/${activeTripId}/clone`);
    setTrips([...trips, { id: clone.id, name: clone.name }]);
    setActiveTripId(clone.id);
    return clone;
  };

  const deleteTrip = async () => {
    if (!activeTripId) return;
    await del(`/trips/${activeTripId}`);
    const remaining = trips.filter((t) => t.id !== activeTripId);
    setTrips(remaining);
    setActiveTripId(remaining.length > 0 ? remaining[0].id : null);
  };

  const refreshTrip = useCallback(async () => {
    await loadTripDetail();
    await loadSummary();
  }, [loadTripDetail, loadSummary]);

  return (
    <TripContext.Provider value={{
      trips, activeTripId, tripDetail, summary,
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
