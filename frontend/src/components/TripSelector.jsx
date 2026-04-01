import { useTrip } from '../context/TripContext';

function TripSelector() {
  const { trips, activeTripId, selectTrip, createTrip, cloneTrip, deleteTrip } = useTrip();

  async function handleNew() {
    const name = prompt('Trip name:');
    if (name) await createTrip(name);
  }

  async function handleDelete() {
    if (!activeTripId) return;
    const trip = trips.find((t) => t.id === activeTripId);
    if (confirm(`Delete trip "${trip?.name}"?`)) {
      await deleteTrip();
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <select
        value={activeTripId || ''}
        onChange={(e) => selectTrip(parseInt(e.target.value))}
        style={{ padding: '4px' }}
      >
        {trips.length === 0 && <option value="">No trips</option>}
        {trips.map((t) => (
          <option key={t.id} value={t.id}>{t.name}</option>
        ))}
      </select>
      <button onClick={handleNew}>New</button>
      <button onClick={cloneTrip} disabled={!activeTripId}>Clone</button>
      <button onClick={handleDelete} disabled={!activeTripId}>Delete</button>
    </div>
  );
}

export default TripSelector;
