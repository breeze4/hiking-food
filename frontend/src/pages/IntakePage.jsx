import { useState, useEffect } from 'react';
import { get, post, patch, del } from '../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const STATUS_SECTIONS = [
  { key: 'pending', label: 'Pending' },
  { key: 'researched', label: 'Researched' },
  { key: 'added', label: 'Added' },
];

function IntakePage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const [addName, setAddName] = useState('');
  const [addNotes, setAddNotes] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ name: '', notes: '' });

  useEffect(() => {
    loadItems();
  }, []);

  async function loadItems() {
    try {
      const data = await get('/food-intake');
      setItems(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAdd(e) {
    e.preventDefault();
    const name = addName.trim();
    if (!name) return;
    try {
      const created = await post('/food-intake', {
        name,
        notes: addNotes.trim() || null,
      });
      setItems([...items, created]);
      setAddName('');
      setAddNotes('');
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(item) {
    setEditingId(item.id);
    setEditForm({ name: item.name, notes: item.notes ?? '' });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm({ name: '', notes: '' });
  }

  async function saveEdit(id) {
    const name = editForm.name.trim();
    if (!name) return;
    try {
      const updated = await patch(`/food-intake/${id}`, {
        name,
        notes: editForm.notes.trim() || null,
      });
      setItems(items.map((i) => (i.id === id ? updated : i)));
      cancelEdit();
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    try {
      await del(`/food-intake/${id}`);
      setItems(items.filter((i) => i.id !== id));
      if (editingId === id) cancelEdit();
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  const grouped = {
    pending: items.filter((i) => i.status === 'pending'),
    researched: items.filter((i) => i.status === 'researched'),
    added: items.filter((i) => i.status === 'added'),
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <h2 className="text-2xl font-semibold tracking-tight">Food Intake</h2>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {/* Add form — top of page, mobile-first, one-thumb friendly */}
      <form onSubmit={handleAdd} className="space-y-3 rounded-md border p-4 bg-muted/30">
        <div className="space-y-2">
          <Label htmlFor="intake-name">Food name</Label>
          <Input
            id="intake-name"
            value={addName}
            onChange={(e) => setAddName(e.target.value)}
            placeholder="e.g. Chomps beef sticks"
            autoComplete="off"
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="intake-notes">Notes (optional)</Label>
          <Input
            id="intake-notes"
            value={addNotes}
            onChange={(e) => setAddNotes(e.target.value)}
            placeholder="e.g. REI, $4"
            autoComplete="off"
          />
        </div>
        <Button type="submit" className="w-full">Add to queue</Button>
      </form>

      {STATUS_SECTIONS.map((section) => (
        <section key={section.key} className="space-y-2">
          <h3 className="text-lg font-semibold tracking-tight">
            {section.label}
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              ({grouped[section.key].length})
            </span>
          </h3>
          {grouped[section.key].length === 0 ? (
            <p className="text-muted-foreground text-sm italic">No items.</p>
          ) : (
            <ul className="space-y-2">
              {grouped[section.key].map((item) =>
                editingId === item.id ? (
                  <li key={item.id} className="rounded-md border p-3 space-y-2">
                    <Input
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      placeholder="Name"
                    />
                    <Input
                      value={editForm.notes}
                      onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                      placeholder="Notes"
                    />
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => saveEdit(item.id)}>Save</Button>
                      <Button size="sm" variant="ghost" onClick={cancelEdit}>Cancel</Button>
                    </div>
                  </li>
                ) : (
                  <li
                    key={item.id}
                    className="rounded-md border p-3 flex items-start justify-between gap-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-medium break-words">{item.name}</div>
                      {item.notes && (
                        <div className="text-sm text-muted-foreground break-words">
                          {item.notes}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <Button size="sm" variant="ghost" onClick={() => startEdit(item)}>
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleDelete(item.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </li>
                )
              )}
            </ul>
          )}
        </section>
      ))}
    </div>
  );
}

export default IntakePage;
