import { useState, useEffect } from 'react';
import { get, post, put, del } from '../api';
import { useTrip } from '../context/TripContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

function SnackSelection() {
  const { tripDetail, refreshTrip } = useTrip();
  const [catalog, setCatalog] = useState([]);
  const [addItemId, setAddItemId] = useState('');

  useEffect(() => {
    get('/snacks').then(setCatalog).catch(() => {});
  }, []);

  if (!tripDetail) return null;

  const snacks = tripDetail.snacks || [];

  async function handleAdd() {
    if (!addItemId) return;
    await post(`/trips/${tripDetail.id}/snacks`, {
      catalog_item_id: parseInt(addItemId),
      servings: 1,
    });
    setAddItemId('');
    refreshTrip();
  }

  async function updateServings(snackId, newServings) {
    if (newServings <= 0) {
      await del(`/trips/${tripDetail.id}/snacks/${snackId}`);
    } else {
      await put(`/trips/${tripDetail.id}/snacks/${snackId}`, { servings: newServings });
    }
    refreshTrip();
  }

  async function updateNotes(snackId, trip_notes) {
    await put(`/trips/${tripDetail.id}/snacks/${snackId}`, { trip_notes: trip_notes || null });
    refreshTrip();
  }

  const usedCatalogIds = new Set(snacks.map((s) => s.catalog_item_id));
  const available = catalog.filter((c) => !usedCatalogIds.has(c.id));

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Snacks</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Desktop table */}
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead className="w-36">Servings</TableHead>
                <TableHead className="text-right">Wt</TableHead>
                <TableHead className="text-right">Cal</TableHead>
                <TableHead className="text-right">Cal/oz</TableHead>
                <TableHead>Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {snacks.map((s) => (
                <TableRow key={s.id} className="even:bg-muted/50">
                  <TableCell className="font-medium">{s.ingredient_name}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="outline" size="icon" className="h-7 w-7"
                        onClick={() => updateServings(s.id, s.servings - 0.5)}>-</Button>
                      <Input
                        type="number"
                        step="0.5"
                        value={s.servings}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value);
                          if (!isNaN(val)) updateServings(s.id, val);
                        }}
                        className="w-14 text-center h-7"
                      />
                      <Button variant="outline" size="icon" className="h-7 w-7"
                        onClick={() => updateServings(s.id, s.servings + 0.5)}>+</Button>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">{s.total_weight}</TableCell>
                  <TableCell className="text-right">{s.total_calories}</TableCell>
                  <TableCell className="text-right">{s.calories_per_oz}</TableCell>
                  <TableCell>
                    <Input
                      defaultValue={s.trip_notes || ''}
                      onBlur={(e) => updateNotes(s.id, e.target.value)}
                      placeholder="notes..."
                      className="h-7 text-xs w-28"
                    />
                  </TableCell>
                </TableRow>
              ))}
              {snacks.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-muted-foreground text-center py-4">
                    No snacks added.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Mobile card layout */}
        <div className="md:hidden space-y-2">
          {snacks.map((s) => (
            <div key={s.id} className="border rounded-lg p-3 space-y-2">
              <div className="font-medium text-sm">{s.ingredient_name}</div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <Button variant="outline" size="icon" className="h-8 w-8"
                    onClick={() => updateServings(s.id, s.servings - 0.5)}>-</Button>
                  <span className="w-10 text-center font-medium">{s.servings}</span>
                  <Button variant="outline" size="icon" className="h-8 w-8"
                    onClick={() => updateServings(s.id, s.servings + 0.5)}>+</Button>
                </div>
                <div className="text-xs text-muted-foreground text-right">
                  {s.total_weight} oz &middot; {s.total_calories} cal &middot; {s.calories_per_oz} c/oz
                </div>
              </div>
            </div>
          ))}
          {snacks.length === 0 && (
            <p className="text-muted-foreground text-center py-4 text-sm">No snacks added.</p>
          )}
        </div>

        <div className="flex gap-2 mt-3">
          <select
            value={addItemId}
            onChange={(e) => setAddItemId(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm flex-1 max-w-xs"
          >
            <option value="">Add snack...</option>
            {available.map((c) => (
              <option key={c.id} value={c.id}>{c.ingredient_name}</option>
            ))}
          </select>
          <Button onClick={handleAdd} disabled={!addItemId} size="sm">Add</Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default SnackSelection;
