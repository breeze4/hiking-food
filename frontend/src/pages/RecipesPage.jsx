import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { get } from '../api';

function RecipesPage() {
  const [recipes, setRecipes] = useState([]);
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadRecipes();
  }, []);

  async function loadRecipes() {
    try {
      setRecipes(await get('/recipes'));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  const filtered = filter === 'all'
    ? recipes
    : recipes.filter((r) => r.category === filter);

  return (
    <div>
      <h2>Recipes</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <div style={{ marginBottom: '1rem' }}>
        {['all', 'breakfast', 'dinner'].map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            style={{
              marginRight: '0.5rem',
              fontWeight: filter === cat ? 'bold' : 'normal',
              textDecoration: filter === cat ? 'underline' : 'none',
            }}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={thStyle}>Name</th>
            <th style={thStyle}>Category</th>
            <th style={thStyle}>Weight (oz)</th>
            <th style={thStyle}>Calories</th>
            <th style={thStyle}>Cal/oz</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr
              key={r.id}
              onClick={() => navigate(`/recipes/${r.id}`)}
              style={{ cursor: 'pointer' }}
            >
              <td style={tdStyle}>{r.name}</td>
              <td style={tdStyle}>{r.category}</td>
              <td style={tdStyle}>{r.total_weight}</td>
              <td style={tdStyle}>{r.total_calories}</td>
              <td style={tdStyle}>{r.cal_per_oz}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr>
              <td style={tdStyle} colSpan={5}>No recipes found.</td>
            </tr>
          )}
        </tbody>
      </table>

      <button style={{ marginTop: '1rem' }} onClick={() => navigate('/recipes/new')}>
        + New Recipe
      </button>
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

export default RecipesPage;
