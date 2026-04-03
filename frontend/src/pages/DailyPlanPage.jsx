import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { get, post } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

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

function DailyPlanPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <p className="text-muted-foreground p-4">Loading...</p>;
  if (error) return <p className="text-destructive p-4">{error}</p>;
  if (!plan) return null;

  const hasAssignments = plan.days.some(d => d.items.length > 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-2xl font-semibold tracking-tight">Daily Plan</h2>
        <div className="flex gap-2">
          <Button onClick={handleAutoFill}>
            {hasAssignments ? 'Re-run Auto-Fill' : 'Auto-Fill'}
          </Button>
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

          // Group items by slot
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
                      {bySlot[slot].map((item) => (
                        <div key={item.id} className="flex items-center justify-between py-0.5">
                          <span>{item.name}{item.servings > 1 ? ` ×${item.servings}` : ''}</span>
                          <span className="text-xs text-muted-foreground ml-2">
                            {Math.round(item.calories)} cal
                          </span>
                        </div>
                      ))}
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
            <CardContent className="p-4">
              <div className="space-y-1 text-sm">
                {plan.unallocated.map((item, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span>
                      {item.name}
                      <Badge variant="outline" className="ml-2 text-xs">{item.category}</Badge>
                    </span>
                    <span className="text-muted-foreground">
                      {item.remaining_servings} serving{item.remaining_servings !== 1 ? 's' : ''} remaining
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default DailyPlanPage;
