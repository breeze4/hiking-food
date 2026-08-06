import { useState, useEffect, useMemo } from 'react';
import {
  get, listSnackUnitTypes, createSnackUnitType, updateSnackUnitType, deleteSnackUnitType,
} from '../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

const EMPTY_FORM = { id: null, name: '', notes: '', composition: [] };

function SnackUnitLibraryPage() {
  const [unitTypes, setUnitTypes] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [error, setError] = useState(null);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [addIngId, setAddIngId] = useState('');
  const [addAmount, setAddAmount] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  useEffect(() => {
    loadUnitTypes();
    get('/ingredients').then(setIngredients).catch(() => {});
  }, []);

  async function loadUnitTypes() {
    try {
      setUnitTypes(await listSnackUnitTypes());
      setError(null);
    } catch (err) { setError(err.message); }
  }

  const ingLookup = useMemo(() => {
    const map = {};
    ingredients.forEach((i) => { map[i.id] = i; });
    return map;
  }, [ingredients]);

  // A preview of what the server will derive, so weight and calories move as
  // the bag is built. The saved values in the table are the server's.
  const preview = useMemo(() => {
    let weight = 0, calories = 0;
    form.composition.forEach((row) => {
      const amount = row.amount_oz || 0;
      weight += amount;
      calories += amount * (ingLookup[row.ingredient_id]?.calories_per_oz ?? 0);
    });
    return {
      weight: Math.round(weight * 100) / 100,
      calories: Math.round(calories * 10) / 10,
    };
  }, [form.composition, ingLookup]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setAddIngId('');
    setAddAmount('');
    setBuilderOpen(true);
  }

  function openEdit(unitType) {
    setForm({
      id: unitType.id,
      name: unitType.name,
      notes: unitType.notes ?? '',
      composition: unitType.composition.map((row) => ({
        ingredient_id: row.ingredient_id,
        ingredient_name: row.ingredient_name,
        amount_oz: row.amount_oz,
      })),
    });
    setAddIngId('');
    setAddAmount('');
    setBuilderOpen(true);
  }

  function addCompositionRow() {
    const ingredient = ingLookup[parseInt(addIngId)];
    if (!ingredient || !addAmount) return;
    setForm({
      ...form,
      composition: [...form.composition, {
        ingredient_id: ingredient.id,
        ingredient_name: ingredient.name,
        amount_oz: parseFloat(addAmount),
      }],
    });
    setAddIngId('');
    setAddAmount('');
  }

  function removeCompositionRow(index) {
    setForm({
      ...form,
      composition: form.composition.filter((_, i) => i !== index),
    });
  }

  function updateCompositionAmount(index, value) {
    setForm({
      ...form,
      composition: form.composition.map((row, i) => (
        i === index ? { ...row, amount_oz: parseFloat(value) || 0 } : row
      )),
    });
  }

  async function handleSave(e) {
    e.preventDefault();
    const payload = {
      name: form.name,
      notes: form.notes || null,
      composition: form.composition.map((row) => ({
        ingredient_id: row.ingredient_id,
        amount_oz: row.amount_oz,
      })),
    };
    try {
      if (form.id) await updateSnackUnitType(form.id, payload);
      else await createSnackUnitType(payload);
      setBuilderOpen(false);
      setForm(EMPTY_FORM);
      await loadUnitTypes();
    } catch (err) { setError(err.message); }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteSnackUnitType(deleteTarget.id);
      setDeleteTarget(null);
      setDeleteError(null);
      await loadUnitTypes();
    } catch (err) { setDeleteError(err.message); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Snack Unit Library</h2>
        <Button onClick={openCreate}>+ Add Bag</Button>
      </div>

      <p className="text-muted-foreground text-sm">
        A bag is one snack unit: bulk ingredients portioned to about 2 oz. Weight,
        calories, and macros are derived from the composition below.
      </p>

      {error && <p className="text-destructive text-sm">{error}</p>}

      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Bag</TableHead>
              <TableHead>Composition</TableHead>
              <TableHead className="text-right">Weight (oz)</TableHead>
              <TableHead className="text-right">Calories</TableHead>
              <TableHead className="text-right">Cal/oz</TableHead>
              <TableHead className="text-right">P / F / C (g)</TableHead>
              <TableHead>Notes</TableHead>
              <TableHead className="w-28"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {unitTypes.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-muted-foreground">
                  No bags yet. Add one to reuse it on every trip.
                </TableCell>
              </TableRow>
            )}
            {unitTypes.map((unitType) => (
              <TableRow key={unitType.id} className="even:bg-muted/50">
                <TableCell className="font-medium">{unitType.name}</TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {unitType.composition
                    .map((row) => `${row.ingredient_name} ${row.amount_oz} oz`)
                    .join(' + ') || '—'}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    {unitType.weight_oz}
                    {unitType.weight_warning && (
                      <Badge variant="destructive" title="Outside 25% of the 2 oz target">
                        Off target
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    {unitType.calories}
                    {!unitType.has_full_data && (
                      <Badge variant="outline" title="An ingredient is missing per-oz data">
                        Partial data
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right">{unitType.cal_per_oz ?? '—'}</TableCell>
                <TableCell className="text-right text-muted-foreground">
                  {unitType.protein_g} / {unitType.fat_g} / {unitType.carb_g}
                </TableCell>
                <TableCell className="text-muted-foreground">{unitType.notes}</TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button size="sm" variant="ghost" aria-label={`Edit ${unitType.name}`}
                      onClick={() => openEdit(unitType)}>Edit</Button>
                    <Button size="sm" variant="ghost" aria-label={`Delete ${unitType.name}`}
                      className="text-destructive hover:text-destructive"
                      onClick={() => { setDeleteTarget(unitType); setDeleteError(null); }}>
                      Delete
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Bag builder */}
      <Dialog open={builderOpen} onOpenChange={setBuilderOpen}>
        <DialogContent className="max-w-2xl">
          <form onSubmit={handleSave}>
            <DialogHeader>
              <DialogTitle>{form.id ? 'Edit Bag' : 'Add Bag'}</DialogTitle>
              <DialogDescription>
                Name the bag and list what goes in it, in ounces.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="bag-name">Name</Label>
                  <Input id="bag-name" required value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="bag-notes">Notes</Label>
                  <Input id="bag-notes" value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </div>
              </div>

              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Ingredient</TableHead>
                      <TableHead className="w-28">Amount (oz)</TableHead>
                      <TableHead className="w-20"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {form.composition.map((row, index) => (
                      <TableRow key={index} className="even:bg-muted/50">
                        <TableCell>{row.ingredient_name}</TableCell>
                        <TableCell>
                          <Input type="number" step="any" value={row.amount_oz}
                            aria-label={`${row.ingredient_name} amount in ounces`}
                            onChange={(e) => updateCompositionAmount(index, e.target.value)}
                            className="w-20 h-8" />
                        </TableCell>
                        <TableCell>
                          <Button type="button" variant="ghost" size="sm"
                            className="text-destructive hover:text-destructive"
                            onClick={() => removeCompositionRow(index)}>Remove</Button>
                        </TableCell>
                      </TableRow>
                    ))}
                    <TableRow>
                      <TableCell>
                        <select value={addIngId} aria-label="Ingredient to add"
                          onChange={(e) => setAddIngId(e.target.value)}
                          className="h-8 rounded-md border border-input bg-background px-2 text-sm w-full">
                          <option value="">Add ingredient...</option>
                          {ingredients.map((ing) => (
                            <option key={ing.id} value={ing.id}>{ing.name}</option>
                          ))}
                        </select>
                      </TableCell>
                      <TableCell>
                        <Input type="number" step="any" placeholder="oz" value={addAmount}
                          aria-label="Amount in ounces to add"
                          onChange={(e) => setAddAmount(e.target.value)}
                          className="w-20 h-8" />
                      </TableCell>
                      <TableCell>
                        <Button type="button" size="sm" onClick={addCompositionRow}
                          disabled={!addIngId || !addAmount}>Add</Button>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              <p className="text-sm font-semibold">
                Bag total: {preview.weight} oz &middot; {preview.calories} cal
              </p>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline"
                onClick={() => setBuilderOpen(false)}>Cancel</Button>
              <Button type="submit">Save</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={!!deleteTarget}
        onOpenChange={(open) => { if (!open) { setDeleteTarget(null); setDeleteError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Bag</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{deleteTarget?.name}&rdquo;?
            </DialogDescription>
          </DialogHeader>
          {deleteError && <p className="text-destructive text-sm">{deleteError}</p>}
          <DialogFooter>
            <Button variant="outline"
              onClick={() => { setDeleteTarget(null); setDeleteError(null); }}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default SnackUnitLibraryPage;
