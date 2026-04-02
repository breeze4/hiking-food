import { useState, useEffect } from 'react';
import { get } from '../api';
import { useTrip } from '../context/TripContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

const SLOT_ORDER = [
  { value: 'morning_snack', label: 'Morning' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'afternoon_snack', label: 'Afternoon' },
];

function TripSummary() {
  const { tripDetail } = useTrip();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!tripDetail) { setSummary(null); return; }
    get(`/trips/${tripDetail.id}/summary`).then(setSummary).catch(() => {});
  }, [tripDetail]);

  if (!summary) return null;

  function rangeStatus(actual, low, high) {
    if (actual >= low && actual <= high) return { variant: 'success', label: 'in range' };
    return { variant: 'warning', label: actual < low ? 'below' : 'above' };
  }

  const snackStatus = rangeStatus(summary.snack_weight, summary.daytime_weight_low, summary.daytime_weight_high);
  const totalStatus = rangeStatus(summary.combined_weight, summary.total_weight_low, summary.total_weight_high);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {/* Snack totals */}
        <div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Snack weight</span>
            <StatusBadge status={snackStatus} />
          </div>
          <div className="font-medium">
            {summary.snack_weight} oz ({(summary.snack_weight / 16).toFixed(1)} lbs)
          </div>
          <div className="text-xs text-muted-foreground">
            target {summary.daytime_weight_low.toFixed(1)}&ndash;{summary.daytime_weight_high.toFixed(1)} oz
          </div>
        </div>

        <div className="flex justify-between">
          <span className="text-muted-foreground">Snack calories</span>
          <span className="font-medium">{summary.snack_calories.toLocaleString()}</span>
        </div>
        <div className="text-xs text-muted-foreground -mt-2">
          target {summary.daytime_cal_low.toLocaleString()}&ndash;{summary.daytime_cal_high.toLocaleString()}
        </div>

        <div className="flex justify-between">
          <span className="text-muted-foreground">Snack cal/oz</span>
          <span className="font-medium">{summary.snack_cal_per_oz ?? '\u2014'}</span>
        </div>

        {summary.slot_subtotals && Object.keys(summary.slot_subtotals).length > 0 && (
          <div className="space-y-1 pl-2 border-l-2 border-muted">
            {SLOT_ORDER.filter(s => summary.slot_subtotals[s.value]).map(({ value, label }) => {
              const st = summary.slot_subtotals[value];
              return (
                <div key={value} className="flex justify-between text-xs text-muted-foreground">
                  <span>{label}</span>
                  <span>{st.weight} oz / {st.calories.toLocaleString()} cal</span>
                </div>
              );
            })}
          </div>
        )}

        <Separator />

        {/* Meal totals */}
        <div className="flex justify-between">
          <span className="text-muted-foreground">Meal weight</span>
          <span className="font-medium">{summary.meal_weight_actual} oz ({(summary.meal_weight_actual / 16).toFixed(1)} lbs)</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Meal calories</span>
          <span className="font-medium">{summary.meal_calories_actual.toLocaleString()}</span>
        </div>

        <Separator className="border-t-2" />

        {/* Combined */}
        <div>
          <div className="flex items-center justify-between">
            <span className="font-semibold">Combined weight</span>
            <StatusBadge status={totalStatus} />
          </div>
          <div className="text-base font-bold">
            {summary.combined_weight} oz ({(summary.combined_weight / 16).toFixed(1)} lbs)
          </div>
          <div className="text-xs text-muted-foreground">
            target {summary.total_weight_low.toFixed(1)}&ndash;{summary.total_weight_high.toFixed(1)} oz
          </div>
        </div>

        <div className="flex justify-between">
          <span className="font-semibold">Combined calories</span>
          <span className="text-base font-bold">{summary.combined_calories.toLocaleString()}</span>
        </div>

        <Separator />

        <div className="flex justify-between">
          <span className="text-muted-foreground">Per day</span>
          <span className="font-medium">
            {summary.weight_per_day} oz &middot; {summary.cal_per_day?.toLocaleString()} cal
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }) {
  return (
    <Badge className={
      status.variant === 'success'
        ? 'bg-success text-success-foreground hover:bg-success'
        : 'bg-warning text-warning-foreground hover:bg-warning'
    }>
      {status.label}
    </Badge>
  );
}

export default TripSummary;
