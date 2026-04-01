import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { get, put } from '../api';

function PackingScreen() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const [packing, setPacking] = useState(null);
  const [shoppingList, setShoppingList] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, [tripId]);

  async function loadData() {
    try {
      const [packingData, shopData] = await Promise.all([
        get(`/trips/${tripId}/packing`),
        get(`/trips/${tripId}/shopping-list`),
      ]);
      setPacking(packingData);
      setShoppingList(shopData);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleMealPacked(mealId, packed) {
    await put(`/trips/${tripId}/meals/${mealId}`, { packed });
    loadData();
  }

  async function setMealWeight(mealId, weight) {
    await put(`/trips/${tripId}/meals/${mealId}`, {
      actual_weight_oz: weight ? parseFloat(weight) : null,
    });
    loadData();
  }

  async function toggleSnackPacked(snackId, packed) {
    await put(`/trips/${tripId}/snacks/${snackId}`, { packed });
    loadData();
  }

  async function setSnackWeight(snackId, weight) {
    await put(`/trips/${tripId}/snacks/${snackId}`, {
      actual_weight_oz: weight ? parseFloat(weight) : null,
    });
    loadData();
  }

  if (error) return <p style={{ color: 'red' }}>{error}</p>;
  if (!packing) return <p>Loading...</p>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Packing: {packing.trip_name}</h2>
        <button onClick={() => navigate('/')}>Back to Planner</button>
      </div>

      {/* Recipe Assembly */}
      <h3>Recipe Assembly</h3>
      {packing.meals.length === 0 && <p>No meals selected for this trip.</p>}
      {packing.meals.map((meal) => (
        <div key={meal.id} style={{
          border: '1px solid #ccc',
          padding: '1rem',
          marginBottom: '1rem',
          opacity: meal.packed ? 0.6 : 1,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <input
              type="checkbox"
              checked={meal.packed}
              onChange={(e) => toggleMealPacked(meal.id, e.target.checked)}
            />
            <strong>{meal.recipe_name}</strong>
            <span>({meal.category})</span>
            {meal.quantity > 1 && <span>x{meal.quantity}</span>}
            <label style={{ marginLeft: 'auto' }}>
              Actual weight:
              <input
                type="number"
                step="any"
                defaultValue={meal.actual_weight_oz || ''}
                onBlur={(e) => setMealWeight(meal.id, e.target.value)}
                style={{ width: '80px', marginLeft: '4px', padding: '2px' }}
              />
              oz
            </label>
          </div>
          <table style={{ borderCollapse: 'collapse', width: '100%', marginTop: '0.5rem' }}>
            <thead>
              <tr>
                <th style={thSmall}>Ingredient</th>
                <th style={thSmall}>Amount (oz)</th>
              </tr>
            </thead>
            <tbody>
              {meal.ingredients.map((ing, i) => (
                <tr key={i}>
                  <td style={tdSmall}>{ing.name}</td>
                  <td style={tdSmall}>{ing.amount_oz}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {meal.at_home_prep && (
            <details style={{ marginTop: '0.5rem' }}>
              <summary>At-home prep</summary>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85em' }}>{meal.at_home_prep}</pre>
            </details>
          )}
        </div>
      ))}

      {/* Snack Packing */}
      <h3>Snack Packing</h3>
      {packing.snacks.length === 0 && <p>No snacks selected for this trip.</p>}
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={thSmall}>Packed</th>
            <th style={thSmall}>Item</th>
            <th style={thSmall}>Servings</th>
            <th style={thSmall}>Target (oz)</th>
            <th style={thSmall}>Target Cal</th>
            <th style={thSmall}>Actual (oz)</th>
          </tr>
        </thead>
        <tbody>
          {packing.snacks.map((s) => (
            <tr key={s.id} style={{ opacity: s.packed ? 0.6 : 1 }}>
              <td style={tdSmall}>
                <input
                  type="checkbox"
                  checked={s.packed}
                  onChange={(e) => toggleSnackPacked(s.id, e.target.checked)}
                />
              </td>
              <td style={tdSmall}>{s.ingredient_name}</td>
              <td style={tdSmall}>{s.servings}</td>
              <td style={tdSmall}>{s.target_weight}</td>
              <td style={tdSmall}>{s.target_calories}</td>
              <td style={tdSmall}>
                <input
                  type="number"
                  step="any"
                  defaultValue={s.actual_weight_oz || ''}
                  onBlur={(e) => setSnackWeight(s.id, e.target.value)}
                  style={{ width: '70px', padding: '2px' }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Shopping List */}
      <h3>Shopping List</h3>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={thSmall}>Ingredient</th>
            <th style={thSmall}>Total (oz)</th>
          </tr>
        </thead>
        <tbody>
          {shoppingList.map((item) => (
            <tr key={item.ingredient_id}>
              <td style={tdSmall}>{item.ingredient_name}</td>
              <td style={tdSmall}>{item.total_oz}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const thSmall = { borderBottom: '2px solid #ccc', padding: '6px', textAlign: 'left', fontSize: '0.85em' };
const tdSmall = { borderBottom: '1px solid #eee', padding: '6px', fontSize: '0.85em' };

export default PackingScreen;
