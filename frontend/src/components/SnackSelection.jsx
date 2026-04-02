import { useState, useEffect, useRef } from 'react';
import { get, post, put, del } from '../api';
import { useTrip } from '../context/TripContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StarRating } from '@/components/ui/star-rating';
import { Input } from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

const SLOTS = [
  { value: 'morning_snack', label: 'Morning Snack' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'afternoon_snack', label: 'Afternoon Snack' },
];

const SLOT_LABELS = Object.fromEntries(SLOTS.map(s => [s.value, s.label]));

const CATEGORY_FILTERS = [
  { value: '', label: 'All' },
  { value: 'drink_mix', label: 'Drink Mix' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'salty', label: 'Salty' },
  { value: 'sweet', label: 'Sweet' },
  { value: 'bars_energy', label: 'Bars/Energy' },
];

const CATEGORY_LABELS = Object.fromEntries(
  CATEGORY_FILTERS.filter(c => c.value).map(c => [c.value, c.label])
);

// Default category filter when adding to a specific slot
const SLOT_DEFAULT_CATEGORIES = {
  morning_snack: new Set(['bars_energy']),
  lunch: new Set(['lunch']),
  afternoon_snack: new Set(['salty', 'sweet']),
};

function SnackSelection() {
  const { tripDetail, refreshTrip } = useTrip();
  const [catalog, setCatalog] = useState([]);
  const [addingSlot, setAddingSlot] = useState(null); // which slot's add panel is open
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const searchRef = useRef(null);

  useEffect(() => {
    get('/snacks').then(setCatalog).catch(() => {});
  }, []);

  useEffect(() => {
    if (addingSlot && searchRef.current) searchRef.current.focus();
  }, [addingSlot]);

  if (!tripDetail) return null;

  const snacks = tripDetail.snacks || [];
  const usedCatalogIds = new Set(snacks.map((s) => s.catalog_item_id));

  // Separate drink mixes from slot snacks
  const drinkMixes = snacks.filter(s => s.category === 'drink_mix');
  const slotSnacks = snacks.filter(s => s.category !== 'drink_mix');

  // Group non-drink-mix snacks by slot
  const bySlot = {};
  for (const slot of SLOTS) bySlot[slot.value] = [];
  for (const s of slotSnacks) {
    const key = s.slot || 'afternoon_snack';
    if (!bySlot[key]) bySlot[key] = [];
    bySlot[key].push(s);
  }

  async function handleAdd(catalogId, slot) {
    if (!catalogId) return;
    await post(`/trips/${tripDetail.id}/snacks`, {
      catalog_item_id: catalogId,
      servings: 1,
      slot,
    });
    setAddingSlot(null);
    setSearch('');
    setCategoryFilter('');
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

  async function updateSlot(snackId, slot) {
    await put(`/trips/${tripDetail.id}/snacks/${snackId}`, { slot });
    refreshTrip();
  }

  function openAddPanel(slot) {
    setAddingSlot(slot);
    setSearch('');
    // Pre-filter to relevant categories for this slot
    setCategoryFilter('');
  }

  function closeAddPanel() {
    setAddingSlot(null);
    setSearch('');
    setCategoryFilter('');
  }

  const available = catalog.filter((c) => !usedCatalogIds.has(c.id));
  const filtered = available.filter((c) => {
    // Exclude drink_mix from slot add panels (they have their own section)
    if (addingSlot !== 'drink_mix' && c.category === 'drink_mix') return false;
    // For drink mix add panel, only show drink_mix items
    if (addingSlot === 'drink_mix' && c.category !== 'drink_mix') return false;
    if (search && !c.ingredient_name.toLowerCase().includes(search.toLowerCase())) return false;
    if (categoryFilter && c.category !== categoryFilter) return false;
    // When no explicit filter, default to slot-relevant categories
    if (!categoryFilter && !search && addingSlot && addingSlot !== 'drink_mix') {
      const defaults = SLOT_DEFAULT_CATEGORIES[addingSlot];
      if (defaults && c.category) return defaults.has(c.category);
    }
    return true;
  });

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Snacks</CardTitle>
      </CardHeader>
      <CardContent className="pt-0 space-y-4">
        {/* Drink Mixes section */}
        <DrinkMixSection
          snacks={drinkMixes}
          isAdding={addingSlot === 'drink_mix'}
          onStartAdd={() => openAddPanel('drink_mix')}
          onCancelAdd={closeAddPanel}
          onAdd={(catalogId) => handleAdd(catalogId, 'morning_snack')}
          onRemove={(snackId) => del(`/trips/${tripDetail.id}/snacks/${snackId}`).then(refreshTrip)}
          onUpdateNotes={updateNotes}
          search={search}
          setSearch={setSearch}
          categoryFilter={categoryFilter}
          setCategoryFilter={setCategoryFilter}
          filtered={filtered}
          searchRef={searchRef}
        />

        {SLOTS.map(({ value: slotValue, label: slotLabel }) => (
          <SlotSection
            key={slotValue}
            slot={slotValue}
            label={slotLabel}
            snacks={bySlot[slotValue]}
            isAdding={addingSlot === slotValue}
            onStartAdd={() => openAddPanel(slotValue)}
            onCancelAdd={closeAddPanel}
            onAdd={(catalogId) => handleAdd(catalogId, slotValue)}
            onUpdateServings={updateServings}
            onUpdateNotes={updateNotes}
            onUpdateSlot={updateSlot}
            search={search}
            setSearch={setSearch}
            categoryFilter={categoryFilter}
            setCategoryFilter={setCategoryFilter}
            filtered={filtered}
            searchRef={searchRef}
          />
        ))}
      </CardContent>
    </Card>
  );
}

function SlotSection({
  slot, label, snacks, isAdding,
  onStartAdd, onCancelAdd, onAdd,
  onUpdateServings, onUpdateNotes, onUpdateSlot,
  search, setSearch, categoryFilter, setCategoryFilter,
  filtered, searchRef,
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">{label}</h3>
        {!isAdding && (
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onStartAdd}>
            + Add
          </Button>
        )}
      </div>

      {isAdding && (
        <AddPanel
          slot={slot}
          onAdd={onAdd}
          onCancel={onCancelAdd}
          search={search}
          setSearch={setSearch}
          categoryFilter={categoryFilter}
          setCategoryFilter={setCategoryFilter}
          filtered={filtered}
          searchRef={searchRef}
        />
      )}

      {!isAdding && (
        <>
          {/* Desktop table */}
          <div className="hidden md:block">
            {snacks.length === 0 ? (
              <p className="text-muted-foreground text-xs py-2">No snacks in this slot.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-36">Servings</TableHead>
                    <TableHead className="text-right">Wt</TableHead>
                    <TableHead className="text-right">Cal</TableHead>
                    <TableHead className="text-right">Cal/oz</TableHead>
                    <TableHead>Notes</TableHead>
                    <TableHead className="w-32">Slot</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {snacks.map((s) => (
                    <TableRow key={s.id} className="even:bg-muted/50">
                      <TableCell className="font-medium">{s.ingredient_name}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="outline" size="icon" className="h-7 w-7"
                            onClick={() => onUpdateServings(s.id, s.servings - 0.5)}>-</Button>
                          <Input
                            type="number"
                            step="0.5"
                            value={s.servings}
                            onChange={(e) => {
                              const val = parseFloat(e.target.value);
                              if (!isNaN(val)) onUpdateServings(s.id, val);
                            }}
                            className="w-14 text-center h-7"
                          />
                          <Button variant="outline" size="icon" className="h-7 w-7"
                            onClick={() => onUpdateServings(s.id, s.servings + 0.5)}>+</Button>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{s.total_weight}</TableCell>
                      <TableCell className="text-right">{s.total_calories}</TableCell>
                      <TableCell className="text-right">{s.calories_per_oz}</TableCell>
                      <TableCell>
                        <Input
                          defaultValue={s.trip_notes || ''}
                          onBlur={(e) => onUpdateNotes(s.id, e.target.value)}
                          placeholder="notes..."
                          className="h-7 text-xs w-28"
                        />
                      </TableCell>
                      <TableCell>
                        <Select value={s.slot || slot} onValueChange={(v) => onUpdateSlot(s.id, v)}>
                          <SelectTrigger className="h-7 text-xs w-28">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {SLOTS.map((sl) => (
                              <SelectItem key={sl.value} value={sl.value}>{sl.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          {/* Mobile card layout */}
          <div className="md:hidden space-y-2">
            {snacks.map((s) => (
              <div key={s.id} className="border rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{s.ingredient_name}</span>
                  <Select value={s.slot || slot} onValueChange={(v) => onUpdateSlot(s.id, v)}>
                    <SelectTrigger className="h-7 text-xs w-28">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SLOTS.map((sl) => (
                        <SelectItem key={sl.value} value={sl.value}>{sl.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <Button variant="outline" size="icon" className="h-8 w-8"
                      onClick={() => onUpdateServings(s.id, s.servings - 0.5)}>-</Button>
                    <span className="w-10 text-center font-medium">{s.servings}</span>
                    <Button variant="outline" size="icon" className="h-8 w-8"
                      onClick={() => onUpdateServings(s.id, s.servings + 0.5)}>+</Button>
                  </div>
                  <div className="text-xs text-muted-foreground text-right">
                    {s.total_weight} oz &middot; {s.total_calories} cal &middot; {s.calories_per_oz} c/oz
                  </div>
                </div>
              </div>
            ))}
            {snacks.length === 0 && (
              <p className="text-muted-foreground text-xs py-2">No snacks in this slot.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function DrinkMixSection({
  snacks, isAdding, onStartAdd, onCancelAdd, onAdd, onRemove, onUpdateNotes,
  search, setSearch, categoryFilter, setCategoryFilter, filtered, searchRef,
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Drink Mixes</h3>
        {!isAdding && (
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onStartAdd}>
            + Add
          </Button>
        )}
      </div>

      {isAdding && (
        <AddPanel
          slot="drink_mix"
          onAdd={onAdd}
          onCancel={onCancelAdd}
          search={search}
          setSearch={setSearch}
          categoryFilter={categoryFilter}
          setCategoryFilter={setCategoryFilter}
          filtered={filtered}
          searchRef={searchRef}
          hideCategoryFilter
        />
      )}

      {!isAdding && (
        <>
          <div className="hidden md:block">
            {snacks.length === 0 ? (
              <p className="text-muted-foreground text-xs py-2">No drink mixes added.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="text-right">Servings</TableHead>
                    <TableHead className="text-right">Wt</TableHead>
                    <TableHead className="text-right">Cal</TableHead>
                    <TableHead>Notes</TableHead>
                    <TableHead className="w-10"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {snacks.map((s) => (
                    <TableRow key={s.id} className="even:bg-muted/50">
                      <TableCell className="font-medium">{s.ingredient_name}</TableCell>
                      <TableCell className="text-right text-muted-foreground">{s.servings}</TableCell>
                      <TableCell className="text-right">{s.total_weight}</TableCell>
                      <TableCell className="text-right">{s.total_calories}</TableCell>
                      <TableCell>
                        <Input
                          defaultValue={s.trip_notes || ''}
                          onBlur={(e) => onUpdateNotes(s.id, e.target.value)}
                          placeholder="notes..."
                          className="h-7 text-xs w-28"
                        />
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                          onClick={() => onRemove(s.id)}>×</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
          <div className="md:hidden space-y-2">
            {snacks.map((s) => (
              <div key={s.id} className="border rounded-lg p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{s.ingredient_name}</span>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                    onClick={() => onRemove(s.id)}>×</Button>
                </div>
                <div className="text-xs text-muted-foreground">
                  {s.servings} servings &middot; {s.total_weight} oz &middot; {s.total_calories} cal
                </div>
              </div>
            ))}
            {snacks.length === 0 && (
              <p className="text-muted-foreground text-xs py-2">No drink mixes added.</p>
            )}
          </div>
        </>
      )}
      <p className="text-xs text-muted-foreground mt-1">Servings auto-calculated from mixes/day setting.</p>
    </div>
  );
}

function AddPanel({ slot, onAdd, onCancel, search, setSearch, categoryFilter, setCategoryFilter, filtered, searchRef, hideCategoryFilter }) {
  return (
    <div className="mb-4 border rounded-lg bg-muted/30">
      <div className="p-3 border-b flex items-center gap-2">
        <Input
          ref={searchRef}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search snacks..."
          className="flex-1"
          onKeyDown={(e) => {
            if (e.key === 'Escape') onCancel();
          }}
        />
        <Button size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
      {!hideCategoryFilter && (
        <div className="p-2 border-b flex flex-wrap gap-1">
          {CATEGORY_FILTERS.map((cf) => (
            <Button
              key={cf.value}
              size="sm"
              variant={categoryFilter === cf.value ? 'default' : 'outline'}
              className="h-7 text-xs px-2"
              onClick={() => setCategoryFilter(cf.value)}
            >
              {cf.label}
            </Button>
          ))}
        </div>
      )}
      <div className="max-h-80 overflow-y-auto">
        {filtered.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">No snacks found.</p>
        )}
        {filtered.map((c) => (
          <button
            key={c.id}
            onClick={() => onAdd(c.id)}
            className="w-full text-left px-3 py-2 hover:bg-accent transition-colors flex items-center justify-between gap-4 border-b last:border-b-0"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-medium text-sm truncate">{c.ingredient_name}</span>
              {c.category && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                  {CATEGORY_LABELS[c.category] || c.category}
                </span>
              )}
            </div>
            {c.rating && <StarRating value={c.rating} readOnly size="xs" />}
            <span className="text-xs text-muted-foreground shrink-0 tabular-nums">
              {c.weight_per_serving} oz &middot; {c.calories_per_serving} cal &middot; {c.calories_per_oz} c/oz
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default SnackSelection;
