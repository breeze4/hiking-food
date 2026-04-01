import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { TripProvider } from './context/TripContext';
import TripSelector from './components/TripSelector';
import IngredientsPage from './pages/IngredientsPage';
import SnackCatalogPage from './pages/SnackCatalogPage';
import RecipesPage from './pages/RecipesPage';
import RecipeEditPage from './pages/RecipeEditPage';
import TripPlannerPage from './pages/TripPlannerPage';
import PackingScreen from './pages/PackingScreen';

const navStyle = {
  display: 'flex',
  gap: '1rem',
  padding: '1rem 2rem',
  borderBottom: '1px solid #ccc',
  fontFamily: 'sans-serif',
  alignItems: 'center',
  flexWrap: 'wrap',
};

const linkStyle = ({ isActive }) => ({
  textDecoration: 'none',
  fontWeight: isActive ? 'bold' : 'normal',
});

function App() {
  return (
    <BrowserRouter>
      <TripProvider>
        <nav style={navStyle}>
          <NavLink to="/" style={linkStyle}>Trip Planner</NavLink>
          <NavLink to="/recipes" style={linkStyle}>Recipes</NavLink>
          <NavLink to="/snacks" style={linkStyle}>Snack Catalog</NavLink>
          <NavLink to="/ingredients" style={linkStyle}>Ingredients</NavLink>
          <div style={{ marginLeft: 'auto' }}>
            <TripSelector />
          </div>
        </nav>
        <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
          <Routes>
            <Route path="/" element={<TripPlannerPage />} />
            <Route path="/ingredients" element={<IngredientsPage />} />
            <Route path="/snacks" element={<SnackCatalogPage />} />
            <Route path="/recipes" element={<RecipesPage />} />
            <Route path="/recipes/:id" element={<RecipeEditPage />} />
            <Route path="/trips/:tripId/packing" element={<PackingScreen />} />
          </Routes>
        </div>
      </TripProvider>
    </BrowserRouter>
  );
}

export default App;
