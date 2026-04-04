import { useState, useEffect } from 'react';
import { get, put } from '../api';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

function SettingsModal() {
  const [open, setOpen] = useState(false);
  const [protein, setProtein] = useState(20);
  const [fat, setFat] = useState(30);
  const [carb, setCarb] = useState(50);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      get('/settings').then(data => {
        setProtein(data.macro_target_protein_pct);
        setFat(data.macro_target_fat_pct);
        setCarb(data.macro_target_carb_pct);
        setError(null);
      });
    }
  }, [open]);

  const total = protein + fat + carb;
  const sumValid = Math.abs(total - 100) < 0.1;

  async function handleSave() {
    if (!sumValid) return;
    setSaving(true);
    setError(null);
    try {
      await put('/settings', {
        macro_target_protein_pct: protein,
        macro_target_fat_pct: fat,
        macro_target_carb_pct: carb,
      });
      setOpen(false);
    } catch (e) {
      setError(e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={
        <Button variant="ghost" size="icon" title="Settings">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </Button>
      } />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Macro Targets</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Set target macro percentages. Must sum to 100%.
          </p>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label htmlFor="protein-pct">Protein %</Label>
              <Input
                id="protein-pct"
                type="number"
                min={0} max={100} step={1}
                value={protein}
                onChange={e => setProtein(Number(e.target.value))}
              />
            </div>
            <div>
              <Label htmlFor="fat-pct">Fat %</Label>
              <Input
                id="fat-pct"
                type="number"
                min={0} max={100} step={1}
                value={fat}
                onChange={e => setFat(Number(e.target.value))}
              />
            </div>
            <div>
              <Label htmlFor="carb-pct">Carb %</Label>
              <Input
                id="carb-pct"
                type="number"
                min={0} max={100} step={1}
                value={carb}
                onChange={e => setCarb(Number(e.target.value))}
              />
            </div>
          </div>
          <div className={`text-xs ${sumValid ? 'text-muted-foreground' : 'text-destructive font-medium'}`}>
            Total: {total}%{!sumValid && ' (must be 100%)'}
          </div>
          {error && <div className="text-xs text-destructive">{error}</div>}
        </div>
        <DialogFooter>
          <Button onClick={handleSave} disabled={!sumValid || saving} size="sm">
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default SettingsModal;
