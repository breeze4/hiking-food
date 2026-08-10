import { useState } from 'react';
import { SquarePen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip';

// Notes control for table rows: a new-note icon when empty, a truncated
// preview with a full-text tooltip when set. Either opens a dialog with a
// full-size textarea for viewing and editing.
function NotesCell({ name, value, disabled, onSave }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');

  const note = value || '';

  function handleOpenChange(next) {
    if (next) setDraft(note);
    setOpen(next);
  }

  function handleSave() {
    onSave(draft.trim());
    setOpen(false);
  }

  return (
    <>
      {note ? (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger render={
              <button
                type="button"
                disabled={disabled}
                aria-label={`${name} notes`}
                onClick={() => handleOpenChange(true)}
                className="group flex max-w-40 items-center gap-1.5 text-left text-xs disabled:opacity-50"
              >
                <span className="truncate">{note}</span>
                <SquarePen className="size-3.5 shrink-0 text-muted-foreground group-hover:text-foreground" />
              </button>
            } />
            <TooltipContent className="max-w-xs whitespace-pre-wrap">{note}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ) : (
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground"
          aria-label={`${name} notes`}
          disabled={disabled}
          onClick={() => handleOpenChange(true)}
        >
          <SquarePen className="size-4" />
        </Button>
      )}

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Notes &mdash; {name}</DialogTitle>
          </DialogHeader>
          <Textarea
            value={draft}
            aria-label={`${name} notes`}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleSave();
            }}
            placeholder="notes..."
            className="min-h-32"
          />
          <DialogFooter>
            <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
            <Button size="sm" disabled={disabled} onClick={handleSave}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default NotesCell;
