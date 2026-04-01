import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { get, post, put, del } from '../api';

function RecipeEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = id === 'new';

  const [form, setForm] = useState({
    name: '',
    category: 'breakfast',
    at_home_prep: '',
    field_prep: '',
    notes: '',
  });
  const [recipeIngredients, setRecipeIngredients] = useState([]);
  const [allIngredients, setAllIngredients] = useState([]);
  const [addIngId, setAddIngId] = useState('');
  const [addAmount, setAddAmount] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    loadIngredients();
    if (!isNew) loadRecipe();
  }, [id]);

  async function loadRecipe() {
    try {
      const data = await get(`/recipes/${id}`);
      setForm({
        name: data.name,
        category: data.category || 'breakfast',
        at_home_prep: data.at_home_prep || '',
        field_prep: data.field_prep || '',
        notes: data.notes || '',
      });
      setRecipeIngredients(data.ingredients || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadIngredients() {
    try {
      setAllIngredients(await get('/ingredients'));
    } catch (err) {
      // non-critical
    }
  }

  // Build a lookup for cal/oz
  const ingLookup = useMemo(() => {
    const map = {};
    allIngredients.forEach((i) => { map[i.id] = i; });
    return map;
  }, [allIngredients]);

  // Compute totals client-side
  const totals = useMemo(() => {
    let weight = 0;
    let cals = 0;
    recipeIngredients.forEach((ri) => {
      weight += ri.amount_oz || 0;
      const calPerOz = ingLookup[ri.ingredient_id]?.calories_per_oz ?? 0;
      cals += (ri.amount_oz || 0) * calPerOz;
    });
    return {
      total_weight: Math.round(weight * 100) / 100,
      total_calories: Math.round(cals * 10) / 10,
      cal_per_oz: weight > 0 ? Math.round((cals / weight) * 10) / 10 : null,
    };
  }, [recipeIngredients, ingLookup]);

  function addIngredient() {
    if (!addIngId || !addAmount) return;
    const ing = ingLookup[parseInt(addIngId)];
    if (!ing) return;
    setRecipeIngredients([
      ...recipeIngredients,
      {
        id: null,
        ingredient_id: ing.id,
        ingredient_name: ing.name,
        amount_oz: parseFloat(addAmount),
        calories: parseFloat(addAmount) * (ing.calories_per_oz || 0),
      },
    ]);
    setAddIngId('');
    setAddAmount('');
  }

  function removeIngredient(index) {
    setRecipeIngredients(recipeIngredients.filter((_, i) => i !== index));
  }

  function updateIngAmount(index, newAmount) {
    setRecipeIngredients(recipeIngredients.map((ri, i) => {
      if (i !== index) return ri;
      const amt = parseFloat(newAmount) || 0;
      const calPerOz = ingLookup[ri.ingredient_id]?.calories_per_oz ?? 0;
      return { ...ri, amount_oz: amt, calories: Math.round(amt * calPerOz * 10) / 10 };
    }));
  }

  async function handleSave() {
    const payload = {
      name: form.name,
      category: form.category,
      at_home_prep: form.at_home_prep || null,
      field_prep: form.field_prep || null,
      notes: form.notes || null,
      ingredients: recipeIngredients.map((ri) => ({
        ingredient_id: ri.ingredient_id,
        amount_oz: ri.amount_oz,
      })),
    };
    try {
      if (isNew) {
        await post('/recipes', payload);
      } else {
        await put(`/recipes/${id}`, payload);
      }
      navigate('/recipes');
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete recipe "${form.name}"?`)) return;
    try {
      await del(`/recipes/${id}`);
      navigate('/recipes');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <h2>{isNew ? 'New Recipe' : `Edit: ${form.name}`}</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: '500px' }}>
        <label>
          Name
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            style={{ display: 'block', width: '100%', padding: '4px' }}
          />
        </label>
        <label>
          Category
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            style={{ display: 'block', padding: '4px' }}
          >
            <option value="breakfast">Breakfast</option>
            <option value="dinner">Dinner</option>
          </select>
        </label>
        <label>
          At-Home Prep
          <textarea
            value={form.at_home_prep}
            onChange={(e) => setForm({ ...form, at_home_prep: e.target.value })}
            rows={3}
            style={{ display: 'block', width: '100%' }}
          />
        </label>
        <label>
          Field Prep
          <textarea
            value={form.field_prep}
            onChange={(e) => setForm({ ...form, field_prep: e.target.value })}
            rows={3}
            style={{ display: 'block', width: '100%' }}
          />
        </label>
        <label>
          Notes
          <textarea
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            rows={2}
            style={{ display: 'block', width: '100%' }}
          />
        </label>
      </div>

      <h3 style={{ marginTop: '1.5rem' }}>Ingredients</h3>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={thStyle}>Ingredient</th>
            <th style={thStyle}>Amount (oz)</th>
            <th style={thStyle}>Calories</th>
            <th style={thStyle}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {recipeIngredients.map((ri, index) => (
            <tr key={index}>
              <td style={tdStyle}>{ri.ingredient_name}</td>
              <td style={tdStyle}>
                <input
                  type="number"
                  step="any"
                  value={ri.amount_oz}
                  onChange={(e) => updateIngAmount(index, e.target.value)}
                  style={{ width: '80px', padding: '4px' }}
                />
              </td>
              <td style={tdStyle}>{Math.round((ri.amount_oz || 0) * (ingLookup[ri.ingredient_id]?.calories_per_oz || 0) * 10) / 10}</td>
              <td style={tdStyle}>
                <button onClick={() => removeIngredient(index)}>Remove</button>
              </td>
            </tr>
          ))}
          <tr>
            <td style={tdStyle}>
              <select
                value={addIngId}
                onChange={(e) => setAddIngId(e.target.value)}
                style={{ padding: '4px' }}
              >
                <option value="">Add ingredient...</option>
                {allIngredients.map((ing) => (
                  <option key={ing.id} value={ing.id}>{ing.name}</option>
                ))}
              </select>
            </td>
            <td style={tdStyle}>
              <input
                type="number"
                step="any"
                placeholder="oz"
                value={addAmount}
                onChange={(e) => setAddAmount(e.target.value)}
                style={{ width: '80px', padding: '4px' }}
              />
            </td>
            <td style={tdStyle}></td>
            <td style={tdStyle}>
              <button onClick={addIngredient} disabled={!addIngId || !addAmount}>Add</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div style={{ marginTop: '0.5rem', fontWeight: 'bold' }}>
        Total: {totals.total_weight} oz | {totals.total_calories} cal | {totals.cal_per_oz ?? '—'} cal/oz
      </div>

      <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.5rem' }}>
        <button onClick={handleSave}>Save</button>
        <button onClick={() => navigate('/recipes')}>Cancel</button>
        {!isNew && <button onClick={handleDelete} style={{ color: 'red' }}>Delete</button>}
      </div>
    </div>
  );
}

const thStyle = {
  borderBottom: '2px solid #ccc',
  padding: '8px',
  textAlign: 'left',
};

const tdStyle = {
  borderBottom: '1px solid #eee',
  padding: '8px',
};

export default RecipeEditPage;
