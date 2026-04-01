import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { get } from '../api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

function RecipesPage() {
  const [recipes, setRecipes] = useState([]);
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    get('/recipes').then(setRecipes).catch((err) => setError(err.message));
  }, []);

  const filtered = filter === 'all'
    ? recipes
    : recipes.filter((r) => r.category === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Recipes</h2>
        <Button onClick={() => navigate('/recipes/new')}>+ New Recipe</Button>
      </div>

      {error && <p className="text-destructive text-sm">{error}</p>}

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="breakfast">Breakfast</TabsTrigger>
          <TabsTrigger value="dinner">Dinner</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Category</TableHead>
              <TableHead className="text-right">Weight (oz)</TableHead>
              <TableHead className="text-right">Calories</TableHead>
              <TableHead className="text-right">Cal/oz</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((r) => (
              <TableRow
                key={r.id}
                onClick={() => navigate(`/recipes/${r.id}`)}
                className="cursor-pointer"
              >
                <TableCell className="font-medium">{r.name}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">{r.category}</Badge>
                </TableCell>
                <TableCell className="text-right">{r.total_weight}</TableCell>
                <TableCell className="text-right">{r.total_calories}</TableCell>
                <TableCell className="text-right">{r.cal_per_oz}</TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  No recipes found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export default RecipesPage;
