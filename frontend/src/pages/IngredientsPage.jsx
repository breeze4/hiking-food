import { useState, useEffect } from 'react';
import { get, post, put, del } from '../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

const PACKING_METHODS = [
  { value: '', label: 'None' },
  { value: 'bag', label: 'Bag' },
  { value: 'container', label: 'Container' },
  { value: 'original', label: 'Original' },
  { value: 'repack', label: 'Repack' },
];

const PACKING_METHOD_LABELS = Object.fromEntries(PACKING_METHODS.filter(p => p.value).map(p => [p.value, p.label]));

function IngredientsPage() {
  const [ingredients, setIngredients] = useState([]);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState({ name: '', calories_per_oz: '', notes: '' });
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [sortCol, setSortCol] = useState('name');
  const [sortAsc, setSortAsc] = useState(true);

  useEffect(() => {
    get('/ingredients').then(setIngredients).catch((err) => setError(err.message));
  }, []);

  function handleSort(col) {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(true); }
  }

  function getSorted() {
    return [...ingredients].sort((a, b) => {
      let aVal = a[sortCol], bVal = b[sortCol];
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';
      if (typeof aVal === 'number' && typeof bVal === 'number')
        return sortAsc ? aVal - bVal : bVal - aVal;
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortAsc ? cmp : -cmp;
    });
  }

  async function handleAdd(e) {
    e.preventDefault();
    try {
      const created = await post('/ingredients', {
        name: addForm.name,
        calories_per_oz: parseFloat(addForm.calories_per_oz),
        notes: addForm.notes || null,
      });
      setIngredients([...ingredients, created]);
      setAddForm({ name: '', calories_per_oz: '', notes: '' });
      setAddOpen(false);
      setError(null);
    } catch (err) { setError(err.message); }
  }

  function startEdit(ingredient) {
    setEditingId(ingredient.id);
    setEditForm({
      name: ingredient.name,
      calories_per_oz: ingredient.calories_per_oz ?? '',
      essentials: ingredient.essentials ?? false,
      packing_method: ingredient.packing_method ?? '',
      notes: ingredient.notes ?? '',
    });
  }

  async function saveEdit(id) {
    try {
      const updated = await put(`/ingredients/${id}`, {
        name: editForm.name,
        calories_per_oz: parseFloat(editForm.calories_per_oz),
        essentials: editForm.essentials,
        packing_method: editForm.packing_method || null,
        notes: editForm.notes || null,
      });
      setIngredients(ingredients.map((i) => (i.id === id ? updated : i)));
      setEditingId(null);
      setError(null);
    } catch (err) { setError(err.message); }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await del(`/ingredients/${deleteTarget.id}`);
      setIngredients(ingredients.filter((i) => i.id !== deleteTarget.id));
      setDeleteTarget(null);
      setError(null);
    } catch (err) { setError(err.message); }
  }

  const sorted = getSorted();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Ingredients</h2>
        <Button onClick={() => setAddOpen(true)}>+ Add Ingredient</Button>
      </div>

      {error && <p className="text-destructive text-sm">{error}</p>}

      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <SortHead col="name" label="Name" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
              <SortHead col="calories_per_oz" label="Cal/oz" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} className="text-right" />
              <SortHead col="essentials" label="Essential" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
              <SortHead col="packing_method" label="Packing" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
              <SortHead col="notes" label="Notes" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
              <TableHead className="w-28"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((ing) =>
              editingId === ing.id ? (
                <TableRow key={ing.id}>
                  <TableCell>
                    <Input value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      className="h-8" />
                  </TableCell>
                  <TableCell className="text-right">
                    <Input type="number" step="any" value={editForm.calories_per_oz}
                      onChange={(e) => setEditForm({ ...editForm, calories_per_oz: e.target.value })}
                      className="w-20 h-8 ml-auto" />
                  </TableCell>
                  <TableCell>
                    <Checkbox checked={editForm.essentials}
                      onCheckedChange={(checked) => setEditForm({ ...editForm, essentials: !!checked })} />
                  </TableCell>
                  <TableCell>
                    <select value={editForm.packing_method}
                      onChange={(e) => setEditForm({ ...editForm, packing_method: e.target.value })}
                      className="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm">
                      {PACKING_METHODS.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                      ))}
                    </select>
                  </TableCell>
                  <TableCell>
                    <Input value={editForm.notes}
                      onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                      className="h-8" />
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" onClick={() => saveEdit(ing.id)}>Save</Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                <TableRow key={ing.id} className="even:bg-muted/50">
                  <TableCell className="font-medium">{ing.name}</TableCell>
                  <TableCell className="text-right">{ing.calories_per_oz}</TableCell>
                  <TableCell>{ing.essentials && <span className="text-xs text-muted-foreground">Yes</span>}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">{PACKING_METHOD_LABELS[ing.packing_method] || ''}</TableCell>
                  <TableCell className="text-muted-foreground">{ing.notes}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => startEdit(ing)}>Edit</Button>
                      <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteTarget(ing)}>Delete</Button>
                    </div>
                  </TableCell>
                </TableRow>
              )
            )}
          </TableBody>
        </Table>
      </div>

      {/* Add Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <form onSubmit={handleAdd}>
            <DialogHeader>
              <DialogTitle>Add Ingredient</DialogTitle>
              <DialogDescription>Enter ingredient details.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={addForm.name} required
                  onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Calories per oz</Label>
                <Input type="number" step="any" required value={addForm.calories_per_oz}
                  onChange={(e) => setAddForm({ ...addForm, calories_per_oz: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Notes</Label>
                <Input value={addForm.notes}
                  onChange={(e) => setAddForm({ ...addForm, notes: e.target.value })} />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
              <Button type="submit">Add</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Ingredient</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{deleteTarget?.name}&rdquo;?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SortHead({ col, label, sortCol, sortAsc, onClick, className = '' }) {
  const arrow = sortCol === col ? (sortAsc ? ' \u25B2' : ' \u25BC') : '';
  return (
    <TableHead className={`cursor-pointer select-none ${className}`} onClick={() => onClick(col)}>
      {label}{arrow}
    </TableHead>
  );
}

export default IngredientsPage;
