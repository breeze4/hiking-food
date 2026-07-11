import { useState } from 'react';
import { useTrip } from '../context/TripContext';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';

function TripSelector() {
  const { trips, activeTripId, selectTrip, createTrip, cloneTrip, deleteTrip, tripMutation } = useTrip();
  const [newOpen, setNewOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [newName, setNewName] = useState('');

  const activeTrip = trips.find((t) => t.id === activeTripId);
  const { pending, error } = tripMutation;

  async function handleCreate() {
    if (!newName.trim()) return;
    const trip = await createTrip(newName.trim());
    if (trip) {
      setNewName('');
      setNewOpen(false);
    }
  }

  async function handleDelete() {
    const ok = await deleteTrip();
    if (ok) setDeleteOpen(false);
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <select
        aria-label="Active trip"
        value={activeTripId || ''}
        onChange={(e) => selectTrip(parseInt(e.target.value))}
        className="h-9 rounded-md border border-input bg-background px-3 text-sm"
      >
        {trips.length === 0 && <option value="">No trips</option>}
        {trips.map((t) => (
          <option key={t.id} value={t.id}>{t.name}</option>
        ))}
      </select>
      <Button variant="outline" size="sm" onClick={() => setNewOpen(true)} disabled={pending}>New</Button>
      <Button variant="outline" size="sm" onClick={cloneTrip} disabled={!activeTripId || pending}>Clone</Button>
      <Button variant="outline" size="sm" onClick={() => setDeleteOpen(true)} disabled={!activeTripId || pending}
        className="text-destructive hover:text-destructive">Delete</Button>
      {error && !newOpen && !deleteOpen && (
        <span className="text-destructive text-sm" role="alert">{error.message}</span>
      )}

      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Trip</DialogTitle>
            <DialogDescription>Enter a name for the new trip.</DialogDescription>
          </DialogHeader>
          <Input
            placeholder="Trip name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            autoFocus
          />
          {error && <p className="text-destructive text-sm" role="alert">{error.message}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!newName.trim() || pending}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Trip</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{activeTrip?.name}&rdquo;? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {error && <p className="text-destructive text-sm" role="alert">{error.message}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={pending}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default TripSelector;
