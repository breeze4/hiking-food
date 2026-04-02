import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { get, put } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

const SNACK_SLOTS = [
  { value: 'lunch', label: 'Lunch' },
  { value: 'snacks', label: 'Snacks' },
];

function PackingScreen() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const [packing, setPacking] = useState(null);
  const [shoppingList, setShoppingList] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => { loadData(); }, [tripId]);

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

  if (error) return <p className="text-destructive">{error}</p>;
  if (!packing) return <p className="text-muted-foreground">Loading...</p>;

  const packedSnacks = packing.snacks.filter((s) => s.packed).length;
  const packedMeals = packing.meals.filter((m) => m.packed).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Packing: {packing.trip_name}</h2>
        <Button variant="outline" onClick={() => navigate('/')}>Back to Planner</Button>
      </div>

      {/* Recipe Assembly */}
      <div>
        <div className="flex items-center gap-3 mb-3">
          <h3 className="text-lg font-semibold">Recipe Assembly</h3>
          {packing.meals.length > 0 && (
            <Badge variant="secondary">{packedMeals}/{packing.meals.length} packed</Badge>
          )}
        </div>
        {packing.meals.length === 0 && (
          <p className="text-muted-foreground text-sm">No meals selected for this trip.</p>
        )}
        <div className="space-y-3">
          {packing.meals.map((meal) => (
            <Card key={meal.id} className={meal.packed ? 'opacity-60' : ''}>
              <CardContent className="p-4">
                <div className="flex items-center gap-3 flex-wrap">
                  <Checkbox
                    checked={meal.packed}
                    onCheckedChange={(checked) => toggleMealPacked(meal.id, checked)}
                  />
                  <span className={`font-medium ${meal.packed ? 'line-through' : ''}`}>
                    {meal.recipe_name}
                  </span>
                  <Badge variant="outline" className="text-xs">{meal.category}</Badge>
                  {meal.quantity > 1 && <Badge variant="secondary">x{meal.quantity}</Badge>}
                  <div className="ml-auto flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Actual:</span>
                    <Input
                      type="number"
                      step="any"
                      defaultValue={meal.actual_weight_oz || ''}
                      onBlur={(e) => setMealWeight(meal.id, e.target.value)}
                      className="w-20 h-8"
                    />
                    <span className="text-sm text-muted-foreground">oz</span>
                  </div>
                </div>
                <Table className="mt-2">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Ingredient</TableHead>
                      <TableHead className="text-xs text-right">Amount (oz)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {meal.ingredients.map((ing, i) => (
                      <TableRow key={i}>
                        <TableCell className="py-1 text-sm">{ing.name}</TableCell>
                        <TableCell className="py-1 text-sm text-right">{ing.amount_oz}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {meal.at_home_prep && (
                  <Collapsible className="mt-2">
                    <CollapsibleTrigger className="text-sm text-muted-foreground hover:text-foreground cursor-pointer">
                      At-home prep &rsaquo;
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <pre className="whitespace-pre-wrap text-sm mt-1 p-2 bg-muted rounded-md">
                        {meal.at_home_prep}
                      </pre>
                    </CollapsibleContent>
                  </Collapsible>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Snack Packing */}
      <div>
        <div className="flex items-center gap-3 mb-3">
          <h3 className="text-lg font-semibold">Snack Packing</h3>
          {packing.snacks.length > 0 && (
            <Badge variant="secondary">{packedSnacks}/{packing.snacks.length} packed</Badge>
          )}
        </div>
        {packing.snacks.length === 0 ? (
          <p className="text-muted-foreground text-sm">No snacks selected for this trip.</p>
        ) : (
          <div className="space-y-4">
            {SNACK_SLOTS.map(({ value, label }) => {
              const slotSnacks = packing.snacks.filter(s => (s.slot || 'snacks') === value);
              if (slotSnacks.length === 0) return null;
              return (
                <div key={value}>
                  <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">{label}</h4>
                  <Card>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-10"></TableHead>
                          <TableHead>Item</TableHead>
                          <TableHead className="text-right">Servings</TableHead>
                          <TableHead className="text-right">Target (oz)</TableHead>
                          <TableHead className="text-right">Target Cal</TableHead>
                          <TableHead className="text-right">Actual (oz)</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {slotSnacks.map((s) => (
                          <TableRow key={s.id} className={s.packed ? 'opacity-60' : ''}>
                            <TableCell>
                              <Checkbox
                                checked={s.packed}
                                onCheckedChange={(checked) => toggleSnackPacked(s.id, checked)}
                              />
                            </TableCell>
                            <TableCell className={`font-medium ${s.packed ? 'line-through' : ''}`}>
                              {s.ingredient_name}
                            </TableCell>
                            <TableCell className="text-right">{s.servings}</TableCell>
                            <TableCell className="text-right">{s.target_weight}</TableCell>
                            <TableCell className="text-right">{s.target_calories}</TableCell>
                            <TableCell className="text-right">
                              <Input
                                type="number"
                                step="any"
                                defaultValue={s.actual_weight_oz || ''}
                                onBlur={(e) => setSnackWeight(s.id, e.target.value)}
                                className="w-20 h-7 ml-auto"
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Card>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Shopping List */}
      <Collapsible defaultOpen>
        <div className="flex items-center gap-3 mb-3">
          <CollapsibleTrigger className="flex items-center gap-2 cursor-pointer">
            <h3 className="text-lg font-semibold">Shopping List</h3>
            <Badge variant="secondary">{shoppingList.length} items</Badge>
          </CollapsibleTrigger>
        </div>
        <CollapsibleContent>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ingredient</TableHead>
                  <TableHead className="text-right">Total (oz)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shoppingList.map((item) => (
                  <TableRow key={item.ingredient_id}>
                    <TableCell>{item.ingredient_name}</TableCell>
                    <TableCell className="text-right">{item.total_oz}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

export default PackingScreen;
