import { useState, useEffect, useRef } from 'react';
import {
  get, post, put, del,
  listSnackUnitTypes, addTripSnackUnit, updateTripSnackUnit, removeTripSnackUnit,
} from '../api';
import { useTrip } from '../context/TripContext';
import { useMutation } from '../hooks/useMutation';
import ProgressMeter from './ProgressMeter';
import SnackUnitMeter from './SnackUnitMeter';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { StarRating } from '@/components/ui/star-rating';
import { Input } from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

const SLOTS = [
  { value: 'lunch', label: 'Lunch' },
  { value: 'snacks', label: 'Snacks' },
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
  lunch: new Set(['lunch']),
  snacks: new Set(['bars_energy', 'salty', 'sweet']),
};

function SnackSelection() {
  const { tripDetail, refreshTrip, summary } = useTrip();
  const [catalog, setCatalog] = useState([]);
  const [unitTypes, setUnitTypes] = useState([]);
  const [addingSlot, setAddingSlot] = useState(null); // which slot's add panel is open
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const searchRef = useRef(null);
  // Structured trips fill a unit quota; legacy trips steer by the calorie band.
  const structured = tripDetail?.snack_model === 'structured';

  useEffect(() => {
    get('/snacks').then(setCatalog).catch(() => {});
  }, []);

  useEffect(() => {
    if (!structured) return;
    listSnackUnitTypes().then(setUnitTypes).catch(() => {});
  }, [structured]);

  useEffect(() => {
    if (addingSlot && searchRef.current) searchRef.current.focus();
  }, [addingSlot]);

  const addMutation = useMutation(async (catalogId, slot) => {
    await post(`/trips/${tripDetail.id}/snacks`, {
      catalog_item_id: catalogId,
      servings: 1,
      slot,
    });
    setAddingSlot(null);
    setSearch('');
    setCategoryFilter('');
    refreshTrip();
  });

  const servingsMutation = useMutation(async (snackId, newServings) => {
    await put(`/trips/${tripDetail.id}/snacks/${snackId}`, {
      servings: newServings < 0 ? 0 : newServings,
    });
    refreshTrip();
  });

  const removeMutation = useMutation(async (snackId) => {
    await del(`/trips/${tripDetail.id}/snacks/${snackId}`);
    refreshTrip();
  });

  const notesMutation = useMutation(async (snackId, trip_notes) => {
    await put(`/trips/${tripDetail.id}/snacks/${snackId}`, { trip_notes: trip_notes || null });
    refreshTrip();
  });

  const slotMutation = useMutation(async (snackId, slot) => {
    await put(`/trips/${tripDetail.id}/snacks/${snackId}`, { slot });
    refreshTrip();
  });

  const addUnitMutation = useMutation(async (payload) => {
    await addTripSnackUnit(tripDetail.id, payload);
    setAddingSlot(null);
    setSearch('');
    refreshTrip();
  });

  const unitMutation = useMutation(async (unitId, data) => {
    await updateTripSnackUnit(tripDetail.id, unitId, data);
    refreshTrip();
  });

  const removeUnitMutation = useMutation(async (unitId) => {
    await removeTripSnackUnit(tripDetail.id, unitId);
    refreshTrip();
  });

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
    const key = s.slot || 'snacks';
    if (!bySlot[key]) bySlot[key] = [];
    bySlot[key].push(s);
  }

  const mutating = addMutation.pending || servingsMutation.pending
    || removeMutation.pending || notesMutation.pending || slotMutation.pending
    || addUnitMutation.pending || unitMutation.pending || removeUnitMutation.pending;
  const mutationError = addMutation.error || servingsMutation.error
    || removeMutation.error || notesMutation.error || slotMutation.error
    || addUnitMutation.error || unitMutation.error || removeUnitMutation.error;

  function handleAdd(catalogId, slot) {
    if (!catalogId) return;
    addMutation.run(catalogId, slot);
  }

  const updateServings = (snackId, newServings) => servingsMutation.run(snackId, newServings);
  const removeSnack = (snackId) => removeMutation.run(snackId);
  const updateNotes = (snackId, trip_notes) => notesMutation.run(snackId, trip_notes);
  const updateSlot = (snackId, slot) => slotMutation.run(snackId, slot);

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

  // A unit is one packaged catalog item or one library bag. Drink mixes and
  // lunch items keep their own sections, so they are not offered as units.
  const units = tripDetail.snack_units || [];
  const usedUnitTypeIds = new Set(units.map((u) => u.unit_type_id).filter(Boolean));
  const usedUnitItemIds = new Set(units.map((u) => u.catalog_item_id).filter(Boolean));
  const unitOptions = [
    ...unitTypes
      .filter((t) => !usedUnitTypeIds.has(t.id))
      .map((t) => ({
        key: `bag-${t.id}`,
        kind: 'bag',
        name: t.name,
        weight: t.weight_oz,
        calories: t.calories,
        payload: { unit_type_id: t.id },
      })),
    ...catalog
      .filter((c) => (
        c.category !== 'drink_mix' && c.category !== 'lunch' && !usedUnitItemIds.has(c.id)
      ))
      .map((c) => ({
        key: `packaged-${c.id}`,
        kind: 'packaged',
        name: c.ingredient_name,
        weight: c.weight_per_serving,
        calories: c.calories_per_serving,
        payload: { catalog_item_id: c.id },
      })),
  ].filter((o) => !search || o.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Snacks</CardTitle>
      </CardHeader>
      <CardContent className="pt-0 space-y-4">
        {mutationError && (
          <p className="text-destructive text-sm">{mutationError.message}</p>
        )}

        {/* Drink Mixes section */}
        <DrinkMixSection
          snacks={drinkMixes}
          tripDetail={tripDetail}
          summary={summary}
          mutating={mutating}
          isAdding={addingSlot === 'drink_mix'}
          onStartAdd={() => openAddPanel('drink_mix')}
          onCancelAdd={closeAddPanel}
          onAdd={(catalogId) => handleAdd(catalogId, 'snacks')}
          onRemove={removeSnack}
          onUpdateServings={updateServings}
          onUpdateNotes={updateNotes}
          search={search}
          setSearch={setSearch}
          categoryFilter={categoryFilter}
          setCategoryFilter={setCategoryFilter}
          filtered={filtered}
          searchRef={searchRef}
        />

        {SLOTS
          // On a structured trip the snacks slot is filled with units. Any
          // legacy rows still sitting in it stay visible and removable, but
          // nothing new is added there.
          .filter(({ value }) => (
            !structured || value !== 'snacks' || bySlot[value].length > 0
          ))
          .map(({ value: slotValue, label: slotLabel }) => (
            <SlotSection
              key={slotValue}
              slot={slotValue}
              label={slotLabel}
              snacks={bySlot[slotValue]}
              summary={summary}
              mutating={mutating}
              canAdd={!structured || slotValue !== 'snacks'}
              isAdding={addingSlot === slotValue}
              onStartAdd={() => openAddPanel(slotValue)}
              onCancelAdd={closeAddPanel}
              onAdd={(catalogId) => handleAdd(catalogId, slotValue)}
              onUpdateServings={updateServings}
              onUpdateNotes={updateNotes}
              onUpdateSlot={updateSlot}
              onRemove={removeSnack}
              search={search}
              setSearch={setSearch}
              categoryFilter={categoryFilter}
              setCategoryFilter={setCategoryFilter}
              filtered={filtered}
              searchRef={searchRef}
            />
          ))}

        {structured && (
          <SnackUnitSection
            units={units}
            options={unitOptions}
            summary={summary}
            mutating={mutating}
            isAdding={addingSlot === 'units'}
            onStartAdd={() => openAddPanel('units')}
            onCancelAdd={closeAddPanel}
            onAdd={(payload) => addUnitMutation.run(payload)}
            onUpdateQuantity={(unitId, quantity) => {
              if (quantity >= 1) unitMutation.run(unitId, { quantity });
            }}
            onUpdatePacked={(unitId, packed) => unitMutation.run(unitId, { packed })}
            onUpdateActualWeight={(unitId, weight) => unitMutation.run(unitId, {
              actual_weight_oz: weight ? parseFloat(weight) : null,
            })}
            onUpdateNotes={(unitId, trip_notes) => unitMutation.run(unitId, {
              trip_notes: trip_notes || null,
            })}
            onRemove={(unitId) => removeUnitMutation.run(unitId)}
            search={search}
            setSearch={setSearch}
            searchRef={searchRef}
          />
        )}
      </CardContent>
    </Card>
  );
}

function SnackUnitSection({
  units, options, summary, mutating, isAdding,
  onStartAdd, onCancelAdd, onAdd,
  onUpdateQuantity, onUpdatePacked, onUpdateActualWeight, onUpdateNotes, onRemove,
  search, setSearch, searchRef,
}) {
  const meter = summary?.snack_units;
  const subtotal = summary?.slot_subtotals?.snacks;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Snack Units
        </h3>
        {!isAdding && (
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onStartAdd}>
            + Add
          </Button>
        )}
      </div>

      {meter && (
        <div className="mb-2 p-2 rounded-md bg-muted/60">
          <SnackUnitMeter
            label="Units"
            filled={meter.filled}
            quota={meter.quota}
            secondary={[
              subtotal ? `${subtotal.weight} oz · ${subtotal.calories} cal` : null,
              meter.per_day?.length ? `${meter.per_day.join(' + ')} by day` : null,
            ].filter(Boolean).join(' · ')}
          />
        </div>
      )}

      {isAdding && (
        <UnitAddPanel
          options={options}
          onAdd={onAdd}
          onCancel={onCancelAdd}
          mutating={mutating}
          search={search}
          setSearch={setSearch}
          searchRef={searchRef}
        />
      )}

      {!isAdding && (
        <>
          {/* Desktop table */}
          <div className="hidden md:block">
            {units.length === 0 ? (
              <p className="text-muted-foreground text-xs py-2">No snack units yet.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Unit</TableHead>
                    <TableHead className="w-36">Units</TableHead>
                    <TableHead className="text-right">Wt</TableHead>
                    <TableHead className="text-right">Cal</TableHead>
                    <TableHead className="w-14">Packed</TableHead>
                    <TableHead className="text-right w-24">Actual</TableHead>
                    <TableHead>Notes</TableHead>
                    <TableHead className="w-10"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {units.map((u) => (
                    <TableRow key={u.id} className="even:bg-muted/50">
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <span>{u.name}</span>
                          <Badge variant="secondary" className="text-[10px]">
                            {u.kind === 'bag' ? 'Bag' : 'Packaged'}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="outline" size="icon" className="h-7 w-7"
                            aria-label={`Decrease ${u.name} units`}
                            disabled={mutating}
                            onClick={() => onUpdateQuantity(u.id, u.quantity - 1)}>-</Button>
                          <Input
                            type="number"
                            step="1"
                            min="1"
                            aria-label={`${u.name} units`}
                            disabled={mutating}
                            value={u.quantity}
                            onChange={(e) => {
                              const val = parseInt(e.target.value, 10);
                              if (!isNaN(val)) onUpdateQuantity(u.id, val);
                            }}
                            className="w-14 text-center h-7"
                          />
                          <Button variant="outline" size="icon" className="h-7 w-7"
                            aria-label={`Increase ${u.name} units`}
                            disabled={mutating}
                            onClick={() => onUpdateQuantity(u.id, u.quantity + 1)}>+</Button>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <span>{u.total_weight}</span>
                          {u.weight_warning && (
                            <Badge variant="destructive" className="text-[10px]"
                              title={`${u.weight_oz} oz is outside 25% of this trip's target`}>
                              Off target
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{u.total_calories}</TableCell>
                      <TableCell>
                        <Checkbox
                          checked={u.packed}
                          disabled={mutating}
                          aria-label={`${u.name} packed`}
                          onCheckedChange={(checked) => onUpdatePacked(u.id, checked)}
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <Input
                          type="number"
                          step="any"
                          aria-label={`${u.name} actual weight`}
                          disabled={mutating}
                          defaultValue={u.actual_weight_oz ?? ''}
                          onBlur={(e) => onUpdateActualWeight(u.id, e.target.value)}
                          className="w-20 h-7 ml-auto"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          defaultValue={u.trip_notes || ''}
                          aria-label={`${u.name} notes`}
                          disabled={mutating}
                          onBlur={(e) => onUpdateNotes(u.id, e.target.value)}
                          placeholder="notes..."
                          className="h-7 text-xs w-28"
                        />
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                          aria-label={`Remove ${u.name}`}
                          disabled={mutating}
                          onClick={() => onRemove(u.id)}>×</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          {/* Mobile card layout */}
          <div className="md:hidden space-y-2">
            {units.map((u) => (
              <div key={u.id} className="border rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-medium text-sm truncate">{u.name}</span>
                    {u.weight_warning && (
                      <Badge variant="destructive" className="text-[10px]">Off target</Badge>
                    )}
                  </div>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                    aria-label={`Remove ${u.name}`}
                    disabled={mutating}
                    onClick={() => onRemove(u.id)}>×</Button>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <Button variant="outline" size="icon" className="h-8 w-8"
                      aria-label={`Decrease ${u.name} units`}
                      disabled={mutating}
                      onClick={() => onUpdateQuantity(u.id, u.quantity - 1)}>-</Button>
                    <span className="w-10 text-center font-medium">{u.quantity}</span>
                    <Button variant="outline" size="icon" className="h-8 w-8"
                      aria-label={`Increase ${u.name} units`}
                      disabled={mutating}
                      onClick={() => onUpdateQuantity(u.id, u.quantity + 1)}>+</Button>
                  </div>
                  <div className="text-xs text-muted-foreground text-right">
                    {u.total_weight} oz &middot; {u.total_calories} cal
                  </div>
                </div>
                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Checkbox
                    checked={u.packed}
                    disabled={mutating}
                    aria-label={`${u.name} packed`}
                    onCheckedChange={(checked) => onUpdatePacked(u.id, checked)}
                  />
                  Packed
                </label>
              </div>
            ))}
            {units.length === 0 && (
              <p className="text-muted-foreground text-xs py-2">No snack units yet.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function UnitAddPanel({ options, onAdd, onCancel, mutating, search, setSearch, searchRef }) {
  return (
    <div className="mb-4 border rounded-lg bg-muted/30">
      <div className="p-3 border-b flex items-center gap-2">
        <Input
          ref={searchRef}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search bags and packaged snacks..."
          className="flex-1"
          onKeyDown={(e) => {
            if (e.key === 'Escape') onCancel();
          }}
        />
        <Button size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
      <div className="max-h-80 overflow-y-auto">
        {options.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">No units found.</p>
        )}
        {options.map((o) => (
          <button
            key={o.key}
            onClick={() => onAdd(o.payload)}
            disabled={mutating}
            aria-label={`Add ${o.name}`}
            className="w-full text-left px-3 py-2 hover:bg-accent transition-colors flex items-center justify-between gap-4 border-b last:border-b-0 disabled:opacity-50 disabled:pointer-events-none"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-medium text-sm truncate">{o.name}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                {o.kind === 'bag' ? 'Bag' : 'Packaged'}
              </span>
            </div>
            <span className="text-xs text-muted-foreground shrink-0 tabular-nums">
              {o.weight} oz &middot; {o.calories} cal
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function SlotMeters({ slot, summary }) {
  if (!summary) return null;
  const st = summary.slot_subtotals?.[slot];
  if (!st) return null;
  // A structured trip's snacks slot has no calorie band; the unit meter is its
  // gauge, so there is nothing to draw here.
  if (st.target_cal_low == null) return null;

  const slotPct = slot === 'lunch' ? 0.40 : 0.60;
  const remainingWeight = (summary.daytime_weight || 0) - (summary.drink_mix_weight || 0);
  const weightTarget = remainingWeight * slotPct;
  const weightLow = weightTarget * 0.9;
  const weightHigh = weightTarget * 1.1;

  return (
    <div className="mb-2 p-2 rounded-md bg-muted/60 grid grid-cols-1 sm:grid-cols-2 gap-2">
      <ProgressMeter label="Cal" actual={st.calories} targetLow={st.target_cal_low} targetHigh={st.target_cal_high} unit="cal" compact />
      <ProgressMeter label="Wt" actual={st.weight} targetLow={weightLow} targetHigh={weightHigh} unit="oz" compact />
    </div>
  );
}

function SlotSection({
  slot, label, snacks, summary, mutating, isAdding, canAdd = true,
  onStartAdd, onCancelAdd, onAdd,
  onUpdateServings, onUpdateNotes, onUpdateSlot, onRemove,
  search, setSearch, categoryFilter, setCategoryFilter,
  filtered, searchRef,
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">{label}</h3>
        {!isAdding && canAdd && (
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onStartAdd}>
            + Add
          </Button>
        )}
      </div>

      <SlotMeters slot={slot} summary={summary} />

      {isAdding && (
        <AddPanel
          slot={slot}
          onAdd={onAdd}
          onCancel={onCancelAdd}
          mutating={mutating}
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
                    <TableHead className="w-10"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {snacks.map((s) => (
                    <TableRow key={s.id} className="even:bg-muted/50">
                      <TableCell className="font-medium">{s.ingredient_name}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="outline" size="icon" className="h-7 w-7"
                            aria-label={`Decrease ${s.ingredient_name} servings`}
                            disabled={mutating}
                            onClick={() => onUpdateServings(s.id, s.servings - 1)}>-</Button>
                          <Input
                            type="number"
                            step="0.5"
                            aria-label={`${s.ingredient_name} servings`}
                            disabled={mutating}
                            value={s.servings}
                            onChange={(e) => {
                              const val = parseFloat(e.target.value);
                              if (!isNaN(val) && val >= 0) onUpdateServings(s.id, val);
                            }}
                            className="w-14 text-center h-7"
                          />
                          <Button variant="outline" size="icon" className="h-7 w-7"
                            aria-label={`Increase ${s.ingredient_name} servings`}
                            disabled={mutating}
                            onClick={() => onUpdateServings(s.id, s.servings + 1)}>+</Button>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{s.total_weight}</TableCell>
                      <TableCell className="text-right">{s.total_calories}</TableCell>
                      <TableCell className="text-right">{s.calories_per_oz}</TableCell>
                      <TableCell>
                        <Input
                          defaultValue={s.trip_notes || ''}
                          aria-label={`${s.ingredient_name} notes`}
                          disabled={mutating}
                          onBlur={(e) => onUpdateNotes(s.id, e.target.value)}
                          placeholder="notes..."
                          className="h-7 text-xs w-28"
                        />
                      </TableCell>
                      <TableCell>
                        <Select value={s.slot || slot} disabled={mutating} onValueChange={(v) => onUpdateSlot(s.id, v)}>
                          <SelectTrigger className="h-7 text-xs w-28" aria-label={`${s.ingredient_name} slot`}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {SLOTS.map((sl) => (
                              <SelectItem key={sl.value} value={sl.value}>{sl.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                          aria-label={`Remove ${s.ingredient_name}`}
                          disabled={mutating}
                          onClick={() => onRemove(s.id)}>×</Button>
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
                  <div className="flex items-center gap-1">
                    <Select value={s.slot || slot} disabled={mutating} onValueChange={(v) => onUpdateSlot(s.id, v)}>
                      <SelectTrigger className="h-7 text-xs w-28" aria-label={`${s.ingredient_name} slot`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SLOTS.map((sl) => (
                          <SelectItem key={sl.value} value={sl.value}>{sl.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                      aria-label={`Remove ${s.ingredient_name}`}
                      disabled={mutating}
                      onClick={() => onRemove(s.id)}>×</Button>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <Button variant="outline" size="icon" className="h-8 w-8"
                      aria-label={`Decrease ${s.ingredient_name} servings`}
                      disabled={mutating}
                      onClick={() => onUpdateServings(s.id, s.servings - 1)}>-</Button>
                    <span className="w-10 text-center font-medium">{s.servings}</span>
                    <Button variant="outline" size="icon" className="h-8 w-8"
                      aria-label={`Increase ${s.ingredient_name} servings`}
                      disabled={mutating}
                      onClick={() => onUpdateServings(s.id, s.servings + 1)}>+</Button>
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

function DrinkMixMeters({ snacks, summary, budget }) {
  if (!summary || snacks.length === 0 || budget <= 0) return null;

  const totalServings = snacks.reduce((sum, s) => sum + s.servings, 0);

  // Cal/weight targets from average per-serving × budget
  const avgCalPerServing = snacks.reduce((s, m) => s + (m.total_calories / m.servings), 0) / snacks.length;
  const avgWeightPerServing = snacks.reduce((s, m) => s + (m.total_weight / m.servings), 0) / snacks.length;
  const targetCal = avgCalPerServing * budget;
  const targetWeight = avgWeightPerServing * budget;

  return (
    <div className="mb-2 p-2 rounded-md bg-muted/60 grid grid-cols-1 sm:grid-cols-3 gap-2">
      <ProgressMeter label="Cal" actual={summary.drink_mix_calories} targetLow={targetCal * 0.9} targetHigh={targetCal * 1.1} unit="cal" compact />
      <ProgressMeter label="Wt" actual={summary.drink_mix_weight} targetLow={targetWeight * 0.9} targetHigh={targetWeight * 1.1} unit="oz" compact />
      <ProgressMeter label="Servings" actual={totalServings} targetLow={budget * 0.9} targetHigh={budget * 1.1} unit="srv" compact />
    </div>
  );
}

function DrinkMixSection({
  snacks, tripDetail, summary, mutating, isAdding, onStartAdd, onCancelAdd, onAdd, onRemove,
  onUpdateServings, onUpdateNotes,
  search, setSearch, categoryFilter, setCategoryFilter, filtered, searchRef,
}) {
  const mixesPerDay = tripDetail.drink_mixes_per_day || 2;
  const totalDays = (tripDetail.first_day_fraction || 0) + (tripDetail.full_days || 0) + (tripDetail.last_day_fraction || 0);
  const budget = mixesPerDay * totalDays;

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

      <DrinkMixMeters snacks={snacks} summary={summary} budget={budget} />

      {isAdding && (
        <AddPanel
          slot="drink_mix"
          onAdd={onAdd}
          onCancel={onCancelAdd}
          mutating={mutating}
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
                    <TableHead className="w-36">Servings</TableHead>
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
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="outline" size="icon" className="h-7 w-7"
                            aria-label={`Decrease ${s.ingredient_name} servings`}
                            disabled={mutating}
                            onClick={() => onUpdateServings(s.id, s.servings - 1)}>-</Button>
                          <span className="w-10 text-center font-medium">{s.servings}</span>
                          <Button variant="outline" size="icon" className="h-7 w-7"
                            aria-label={`Increase ${s.ingredient_name} servings`}
                            disabled={mutating}
                            onClick={() => onUpdateServings(s.id, s.servings + 1)}>+</Button>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{s.total_weight}</TableCell>
                      <TableCell className="text-right">{s.total_calories}</TableCell>
                      <TableCell>
                        <Input
                          defaultValue={s.trip_notes || ''}
                          aria-label={`${s.ingredient_name} notes`}
                          disabled={mutating}
                          onBlur={(e) => onUpdateNotes(s.id, e.target.value)}
                          placeholder="notes..."
                          className="h-7 text-xs w-28"
                        />
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                          aria-label={`Remove ${s.ingredient_name}`}
                          disabled={mutating}
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
              <div key={s.id} className="border rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{s.ingredient_name}</span>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                    aria-label={`Remove ${s.ingredient_name}`}
                    disabled={mutating}
                    onClick={() => onRemove(s.id)}>×</Button>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <Button variant="outline" size="icon" className="h-8 w-8"
                      aria-label={`Decrease ${s.ingredient_name} servings`}
                      disabled={mutating}
                      onClick={() => onUpdateServings(s.id, s.servings - 1)}>-</Button>
                    <span className="w-10 text-center font-medium">{s.servings}</span>
                    <Button variant="outline" size="icon" className="h-8 w-8"
                      aria-label={`Increase ${s.ingredient_name} servings`}
                      disabled={mutating}
                      onClick={() => onUpdateServings(s.id, s.servings + 1)}>+</Button>
                  </div>
                  <div className="text-xs text-muted-foreground text-right">
                    {s.total_weight} oz &middot; {s.total_calories} cal
                  </div>
                </div>
              </div>
            ))}
            {snacks.length === 0 && (
              <p className="text-muted-foreground text-xs py-2">No drink mixes added.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function AddPanel({ onAdd, onCancel, mutating, search, setSearch, categoryFilter, setCategoryFilter, filtered, searchRef, hideCategoryFilter }) {
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
            disabled={mutating}
            aria-label={`Add ${c.ingredient_name}`}
            className="w-full text-left px-3 py-2 hover:bg-accent transition-colors flex items-center justify-between gap-4 border-b last:border-b-0 disabled:opacity-50 disabled:pointer-events-none"
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
