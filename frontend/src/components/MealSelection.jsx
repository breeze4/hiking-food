import { useState, useEffect } from 'react';
import { get, post, put, del } from '../api';
import { useTrip } from '../context/TripContext';

function MealSelection() {
  const { tripDetail, refreshTrip } = useTrip();
  const [recipes, setRecipes] = useState([]);
  const [addRecipeId, setAddRecipeId] = useState('');

  useEffect(() => {
    get('/recipes').then(setRecipes).catch(() => {});
  }, []);

  if (!tripDetail) return null;

  const meals = tripDetail.meals || [];

  async function handleAdd() {
    if (!addRecipeId) return;
    await post(`/trips/${tripDetail.id}/meals`, {
      recipe_id: parseInt(addRecipeId),
      quantity: 1,
    });
    setAddRecipeId('');
    refreshTrip();
  }

  async function updateQuantity(mealId, newQty) {
    if (newQty <= 0) {
      await del(`/trips/${tripDetail.id}/meals/${mealId}`);
    } else {
      await put(`/trips/${tripDetail.id}/meals/${mealId}`, { quantity: newQty });
    }
    refreshTrip();
  }

  const breakfastRecipes = recipes.filter((r) => r.category === 'breakfast');
  const dinnerRecipes = recipes.filter((r) => r.category === 'dinner');

  return (
    <div style={{ marginBottom: '1rem' }}>
      <h3>Meals</h3>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={thStyle}>Recipe</th>
            <th style={thStyle}>Category</th>
            <th style={thStyle}>Qty</th>
            <th style={thStyle}>Wt/Unit</th>
            <th style={thStyle}>Total Wt</th>
            <th style={thStyle}>Total Cal</th>
          </tr>
        </thead>
        <tbody>
          {meals.map((m) => (
            <tr key={m.id}>
              <td style={tdStyle}>{m.recipe_name}</td>
              <td style={tdStyle}>{m.category}</td>
              <td style={tdStyle}>
                <button onClick={() => updateQuantity(m.id, m.quantity - 1)}>-</button>
                <span style={{ margin: '0 6px' }}>{m.quantity}</span>
                <button onClick={() => updateQuantity(m.id, m.quantity + 1)}>+</button>
              </td>
              <td style={tdStyle}>{m.weight_per_unit}</td>
              <td style={tdStyle}>{m.total_weight}</td>
              <td style={tdStyle}>{m.total_calories}</td>
            </tr>
          ))}
          {meals.length === 0 && (
            <tr><td style={tdStyle} colSpan={6}>No meals selected.</td></tr>
          )}
        </tbody>
      </table>

      <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem' }}>
        <select value={addRecipeId} onChange={(e) => setAddRecipeId(e.target.value)} style={{ padding: '4px' }}>
          <option value="">Add meal...</option>
          {breakfastRecipes.length > 0 && (
            <optgroup label="Breakfast">
              {breakfastRecipes.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </optgroup>
          )}
          {dinnerRecipes.length > 0 && (
            <optgroup label="Dinner">
              {dinnerRecipes.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </optgroup>
          )}
        </select>
        <button onClick={handleAdd} disabled={!addRecipeId}>Add</button>
      </div>
    </div>
  );
}

const thStyle = { borderBottom: '2px solid #ccc', padding: '6px', textAlign: 'left', fontSize: '0.85em' };
const tdStyle = { borderBottom: '1px solid #eee', padding: '6px', fontSize: '0.85em' };

export default MealSelection;
