import { useState, useEffect } from 'react';
import { get, post, put, del } from '../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { StarRating } from '@/components/ui/star-rating';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

const CATEGORIES = [
  { value: '', label: 'None' },
  { value: 'drink_mix', label: 'Drink Mix' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'salty', label: 'Salty' },
  { value: 'sweet', label: 'Sweet' },
  { value: 'bars_energy', label: 'Bars/Energy' },
];

const CATEGORY_LABELS = Object.fromEntries(CATEGORIES.filter(c => c.value).map(c => [c.value, c.label]));

function SnackCatalogPage() {
  const [snacks, setSnacks] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState({
    ingredient_id: '', weight_per_serving: '', calories_per_serving: '', category: '', notes: '',
  });
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [sortCol, setSortCol] = useState('ingredient_name');
  const [sortAsc, setSortAsc] = useState(true);

  useEffect(() => {
    loadSnacks();
    get('/ingredients').then(setIngredients).catch(() => {});
  }, []);

  async function loadSnacks() {
    try {
      setSnacks(await get('/snacks'));
      setError(null);
    } catch (err) { setError(err.message); }
  }

  function handleSort(col) {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(true); }
  }

  function getSorted() {
    return [...snacks].sort((a, b) => {
      let aVal = a[sortCol], bVal = b[sortCol];
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';
      if (typeof aVal === 'number' && typeof bVal === 'number')
        return sortAsc ? aVal - bVal : bVal - aVal;
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortAsc ? cmp : -cmp;
    });
  }

  function sortArrow(col) {
    if (sortCol !== col) return '';
    return sortAsc ? ' \u25B2' : ' \u25BC';
  }

  async function handleAdd(e) {
    e.preventDefault();
    try {
      const created = await post('/snacks', {
        ingredient_id: parseInt(addForm.ingredient_id),
        weight_per_serving: parseFloat(addForm.weight_per_serving),
        calories_per_serving: parseFloat(addForm.calories_per_serving),
        category: addForm.category || null,
        notes: addForm.notes || null,
      });
      setSnacks([...snacks, created]);
      setAddForm({ ingredient_id: '', weight_per_serving: '', calories_per_serving: '', category: '', notes: '' });
      setAddOpen(false);
      setError(null);
    } catch (err) { setError(err.message); }
  }

  function startEdit(snack) {
    setEditingId(snack.id);
    setEditForm({
      weight_per_serving: snack.weight_per_serving ?? '',
      calories_per_serving: snack.calories_per_serving ?? '',
      category: snack.category ?? '',
      notes: snack.notes ?? '',
      rating: snack.rating ?? null,
    });
  }

  async function saveEdit(id) {
    try {
      const updated = await put(`/snacks/${id}`, {
        weight_per_serving: parseFloat(editForm.weight_per_serving),
        calories_per_serving: parseFloat(editForm.calories_per_serving),
        category: editForm.category || null,
        notes: editForm.notes || null,
        rating: editForm.rating,
      });
      setSnacks(snacks.map((s) => (s.id === id ? updated : s)));
      setEditingId(null);
      setError(null);
    } catch (err) { setError(err.message); }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await del(`/snacks/${deleteTarget.id}`);
      setSnacks(snacks.filter((s) => s.id !== deleteTarget.id));
      setDeleteTarget(null);
      setError(null);
    } catch (err) { setError(err.message); }
  }

  const sorted = getSorted();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Snack Catalog</h2>
        <Button onClick={() => setAddOpen(true)}>+ Add Snack Item</Button>
      </div>

      {error && <p className="text-destructive text-sm">{error}</p>}

      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <SortHead col="ingredient_name" label="Ingredient" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
              <SortHead col="category" label="Category" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
              <SortHead col="weight_per_serving" label="Wt/Serving (oz)" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} className="text-right" />
              <SortHead col="calories_per_serving" label="Cal/Serving" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} className="text-right" />
              <SortHead col="calories_per_oz" label="Cal/oz" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} className="text-right" />
              <SortHead col="rating" label="Rating" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
              <SortHead col="notes" label="Notes" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
              <TableHead className="w-28"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((s) =>
              editingId === s.id ? (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.ingredient_name}</TableCell>
                  <TableCell>
                    <select value={editForm.category}
                      onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                      className="flex h-8 w-full rounded-md border border-input bg-background px-2 text-sm">
                      {CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>{c.label}</option>
                      ))}
                    </select>
                  </TableCell>
                  <TableCell className="text-right">
                    <Input type="number" step="any" value={editForm.weight_per_serving}
                      onChange={(e) => setEditForm({ ...editForm, weight_per_serving: e.target.value })}
                      className="w-20 h-8 ml-auto" />
                  </TableCell>
                  <TableCell className="text-right">
                    <Input type="number" step="any" value={editForm.calories_per_serving}
                      onChange={(e) => setEditForm({ ...editForm, calories_per_serving: e.target.value })}
                      className="w-20 h-8 ml-auto" />
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">&mdash;</TableCell>
                  <TableCell>
                    <StarRating value={editForm.rating} onChange={(r) => setEditForm({ ...editForm, rating: r })} />
                  </TableCell>
                  <TableCell>
                    <Input value={editForm.notes}
                      onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                      className="h-8" />
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" onClick={() => saveEdit(s.id)}>Save</Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                <TableRow key={s.id} className="even:bg-muted/50">
                  <TableCell className="font-medium">{s.ingredient_name}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">{CATEGORY_LABELS[s.category] || ''}</TableCell>
                  <TableCell className="text-right">{s.weight_per_serving}</TableCell>
                  <TableCell className="text-right">{s.calories_per_serving}</TableCell>
                  <TableCell className="text-right">{s.calories_per_oz}</TableCell>
                  <TableCell>
                    <StarRating value={s.rating} onChange={async (r) => {
                      try {
                        const updated = await put(`/snacks/${s.id}`, { rating: r });
                        setSnacks(snacks.map((x) => (x.id === s.id ? updated : x)));
                      } catch (err) { setError(err.message); }
                    }} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">{s.notes}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => startEdit(s)}>Edit</Button>
                      <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteTarget(s)}>Delete</Button>
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
              <DialogTitle>Add Snack Item</DialogTitle>
              <DialogDescription>Select an ingredient and set serving info.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Ingredient</Label>
                <select value={addForm.ingredient_id}
                  onChange={(e) => setAddForm({ ...addForm, ingredient_id: e.target.value })}
                  required
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                  <option value="">Select ingredient...</option>
                  {ingredients.map((ing) => (
                    <option key={ing.id} value={ing.id}>{ing.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Weight/serving (oz)</Label>
                  <Input type="number" step="any" required value={addForm.weight_per_serving}
                    onChange={(e) => setAddForm({ ...addForm, weight_per_serving: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Calories/serving</Label>
                  <Input type="number" step="any" required value={addForm.calories_per_serving}
                    onChange={(e) => setAddForm({ ...addForm, calories_per_serving: e.target.value })} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Category</Label>
                <select value={addForm.category}
                  onChange={(e) => setAddForm({ ...addForm, category: e.target.value })}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
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
            <DialogTitle>Delete Snack</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{deleteTarget?.ingredient_name}&rdquo;?
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

export default SnackCatalogPage;
