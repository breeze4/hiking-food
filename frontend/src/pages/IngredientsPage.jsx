import { useState, useEffect } from 'react';
import { get, post, put, del } from '../api';

function IngredientsPage() {
  const [ingredients, setIngredients] = useState([]);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [addForm, setAddForm] = useState({ name: '', calories_per_oz: '', notes: '' });
  const [showAdd, setShowAdd] = useState(false);
  const [sortCol, setSortCol] = useState('name');
  const [sortAsc, setSortAsc] = useState(true);

  useEffect(() => {
    loadIngredients();
  }, []);

  async function loadIngredients() {
    try {
      const data = await get('/ingredients');
      setIngredients(data);
      setError(null);
    } catch (err) {
      setError(err.message);
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
    return [...ingredients].sort((a, b) => {
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
      const created = await post('/ingredients', {
        name: addForm.name,
        calories_per_oz: parseFloat(addForm.calories_per_oz),
        notes: addForm.notes || null,
      });
      setIngredients([...ingredients, created]);
      setAddForm({ name: '', calories_per_oz: '', notes: '' });
      setShowAdd(false);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  // Edit
  function startEdit(ingredient) {
    setEditingId(ingredient.id);
    setEditForm({
      name: ingredient.name,
      calories_per_oz: ingredient.calories_per_oz ?? '',
      notes: ingredient.notes ?? '',
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm({});
  }

  async function saveEdit(id) {
    try {
      const updated = await put(`/ingredients/${id}`, {
        name: editForm.name,
        calories_per_oz: parseFloat(editForm.calories_per_oz),
        notes: editForm.notes || null,
      });
      setIngredients(ingredients.map((i) => (i.id === id ? updated : i)));
      setEditingId(null);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  // Delete
  async function handleDelete(id, name) {
    if (!confirm(`Delete "${name}"?`)) return;
    try {
      await del(`/ingredients/${id}`);
      setIngredients(ingredients.filter((i) => i.id !== id));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  const sorted = getSorted();

  return (
    <div>
      <h2>Ingredients</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={thStyle} onClick={() => handleSort('name')}>
              Name{sortArrow('name')}
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
          {sorted.map((ing) =>
            editingId === ing.id ? (
              <tr key={ing.id}>
                <td style={tdStyle}>
                  <input
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    style={inputStyle}
                  />
                </td>
                <td style={tdStyle}>
                  <input
                    type="number"
                    step="any"
                    value={editForm.calories_per_oz}
                    onChange={(e) => setEditForm({ ...editForm, calories_per_oz: e.target.value })}
                    style={{ ...inputStyle, width: '80px' }}
                  />
                </td>
                <td style={tdStyle}>
                  <input
                    value={editForm.notes}
                    onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                    style={inputStyle}
                  />
                </td>
                <td style={tdStyle}>
                  <button onClick={() => saveEdit(ing.id)}>Save</button>{' '}
                  <button onClick={cancelEdit}>Cancel</button>
                </td>
              </tr>
            ) : (
              <tr key={ing.id} onDoubleClick={() => startEdit(ing)}>
                <td style={tdStyle}>{ing.name}</td>
                <td style={tdStyle}>{ing.calories_per_oz}</td>
                <td style={tdStyle}>{ing.notes}</td>
                <td style={tdStyle}>
                  <button onClick={() => startEdit(ing)}>Edit</button>{' '}
                  <button onClick={() => handleDelete(ing.id, ing.name)}>Delete</button>
                </td>
              </tr>
            )
          )}
        </tbody>
      </table>

      {showAdd ? (
        <form onSubmit={handleAdd} style={{ marginTop: '1rem' }}>
          <input
            placeholder="Name"
            value={addForm.name}
            onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
            required
            style={inputStyle}
          />{' '}
          <input
            placeholder="Cal/oz"
            type="number"
            step="any"
            value={addForm.calories_per_oz}
            onChange={(e) => setAddForm({ ...addForm, calories_per_oz: e.target.value })}
            required
            style={{ ...inputStyle, width: '80px' }}
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
        <button style={{ marginTop: '1rem' }} onClick={() => setShowAdd(true)}>
          + Add Ingredient
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

export default IngredientsPage;
