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

// Category colors for the stacked bar chart
const CATEGORY_COLORS = {
  breakfast: '#3b82f6',      // blue
  dinner: '#8b5cf6',         // purple
  lunch: '#22c55e',          // green
  snacks: '#f59e0b',         // amber
  drink_mix: '#06b6d4',      // cyan
};

const CATEGORY_LABELS = {
  breakfast: 'Breakfast',
  dinner: 'Dinner',
  lunch: 'Lunch',
  snacks: 'Snacks',
  drink_mix: 'Drinks',
};

// Map slot to display category
function slotToCategory(slot) {
  if (slot === 'breakfast') return 'breakfast';
  if (slot === 'dinner') return 'dinner';
  if (slot === 'lunch') return 'lunch';
  if (slot === 'morning_snacks' || slot === 'afternoon_snacks') return 'snacks';
  return 'drink_mix';
}

function defaultSlotForItem(item) {
  if (item.source_type === 'meal') {
    return item.category === 'breakfast' ? 'breakfast' : 'dinner';
  }
  if (item.category === 'drink_mix') return 'all_day_drinks';
  if (item.category === 'lunch') return 'lunch';
  return 'afternoon_snacks';
}

// --- Stacked Bar Chart ---

function StackedBarChart({ days }) {
  if (!days.length) return null;

  const maxCal = Math.max(
    ...days.map(d => Math.max(
      d.items.reduce((s, i) => s + i.calories, 0),
      d.target_calories || 0
    ))
  ) * 1.1 || 1;

  const barWidth = Math.min(60, Math.floor(600 / days.length));
  const chartHeight = 180;
  const chartWidth = days.length * (barWidth + 12) + 20;
  const categories = ['breakfast', 'dinner', 'lunch', 'snacks', 'drink_mix'];

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <svg width={chartWidth} height={chartHeight + 40} className="block">
          {days.map((day, idx) => {
            const x = idx * (barWidth + 12) + 10;
            const target = day.target_calories || 0;

            // Sum calories per category
            const byCat = {};
            for (const cat of categories) byCat[cat] = 0;
            for (const item of day.items) {
              byCat[slotToCategory(item.slot)] += item.calories;
            }

            // Stack segments bottom-up
            let yOffset = chartHeight;
            const segments = [];
            for (const cat of categories) {
              const cal = byCat[cat];
              if (cal <= 0) continue;
              const h = (cal / maxCal) * chartHeight;
              yOffset -= h;
              segments.push({ cat, y: yOffset, h });
            }

            // Target line
            const targetY = chartHeight - (target / maxCal) * chartHeight;

            const typeLabel = DAY_TYPE_LABELS[day.day_type];
            const label = typeLabel ? `D${day.day_number}(½)` : `D${day.day_number}`;

            return (
              <g key={day.day_number}>
                {segments.map(({ cat, y, h }) => (
                  <rect
                    key={cat}
                    x={x}
                    y={y}
                    width={barWidth}
                    height={h}
                    fill={CATEGORY_COLORS[cat]}
                    rx={2}
                  />
                ))}
                {/* Target line */}
                <line
                  x1={x - 3}
                  y1={targetY}
                  x2={x + barWidth + 3}
                  y2={targetY}
                  stroke="currentColor"
                  strokeWidth={1.5}
                  strokeDasharray="4,2"
                  className="text-foreground/40"
                />
                {/* Day label */}
                <text
                  x={x + barWidth / 2}
                  y={chartHeight + 16}
                  textAnchor="middle"
                  className="fill-muted-foreground text-[10px]"
                >
                  {label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-xs">
        {categories.map(cat => (
          <div key={cat} className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: CATEGORY_COLORS[cat] }} />
            <span className="text-muted-foreground">{CATEGORY_LABELS[cat]}</span>
          </div>
        ))}
        <div className="flex items-center gap-1">
          <span className="inline-block w-4 border-t-2 border-dashed border-foreground/40" />
          <span className="text-muted-foreground">Target</span>
        </div>
      </div>
    </div>
  );
}

// --- Macro Bar ---

const MACRO_COLORS = {
  protein: '#ef4444',  // red
  fat: '#eab308',      // yellow
  carb: '#3b82f6',     // blue
};

function MacroBar({ macros, target }) {
  if (!macros) return null;

  const { protein_pct, fat_pct, carb_pct, protein_g, fat_g, carb_g, coverage_pct } = macros;

  return (
    <div className="mt-2 pt-2 border-t border-border/50 space-y-1">
      {/* Stacked percentage bar */}
      <div className="flex h-2 rounded-full overflow-hidden bg-muted">
        {protein_pct > 0 && (
          <div style={{ width: `${protein_pct}%`, backgroundColor: MACRO_COLORS.protein }} />
        )}
        {fat_pct > 0 && (
          <div style={{ width: `${fat_pct}%`, backgroundColor: MACRO_COLORS.fat }} />
        )}
        {carb_pct > 0 && (
          <div style={{ width: `${carb_pct}%`, backgroundColor: MACRO_COLORS.carb }} />
        )}
      </div>

      {/* Gram totals and percentages */}
      <div className="flex gap-3 text-[10px] text-muted-foreground">
        <span style={{ color: MACRO_COLORS.protein }}>
          P {protein_g}g ({protein_pct}%{target ? ` / ${target.protein_pct}%` : ''})
        </span>
        <span style={{ color: MACRO_COLORS.fat }}>
          F {fat_g}g ({fat_pct}%{target ? ` / ${target.fat_pct}%` : ''})
        </span>
        <span style={{ color: MACRO_COLORS.carb }}>
          C {carb_g}g ({carb_pct}%{target ? ` / ${target.carb_pct}%` : ''})
        </span>
      </div>

      {/* Coverage indicator */}
      {coverage_pct !== null && coverage_pct < 100 && (
        <p className="text-[10px] text-muted-foreground/70">
          Macro data covers {coverage_pct}% of calories
        </p>
      )}
    </div>
  );
}

// --- Main Page ---

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

  // Track last day each item appears (for "runs out" indicator)
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

      {/* Warnings */}
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

      {/* Stacked bar chart */}
      {hasAssignments && <StackedBarChart days={plan.days} />}

      {/* Unallocated summary banner */}
      {hasAssignments && plan.unallocated_summary?.count > 0 && (
        <p className="text-sm text-amber-600 dark:text-amber-400">
          {plan.unallocated_summary.count} item{plan.unallocated_summary.count !== 1 ? 's' : ''} unallocated ({plan.unallocated_summary.total_calories} cal · {plan.unallocated_summary.total_weight} oz)
        </p>
      )}
      {hasAssignments && plan.unallocated_summary?.count === 0 && (
        <p className="text-sm text-green-600/70 dark:text-green-400/70">All food allocated</p>
      )}

      {/* Day detail cards — responsive grid */}
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
                  <span className="text-xs text-muted-foreground">
                    {day.items.length > 0 && <>{Math.round(totalCal)} / {Math.round(day.target_calories)} cal</>}
                    {day.items.length > 0 && <> · {totalWeight.toFixed(1)} oz</>}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                {day.items.length === 0 ? (
                  <p className="text-muted-foreground text-xs">No items assigned</p>
                ) : (
                  <>
                    {SLOT_ORDER.filter(s => bySlot[s]).map(slot => (
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
                    ))}
                    <MacroBar macros={day.macros} target={plan.macro_target} />
                  </>
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
