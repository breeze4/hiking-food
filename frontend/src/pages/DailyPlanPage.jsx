import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { get, post, del, patch } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';

const SLOT_ORDER = [
  'breakfast', 'breakfast_drinks', 'morning_snacks',
  'lunch', 'afternoon_snacks',
  'dinner', 'evening_drinks', 'all_day_drinks',
];

const SLOT_LABELS = {
  breakfast: 'Breakfast',
  breakfast_drinks: 'Breakfast Drinks',
  morning_snacks: 'Morning Snacks',
  lunch: 'Lunch',
  afternoon_snacks: 'Afternoon Snacks',
  dinner: 'Dinner',
  evening_drinks: 'Evening Drinks',
  all_day_drinks: 'All-Day Drinks',
};

const DAY_TYPE_LABELS = {
  first_partial: 'half',
  last_partial: 'half',
  full: null,
};

// Map source categories to default slots for adding from pool
function defaultSlotForItem(item) {
  if (item.source_type === 'meal') {
    return item.category === 'breakfast' ? 'breakfast' : 'dinner';
  }
  if (item.category === 'drink_mix') return 'all_day_drinks';
  if (item.category === 'lunch') return 'lunch';
  return 'afternoon_snacks';
}

function DailyPlanPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resetOpen, setResetOpen] = useState(false);

  useEffect(() => { loadPlan(); }, [tripId]);

  async function loadPlan() {
    try {
      setPlan(await get(`/trips/${tripId}/daily-plan`));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAutoFill() {
    try {
      setPlan(await post(`/trips/${tripId}/daily-plan/auto-fill`));
      setError(null);
      setResetOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeAssignment(assignmentId) {
    try {
      setPlan(await del(`/trips/${tripId}/daily-plan/assignments/${assignmentId}`));
    } catch (err) { setError(err.message); }
  }

  async function incrementServings(assignmentId, currentServings) {
    try {
      setPlan(await patch(`/trips/${tripId}/daily-plan/assignments/${assignmentId}`, {
        servings: currentServings + 1,
      }));
    } catch (err) { setError(err.message); }
  }

  async function addToDay(item, dayNumber) {
    try {
      setPlan(await post(`/trips/${tripId}/daily-plan/assignments`, {
        day_number: dayNumber,
        slot: defaultSlotForItem(item),
        source_type: item.source_type,
        source_id: item.source_id,
        servings: 1,
      }));
    } catch (err) { setError(err.message); }
  }

  if (loading) return <p className="text-muted-foreground p-4">Loading...</p>;
  if (error) return <p className="text-destructive p-4">{error}</p>;
  if (!plan) return null;

  const hasAssignments = plan.days.some(d => d.items.length > 0);
  const totalDays = plan.days.length;

  // Track which items run out: find last day each item appears
  const lastDayBySource = {};
  for (const day of plan.days) {
    for (const item of day.items) {
      const key = `${item.source_type}:${item.source_id}`;
      lastDayBySource[key] = day.day_number;
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-2xl font-semibold tracking-tight">Daily Plan</h2>
        <div className="flex gap-2">
          {hasAssignments ? (
            <Button variant="outline" onClick={() => setResetOpen(true)}>
              Reset Auto-Fill
            </Button>
          ) : (
            <Button onClick={handleAutoFill}>Auto-Fill</Button>
          )}
          <Button variant="outline" onClick={() => navigate('/')}>Back to Planner</Button>
        </div>
      </div>

      {plan.warnings.length > 0 && (
        <div className="space-y-1">
          {plan.warnings.map((w, i) => (
            <p key={i} className="text-sm text-orange-600 dark:text-orange-400">{w}</p>
          ))}
        </div>
      )}

      {!hasAssignments && (
        <p className="text-muted-foreground">No assignments yet. Click Auto-Fill to distribute food across days.</p>
      )}

      {/* Day cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {plan.days.map((day) => {
          const typeLabel = DAY_TYPE_LABELS[day.day_type];
          const dayLabel = `Day ${day.day_number}${typeLabel ? ` (${typeLabel})` : ''}`;
          const totalCal = day.items.reduce((s, i) => s + i.calories, 0);
          const totalWeight = day.items.reduce((s, i) => s + i.weight, 0);

          const bySlot = {};
          for (const item of day.items) {
            if (!bySlot[item.slot]) bySlot[item.slot] = [];
            bySlot[item.slot].push(item);
          }

          return (
            <Card key={day.day_number}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{dayLabel}</CardTitle>
                  {day.items.length > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {Math.round(totalCal)} cal · {totalWeight.toFixed(1)} oz
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                {day.items.length === 0 ? (
                  <p className="text-muted-foreground text-xs">No items assigned</p>
                ) : (
                  SLOT_ORDER.filter(s => bySlot[s]).map(slot => (
                    <div key={slot}>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-0.5">
                        {SLOT_LABELS[slot]}
                      </p>
                      {bySlot[slot].map((item) => {
                        const key = `${item.source_type}:${item.source_id}`;
                        const runsOut = lastDayBySource[key];
                        const showRunsOut = item.source_type === 'snack' && runsOut && runsOut < totalDays && runsOut === day.day_number;

                        return (
                          <div key={item.id} className="flex items-center gap-1 py-0.5 group">
                            <span className="flex-1">
                              {item.name}{item.servings > 1 ? ` ×${item.servings}` : ''}
                              {showRunsOut && (
                                <span className="text-xs text-orange-500 ml-1">(last day)</span>
                              )}
                            </span>
                            <span className="text-xs text-muted-foreground mr-1">
                              {Math.round(item.calories)} cal
                            </span>
                            {item.source_type === 'snack' && (
                              <button
                                onClick={() => incrementServings(item.id, item.servings)}
                                className="text-xs px-1 rounded hover:bg-muted opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Add serving"
                              >+</button>
                            )}
                            <button
                              onClick={() => removeAssignment(item.id)}
                              className="text-xs px-1 rounded hover:bg-destructive/10 text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                              title="Remove"
                            >×</button>
                          </div>
                        );
                      })}
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Unallocated Pool */}
      {plan.unallocated.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-3">Unallocated</h3>
          <Card>
            <CardContent className="p-4 space-y-3">
              {plan.unallocated.map((item, i) => (
                <div key={i}>
                  <div className="flex items-center gap-2 text-sm mb-1">
                    <span className="font-medium">{item.name}</span>
                    <Badge variant="outline" className="text-xs">{item.category}</Badge>
                    <span className="text-muted-foreground text-xs">
                      {item.remaining_servings} serving{item.remaining_servings !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {plan.days.map((day) => (
                      <Button
                        key={day.day_number}
                        size="sm"
                        variant="outline"
                        className="h-6 w-8 text-xs px-0"
                        onClick={() => addToDay(item, day.day_number)}
                      >
                        {day.day_number}
                      </Button>
                    ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Reset confirmation dialog */}
      <Dialog open={resetOpen} onOpenChange={setResetOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset to Auto-Fill?</DialogTitle>
            <DialogDescription>
              This will clear all manual edits and re-run the auto-fill algorithm.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetOpen(false)}>Cancel</Button>
            <Button onClick={handleAutoFill}>Reset</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default DailyPlanPage;
