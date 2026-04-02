import { useState, useEffect, useRef } from 'react';
import { get, post, put, del } from '../api';
import { useTrip } from '../context/TripContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

function SortHead({ col, label, sortCol, sortAsc, onClick, className = '' }) {
  const arrow = sortCol === col ? (sortAsc ? ' \u25B2' : ' \u25BC') : '';
  return (
    <TableHead className={`cursor-pointer select-none ${className}`} onClick={() => onClick(col)}>
      {label}{arrow}
    </TableHead>
  );
}

function SnackSelection() {
  const { tripDetail, refreshTrip } = useTrip();
  const [catalog, setCatalog] = useState([]);
  const [adding, setAdding] = useState(false);
  const [search, setSearch] = useState('');
  const [sortCol, setSortCol] = useState(null);
  const [sortAsc, setSortAsc] = useState(true);
  const searchRef = useRef(null);

  useEffect(() => {
    get('/snacks').then(setCatalog).catch(() => {});
  }, []);

  useEffect(() => {
    if (adding && searchRef.current) searchRef.current.focus();
  }, [adding]);

  if (!tripDetail) return null;

  const snacks = tripDetail.snacks || [];

  function handleSort(col) {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(true); }
  }

  function getSorted() {
    const list = [...snacks];
    if (!sortCol) {
      // Default: newest first
      list.reverse();
      return list;
    }
    return list.sort((a, b) => {
      let aVal = a[sortCol], bVal = b[sortCol];
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';
      if (typeof aVal === 'number' && typeof bVal === 'number')
        return sortAsc ? aVal - bVal : bVal - aVal;
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortAsc ? cmp : -cmp;
    });
  }

  const sorted = getSorted();

  async function handleAdd(catalogId) {
    if (!catalogId) return;
    await post(`/trips/${tripDetail.id}/snacks`, {
      catalog_item_id: catalogId,
      servings: 1,
    });
    setAdding(false);
    setSearch('');
    // Reset sort so new item appears at top
    setSortCol(null);
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
  const filtered = search
    ? available.filter((c) => c.ingredient_name.toLowerCase().includes(search.toLowerCase()))
    : available;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Snacks</CardTitle>
          {!adding && (
            <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
              + Add snack
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Inline search panel */}
        {adding && (
          <div className="mb-4 border rounded-lg bg-muted/30">
            <div className="p-3 border-b flex items-center gap-2">
              <Input
                ref={searchRef}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search snacks..."
                className="flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Escape') { setAdding(false); setSearch(''); }
                }}
              />
              <Button size="sm" variant="ghost" onClick={() => { setAdding(false); setSearch(''); }}>
                Cancel
              </Button>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {filtered.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">No snacks found.</p>
              )}
              {filtered.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleAdd(c.id)}
                  className="w-full text-left px-3 py-2 hover:bg-accent transition-colors flex items-center justify-between gap-4 border-b last:border-b-0"
                >
                  <span className="font-medium text-sm">{c.ingredient_name}</span>
                  <span className="text-xs text-muted-foreground shrink-0 tabular-nums">
                    {c.weight_per_serving} oz &middot; {c.calories_per_serving} cal &middot; {c.calories_per_oz} c/oz
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Desktop table */}
        {!adding && (
          <div className="hidden md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <SortHead col="ingredient_name" label="Name" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} />
                  <TableHead className="w-36">Servings</TableHead>
                  <SortHead col="total_weight" label="Wt" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} className="text-right" />
                  <SortHead col="total_calories" label="Cal" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} className="text-right" />
                  <SortHead col="calories_per_oz" label="Cal/oz" sortCol={sortCol} sortAsc={sortAsc} onClick={handleSort} className="text-right" />
                  <TableHead>Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((s) => (
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
        )}

        {/* Mobile card layout */}
        {!adding && (
          <div className="md:hidden space-y-2">
            {sorted.map((s) => (
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
        )}
      </CardContent>
    </Card>
  );
}

export default SnackSelection;
