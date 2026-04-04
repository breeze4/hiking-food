import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { get, post, put, del } from '../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { StarRating } from '@/components/ui/star-rating';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

function RecipeEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = id === 'new';

  const [form, setForm] = useState({
    name: '', category: 'breakfast', at_home_prep: '', field_prep: '', notes: '', rating: null,
  });
  const [recipeIngredients, setRecipeIngredients] = useState([]);
  const [allIngredients, setAllIngredients] = useState([]);
  const [addIngId, setAddIngId] = useState('');
  const [addAmount, setAddAmount] = useState('');
  const [error, setError] = useState(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    get('/ingredients').then(setAllIngredients).catch(() => {});
    if (!isNew) {
      get(`/recipes/${id}`).then((data) => {
        setForm({
          name: data.name,
          category: data.category || 'breakfast',
          at_home_prep: data.at_home_prep || '',
          field_prep: data.field_prep || '',
          notes: data.notes || '',
          rating: data.rating ?? null,
        });
        setRecipeIngredients(data.ingredients || []);
      }).catch((err) => setError(err.message));
    }
  }, [id]);

  const ingLookup = useMemo(() => {
    const map = {};
    allIngredients.forEach((i) => { map[i.id] = i; });
    return map;
  }, [allIngredients]);

  const totals = useMemo(() => {
    let weight = 0, cals = 0, protein = 0, fat = 0, carb = 0;
    recipeIngredients.forEach((ri) => {
      const amt = ri.amount_oz || 0;
      const ing = ingLookup[ri.ingredient_id];
      weight += amt;
      cals += amt * (ing?.calories_per_oz ?? 0);
      protein += amt * (ing?.protein_per_oz ?? 0);
      fat += amt * (ing?.fat_per_oz ?? 0);
      carb += amt * (ing?.carb_per_oz ?? 0);
    });
    return {
      total_weight: Math.round(weight * 100) / 100,
      total_calories: Math.round(cals * 10) / 10,
      cal_per_oz: weight > 0 ? Math.round((cals / weight) * 10) / 10 : null,
      protein_g: Math.round(protein * 10) / 10,
      fat_g: Math.round(fat * 10) / 10,
      carb_g: Math.round(carb * 10) / 10,
    };
  }, [recipeIngredients, ingLookup]);

  function addIngredient() {
    if (!addIngId || !addAmount) return;
    const ing = ingLookup[parseInt(addIngId)];
    if (!ing) return;
    setRecipeIngredients([...recipeIngredients, {
      id: null, ingredient_id: ing.id, ingredient_name: ing.name,
      amount_oz: parseFloat(addAmount),
      calories: parseFloat(addAmount) * (ing.calories_per_oz || 0),
    }]);
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
      name: form.name, category: form.category,
      at_home_prep: form.at_home_prep || null,
      field_prep: form.field_prep || null,
      notes: form.notes || null,
      rating: form.rating,
      ingredients: recipeIngredients.map((ri) => ({
        ingredient_id: ri.ingredient_id, amount_oz: ri.amount_oz,
      })),
    };
    try {
      if (isNew) await post('/recipes', payload);
      else await put(`/recipes/${id}`, payload);
      navigate('/recipes');
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete() {
    try {
      await del(`/recipes/${id}`);
      navigate('/recipes');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <h2 className="text-2xl font-semibold tracking-tight">
        {isNew ? 'New Recipe' : `Edit: ${form.name}`}
      </h2>
      {error && <p className="text-destructive text-sm">{error}</p>}

      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <select id="category" value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm">
                <option value="breakfast">Breakfast</option>
                <option value="dinner">Dinner</option>
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Rating</Label>
            <div>
              <StarRating value={form.rating} onChange={(r) => setForm({ ...form, rating: r })} size="md" />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="at-home-prep">At-Home Prep</Label>
            <textarea id="at-home-prep" value={form.at_home_prep}
              onChange={(e) => setForm({ ...form, at_home_prep: e.target.value })}
              rows={3}
              className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="field-prep">Field Prep</Label>
            <textarea id="field-prep" value={form.field_prep}
              onChange={(e) => setForm({ ...form, field_prep: e.target.value })}
              rows={3}
              className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <textarea id="notes" value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={2}
              className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
          </div>
        </CardContent>
      </Card>

      <div>
        <h3 className="text-lg font-semibold mb-3">Ingredients</h3>
        <div className="rounded-md border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ingredient</TableHead>
                <TableHead className="w-28">Amount (oz)</TableHead>
                <TableHead className="text-right w-24">Calories</TableHead>
                <TableHead className="w-20"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recipeIngredients.map((ri, index) => (
                <TableRow key={index} className="even:bg-muted/50">
                  <TableCell>{ri.ingredient_name}</TableCell>
                  <TableCell>
                    <Input type="number" step="any" value={ri.amount_oz}
                      onChange={(e) => updateIngAmount(index, e.target.value)}
                      className="w-20 h-8" />
                  </TableCell>
                  <TableCell className="text-right">
                    {Math.round((ri.amount_oz || 0) * (ingLookup[ri.ingredient_id]?.calories_per_oz || 0) * 10) / 10}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive"
                      onClick={() => removeIngredient(index)}>Remove</Button>
                  </TableCell>
                </TableRow>
              ))}
              <TableRow>
                <TableCell>
                  <select value={addIngId} onChange={(e) => setAddIngId(e.target.value)}
                    className="h-8 rounded-md border border-input bg-background px-2 text-sm w-full">
                    <option value="">Add ingredient...</option>
                    {allIngredients.map((ing) => (
                      <option key={ing.id} value={ing.id}>{ing.name}</option>
                    ))}
                  </select>
                </TableCell>
                <TableCell>
                  <Input type="number" step="any" placeholder="oz" value={addAmount}
                    onChange={(e) => setAddAmount(e.target.value)} className="w-20 h-8" />
                </TableCell>
                <TableCell></TableCell>
                <TableCell>
                  <Button size="sm" onClick={addIngredient}
                    disabled={!addIngId || !addAmount}>Add</Button>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div className="mt-3 text-sm font-semibold">
          Total: {totals.total_weight} oz &middot; {totals.total_calories} cal &middot; {totals.cal_per_oz ?? '\u2014'} cal/oz
          {(totals.protein_g > 0 || totals.fat_g > 0 || totals.carb_g > 0) && (
            <span className="ml-2 font-normal text-muted-foreground">
              &middot; {totals.protein_g}g P / {totals.fat_g}g F / {totals.carb_g}g C
            </span>
          )}
        </div>
      </div>

      <div className="flex gap-2">
        <Button onClick={handleSave}>Save</Button>
        <Button variant="outline" onClick={() => navigate('/recipes')}>Cancel</Button>
        {!isNew && (
          <Button variant="destructive" onClick={() => setDeleteOpen(true)}>Delete</Button>
        )}
      </div>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Recipe</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{form.name}&rdquo;? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default RecipeEditPage;
