import { useState, useEffect } from 'react';
import { get, post, put, del } from '../api';
import { useTrip } from '../context/TripContext';

function SnackSelection() {
  const { tripDetail, refreshTrip } = useTrip();
  const [catalog, setCatalog] = useState([]);
  const [addItemId, setAddItemId] = useState('');

  useEffect(() => {
    get('/snacks').then(setCatalog).catch(() => {});
  }, []);

  if (!tripDetail) return null;

  const snacks = tripDetail.snacks || [];

  async function handleAdd() {
    if (!addItemId) return;
    await post(`/trips/${tripDetail.id}/snacks`, {
      catalog_item_id: parseInt(addItemId),
      servings: 1,
    });
    setAddItemId('');
    refreshTrip();
  }

  async function updateServings(snackId, newServings) {
    if (newServings <= 0) {
      await del(`/trips/${tripDetail.id}/snacks/${snackId}`);
    } else {
      await put(`/trips/${tripDetail.id}/snacks/${snackId}`, { servings: newServings });
    }
    refreshTrip();
  }

  async function togglePacked(snackId, packed) {
    await put(`/trips/${tripDetail.id}/snacks/${snackId}`, { packed });
    refreshTrip();
  }

  async function updateNotes(snackId, trip_notes) {
    await put(`/trips/${tripDetail.id}/snacks/${snackId}`, { trip_notes: trip_notes || null });
    refreshTrip();
  }

  // Filter catalog to items not already in trip
  const usedCatalogIds = new Set(snacks.map((s) => s.catalog_item_id));
  const available = catalog.filter((c) => !usedCatalogIds.has(c.id));

  return (
    <div style={{ marginBottom: '1rem' }}>
      <h3>Snacks</h3>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={thStyle}>Name</th>
            <th style={thStyle}>Servings</th>
            <th style={thStyle}>Wt/Srv</th>
            <th style={thStyle}>Total Wt</th>
            <th style={thStyle}>Cal/Srv</th>
            <th style={thStyle}>Total Cal</th>
            <th style={thStyle}>Cal/oz</th>
            <th style={thStyle}>Packed</th>
            <th style={thStyle}>Notes</th>
          </tr>
        </thead>
        <tbody>
          {snacks.map((s) => (
            <tr key={s.id}>
              <td style={tdStyle}>{s.ingredient_name}</td>
              <td style={tdStyle}>
                <button onClick={() => updateServings(s.id, s.servings - 0.5)}>-</button>
                <input
                  type="number"
                  step="0.5"
                  value={s.servings}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    if (!isNaN(val)) updateServings(s.id, val);
                  }}
                  style={{ width: '50px', textAlign: 'center', margin: '0 4px' }}
                />
                <button onClick={() => updateServings(s.id, s.servings + 0.5)}>+</button>
              </td>
              <td style={tdStyle}>{s.weight_per_serving}</td>
              <td style={tdStyle}>{s.total_weight}</td>
              <td style={tdStyle}>{s.calories_per_serving}</td>
              <td style={tdStyle}>{s.total_calories}</td>
              <td style={tdStyle}>{s.calories_per_oz}</td>
              <td style={tdStyle}>
                <input
                  type="checkbox"
                  checked={s.packed}
                  onChange={(e) => togglePacked(s.id, e.target.checked)}
                />
              </td>
              <td style={tdStyle}>
                <input
                  defaultValue={s.trip_notes || ''}
                  onBlur={(e) => updateNotes(s.id, e.target.value)}
                  style={{ width: '100px', padding: '2px' }}
                  placeholder="notes..."
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem' }}>
        <select value={addItemId} onChange={(e) => setAddItemId(e.target.value)} style={{ padding: '4px' }}>
          <option value="">Add snack...</option>
          {available.map((c) => (
            <option key={c.id} value={c.id}>{c.ingredient_name}</option>
          ))}
        </select>
        <button onClick={handleAdd} disabled={!addItemId}>Add</button>
      </div>
    </div>
  );
}

const thStyle = { borderBottom: '2px solid #ccc', padding: '6px', textAlign: 'left', fontSize: '0.85em' };
const tdStyle = { borderBottom: '1px solid #eee', padding: '6px', fontSize: '0.85em' };

export default SnackSelection;
