import { useState, useEffect } from 'react';
import { get } from '../api';
import { useTrip } from '../context/TripContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

function ProgressMeter({ label, actual, targetLow, targetHigh, unit }) {
  const mid = (targetLow + targetHigh) / 2;
  const pct = mid > 0 ? Math.min((actual / mid) * 100, 100) : 0;
  const deviation = mid > 0 ? Math.abs(actual - mid) / mid : 0;

  let color;
  if (deviation <= 0.05) color = 'bg-green-500';
  else if (deviation <= 0.10) color = 'bg-yellow-500';
  else if (deviation <= 0.20) color = 'bg-orange-500';
  else color = 'bg-red-500';

  const delta = actual - mid;
  let deltaText;
  if (Math.abs(delta) < 0.5) deltaText = 'on target';
  else if (delta > 0) deltaText = `+${Math.round(delta)} ${unit}`;
  else deltaText = `${Math.round(delta)} ${unit}`;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">{deltaText}</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-[10px] text-muted-foreground">
        {typeof actual === 'number' ? (unit === 'cal' ? actual.toLocaleString() : actual.toFixed(1)) : '\u2014'} / {unit === 'cal' ? mid.toLocaleString() : mid.toFixed(1)} {unit}
      </div>
    </div>
  );
}

function CategorySection({ title, weight, calories, count, totalDays, calPerOz }) {
  if (count === 0 && weight === 0) return null;

  // Target = (per-unit average) * totalDays
  const avgWeight = count > 0 ? weight / count : 0;
  const avgCal = count > 0 ? calories / count : 0;
  const targetWeight = avgWeight * totalDays;
  const targetCal = avgCal * totalDays;

  // Use +/- 10% for the range
  const weightLow = targetWeight * 0.9;
  const weightHigh = targetWeight * 1.1;
  const calLow = targetCal * 0.9;
  const calHigh = targetCal * 1.1;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{title}</h4>
      <ProgressMeter label="Calories" actual={calories} targetLow={calLow} targetHigh={calHigh} unit="cal" />
      <ProgressMeter label="Weight" actual={weight} targetLow={weightLow} targetHigh={weightHigh} unit="oz" />
    </div>
  );
}

function TripSummary() {
  const { tripDetail } = useTrip();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!tripDetail) { setSummary(null); return; }
    get(`/trips/${tripDetail.id}/summary`).then(setSummary).catch(() => {});
  }, [tripDetail]);

  if (!summary) return null;

  // Snack actuals: combine lunch + snacks slots, exclude drink mixes
  const snackActualWeight = Object.values(summary.slot_subtotals || {}).reduce((s, st) => s + st.weight, 0);
  const snackActualCal = Object.values(summary.slot_subtotals || {}).reduce((s, st) => s + st.calories, 0);

  // Snack targets: daytime targets minus drink mixes
  const snackTargetWeightLow = summary.daytime_weight_low - summary.drink_mix_weight;
  const snackTargetWeightHigh = summary.daytime_weight_high - summary.drink_mix_weight;
  const snackTargetCalLow = summary.daytime_cal_low - summary.drink_mix_calories;
  const snackTargetCalHigh = summary.daytime_cal_high - summary.drink_mix_calories;

  // Overall cal/oz
  const calPerOz = summary.combined_weight > 0
    ? Math.round(summary.combined_calories / summary.combined_weight)
    : null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {/* Breakfast */}
        <CategorySection
          title="Breakfast"
          weight={summary.breakfast_weight}
          calories={summary.breakfast_calories}
          count={summary.breakfast_count}
          totalDays={summary.total_days}
        />

        {/* Dinner */}
        <CategorySection
          title="Dinner"
          weight={summary.dinner_weight}
          calories={summary.dinner_calories}
          count={summary.dinner_count}
          totalDays={summary.total_days}
        />

        {/* Snacks */}
        {(snackActualWeight > 0 || snackActualCal > 0) && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Snacks</h4>
            <ProgressMeter
              label="Calories"
              actual={snackActualCal}
              targetLow={snackTargetCalLow}
              targetHigh={snackTargetCalHigh}
              unit="cal"
            />
            <ProgressMeter
              label="Weight"
              actual={snackActualWeight}
              targetLow={snackTargetWeightLow}
              targetHigh={snackTargetWeightHigh}
              unit="oz"
            />
          </div>
        )}

        {/* Drink mixes */}
        {summary.drink_mix_weight > 0 && (
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Drink mixes</span>
            <span>{summary.drink_mix_weight} oz / {summary.drink_mix_calories.toLocaleString()} cal</span>
          </div>
        )}

        <Separator className="border-t-2" />

        {/* Combined with progress bars */}
        <div className="space-y-2">
          <ProgressMeter
            label="Combined weight"
            actual={summary.combined_weight}
            targetLow={summary.total_weight_low}
            targetHigh={summary.total_weight_high}
            unit="oz"
          />
          <div className="text-xs text-muted-foreground ml-0.5">
            {(summary.combined_weight / 16).toFixed(1)} lbs
          </div>
        </div>

        <ProgressMeter
          label="Combined calories"
          actual={summary.combined_calories}
          targetLow={summary.total_cal_low}
          targetHigh={summary.total_cal_high}
          unit="cal"
        />

        {calPerOz != null && (
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Overall cal/oz</span>
            <span className="font-medium">{calPerOz}</span>
          </div>
        )}

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

export default TripSummary;
