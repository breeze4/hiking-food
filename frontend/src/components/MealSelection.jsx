import { useState, useEffect } from 'react';
import { get, post, put, del } from '../api';
import { useTrip } from '../context/TripContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

function MealSelection() {
  const { tripDetail, refreshTrip } = useTrip();
  const [recipes, setRecipes] = useState([]);
  const [addRecipeId, setAddRecipeId] = useState('');
  const [open, setOpen] = useState(true);

  useEffect(() => {
    get('/recipes').then(setRecipes).catch(() => {});
  }, []);

  if (!tripDetail) return null;

  const meals = tripDetail.meals || [];
  const totalWeight = meals.reduce((sum, m) => sum + (m.total_weight || 0), 0);
  const mealCount = meals.reduce((sum, m) => sum + m.quantity, 0);

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
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Meals</CardTitle>
              <div className="flex items-center gap-2">
                {mealCount > 0 && (
                  <Badge variant="secondary">{mealCount} meal{mealCount !== 1 && 's'} &middot; {totalWeight.toFixed(1)} oz</Badge>
                )}
                <ChevronIcon open={open} />
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Recipe</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="w-32">Qty</TableHead>
                  <TableHead className="text-right">Wt/Unit</TableHead>
                  <TableHead className="text-right">Total Wt</TableHead>
                  <TableHead className="text-right">Total Cal</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {meals.map((m) => (
                  <TableRow key={m.id} className="even:bg-muted/50">
                    <TableCell className="font-medium">{m.recipe_name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {m.category}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="outline" size="icon" className="h-7 w-7"
                          onClick={() => updateQuantity(m.id, m.quantity - 1)}>-</Button>
                        <span className="w-8 text-center text-sm">{m.quantity}</span>
                        <Button variant="outline" size="icon" className="h-7 w-7"
                          onClick={() => updateQuantity(m.id, m.quantity + 1)}>+</Button>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">{m.weight_per_unit}</TableCell>
                    <TableCell className="text-right">{m.total_weight}</TableCell>
                    <TableCell className="text-right">{m.total_calories}</TableCell>
                  </TableRow>
                ))}
                {meals.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-muted-foreground text-center py-4">
                      No meals selected.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            <div className="flex gap-2 mt-3">
              <select
                value={addRecipeId}
                onChange={(e) => setAddRecipeId(e.target.value)}
                className="h-9 rounded-md border border-input bg-background px-3 text-sm flex-1 max-w-xs"
              >
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
              <Button onClick={handleAdd} disabled={!addRecipeId} size="sm">Add</Button>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

function ChevronIcon({ open }) {
  return (
    <svg width="16" height="16" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"
      className={`transition-transform ${open ? 'rotate-180' : ''}`}>
      <path d="M3.13523 6.15803C3.3241 5.95657 3.64052 5.94637 3.84197 6.13523L7.5 9.56464L11.158 6.13523C11.3595 5.94637 11.6759 5.95657 11.8648 6.15803C12.0536 6.35949 12.0434 6.67591 11.842 6.86477L7.84197 10.6148C7.64964 10.7951 7.35036 10.7951 7.15803 10.6148L3.15803 6.86477C2.95657 6.67591 2.94637 6.35949 3.13523 6.15803Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd" />
    </svg>
  );
}

export default MealSelection;
