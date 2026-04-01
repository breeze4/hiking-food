import { useState, useEffect } from 'react';
import { get, post, put, del } from '../api';

function SnackCatalogPage() {
  const [snacks, setSnacks] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({
    ingredient_id: '',
    weight_per_serving: '',
    calories_per_serving: '',
    notes: '',
  });
  const [sortCol, setSortCol] = useState('ingredient_name');
  const [sortAsc, setSortAsc] = useState(true);

  useEffect(() => {
    loadSnacks();
    loadIngredients();
  }, []);

  async function loadSnacks() {
    try {
      setSnacks(await get('/snacks'));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadIngredients() {
    try {
      setIngredients(await get('/ingredients'));
    } catch (err) {
      // non-critical
    }
  }

  // Sorting
  function handleSort(col) {
    if (sortCol === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(col);
      setSortAsc(true);
    }
  }

  function getSorted() {
    return [...snacks].sort((a, b) => {
      let aVal = a[sortCol];
      let bVal = b[sortCol];
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortAsc ? aVal - bVal : bVal - aVal;
      }
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortAsc ? cmp : -cmp;
    });
  }

  function sortArrow(col) {
    if (sortCol !== col) return '';
    return sortAsc ? ' ▲' : ' ▼';
  }

  // Add
  async function handleAdd(e) {
    e.preventDefault();
    try {
      const created = await post('/snacks', {
        ingredient_id: parseInt(addForm.ingredient_id),
        weight_per_serving: parseFloat(addForm.weight_per_serving),
        calories_per_serving: parseFloat(addForm.calories_per_serving),
        notes: addForm.notes || null,
      });
      setSnacks([...snacks, created]);
      setAddForm({ ingredient_id: '', weight_per_serving: '', calories_per_serving: '', notes: '' });
      setShowAdd(false);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  // Edit
  function startEdit(snack) {
    setEditingId(snack.id);
    setEditForm({
      weight_per_serving: snack.weight_per_serving ?? '',
      calories_per_serving: snack.calories_per_serving ?? '',
      notes: snack.notes ?? '',
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm({});
  }

  async function saveEdit(id) {
    try {
      const updated = await put(`/snacks/${id}`, {
        weight_per_serving: parseFloat(editForm.weight_per_serving),
        calories_per_serving: parseFloat(editForm.calories_per_serving),
        notes: editForm.notes || null,
      });
      setSnacks(snacks.map((s) => (s.id === id ? updated : s)));
      setEditingId(null);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  // Delete
  async function handleDelete(id, name) {
    if (!confirm(`Delete snack "${name}"?`)) return;
    try {
      await del(`/snacks/${id}`);
      setSnacks(snacks.filter((s) => s.id !== id));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  const sorted = getSorted();

  return (
    <div>
      <h2>Snack Catalog</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={thStyle} onClick={() => handleSort('ingredient_name')}>
              Ingredient{sortArrow('ingredient_name')}
            </th>
            <th style={thStyle} onClick={() => handleSort('weight_per_serving')}>
              Wt/Serving (oz){sortArrow('weight_per_serving')}
            </th>
            <th style={thStyle} onClick={() => handleSort('calories_per_serving')}>
              Cal/Serving{sortArrow('calories_per_serving')}
            </th>
            <th style={thStyle} onClick={() => handleSort('calories_per_oz')}>
              Cal/oz{sortArrow('calories_per_oz')}
            </th>
            <th style={thStyle} onClick={() => handleSort('notes')}>
              Notes{sortArrow('notes')}
            </th>
            <th style={thStyle}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) =>
            editingId === s.id ? (
              <tr key={s.id}>
                <td style={tdStyle}>{s.ingredient_name}</td>
                <td style={tdStyle}>
                  <input
                    type="number"
                    step="any"
                    value={editForm.weight_per_serving}
                    onChange={(e) => setEditForm({ ...editForm, weight_per_serving: e.target.value })}
                    style={{ ...inputStyle, width: '80px' }}
                  />
                </td>
                <td style={tdStyle}>
                  <input
                    type="number"
                    step="any"
                    value={editForm.calories_per_serving}
                    onChange={(e) => setEditForm({ ...editForm, calories_per_serving: e.target.value })}
                    style={{ ...inputStyle, width: '80px' }}
                  />
                </td>
                <td style={tdStyle}>—</td>
                <td style={tdStyle}>
                  <input
                    value={editForm.notes}
                    onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                    style={inputStyle}
                  />
                </td>
                <td style={tdStyle}>
                  <button onClick={() => saveEdit(s.id)}>Save</button>{' '}
                  <button onClick={cancelEdit}>Cancel</button>
                </td>
              </tr>
            ) : (
              <tr key={s.id} onDoubleClick={() => startEdit(s)}>
                <td style={tdStyle}>{s.ingredient_name}</td>
                <td style={tdStyle}>{s.weight_per_serving}</td>
                <td style={tdStyle}>{s.calories_per_serving}</td>
                <td style={tdStyle}>{s.calories_per_oz}</td>
                <td style={tdStyle}>{s.notes}</td>
                <td style={tdStyle}>
                  <button onClick={() => startEdit(s)}>Edit</button>{' '}
                  <button onClick={() => handleDelete(s.id, s.ingredient_name)}>Delete</button>
                </td>
              </tr>
            )
          )}
        </tbody>
      </table>

      {showAdd ? (
        <form onSubmit={handleAdd} style={{ marginTop: '1rem' }}>
          <select
            value={addForm.ingredient_id}
            onChange={(e) => setAddForm({ ...addForm, ingredient_id: e.target.value })}
            required
            style={inputStyle}
          >
            <option value="">Select ingredient...</option>
            {ingredients.map((ing) => (
              <option key={ing.id} value={ing.id}>
                {ing.name}
              </option>
            ))}
          </select>{' '}
          <input
            placeholder="Wt/serving (oz)"
            type="number"
            step="any"
            value={addForm.weight_per_serving}
            onChange={(e) => setAddForm({ ...addForm, weight_per_serving: e.target.value })}
            required
            style={{ ...inputStyle, width: '100px' }}
          />{' '}
          <input
            placeholder="Cal/serving"
            type="number"
            step="any"
            value={addForm.calories_per_serving}
            onChange={(e) => setAddForm({ ...addForm, calories_per_serving: e.target.value })}
            required
            style={{ ...inputStyle, width: '100px' }}
          />{' '}
          <input
            placeholder="Notes"
            value={addForm.notes}
            onChange={(e) => setAddForm({ ...addForm, notes: e.target.value })}
            style={inputStyle}
          />{' '}
          <button type="submit">Add</button>{' '}
          <button type="button" onClick={() => setShowAdd(false)}>Cancel</button>
        </form>
      ) : (
        <button style={{ marginTop: '1rem' }} onClick={() => { setShowAdd(true); loadIngredients(); }}>
          + Add Snack Item
        </button>
      )}
    </div>
  );
}

const thStyle = {
  borderBottom: '2px solid #ccc',
  padding: '8px',
  textAlign: 'left',
  cursor: 'pointer',
  userSelect: 'none',
};

const tdStyle = {
  borderBottom: '1px solid #eee',
  padding: '8px',
};

const inputStyle = {
  padding: '4px',
  width: '150px',
};

export default SnackCatalogPage;
