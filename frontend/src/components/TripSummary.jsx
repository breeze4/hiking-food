import { useState } from 'react';
import { useTrip } from '../context/TripContext';
import ProgressMeter from './ProgressMeter';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

// Compute ±10% target range from per-unit average × days
function mealTargets(weight, calories, count, totalDays) {
  if (count === 0 && weight === 0) return null;
  const avgWeight = count > 0 ? weight / count : 0;
  const avgCal = count > 0 ? calories / count : 0;
  const tw = avgWeight * totalDays;
  const tc = avgCal * totalDays;
  return {
    calLow: tc * 0.9, calHigh: tc * 1.1,
    weightLow: tw * 0.9, weightHigh: tw * 1.1,
  };
}

function CategoryRow({ label, actualCal, calLow, calHigh, actualWeight, weightLow, weightHigh }) {
  return (
    <>
      {/* Desktop: single row with label + two bars side by side */}
      <div className="hidden sm:grid sm:grid-cols-[8rem_1fr_1fr] gap-3 items-center">
        <span className="text-xs font-medium">{label}</span>
        <ProgressMeter label="Cal" actual={actualCal} targetLow={calLow} targetHigh={calHigh} unit="cal" compact />
        <ProgressMeter label="Wt" actual={actualWeight} targetLow={weightLow} targetHigh={weightHigh} unit="oz" compact />
      </div>
      {/* Mobile: stacked */}
      <div className="sm:hidden space-y-1">
        <span className="text-xs font-medium">{label}</span>
        <ProgressMeter label="Cal" actual={actualCal} targetLow={calLow} targetHigh={calHigh} unit="cal" compact />
        <ProgressMeter label="Wt" actual={actualWeight} targetLow={weightLow} targetHigh={weightHigh} unit="oz" compact />
      </div>
    </>
  );
}

function TripSummary() {
  const { summary, tripDetail } = useTrip();
  const [categoryOpen, setCategoryOpen] = useState(false);

  if (!summary) return null;

  // Breakfast/dinner targets
  const bkf = mealTargets(summary.breakfast_weight, summary.breakfast_calories, summary.breakfast_count, summary.total_days);
  const din = mealTargets(summary.dinner_weight, summary.dinner_calories, summary.dinner_count, summary.total_days);

  // Slot targets (lunch/snacks) — cal from backend, weight computed with same percentage split
  const slotPcts = { lunch: 0.40, snacks: 0.60 };
  const remainingWeightLow = summary.daytime_weight_low - summary.drink_mix_weight;
  const remainingWeightHigh = summary.daytime_weight_high - summary.drink_mix_weight;

  const slotData = {};
  for (const slotName of ['lunch', 'snacks']) {
    const st = summary.slot_subtotals?.[slotName] || { weight: 0, calories: 0, target_cal_low: 0, target_cal_high: 0 };
    const pct = slotPcts[slotName];
    slotData[slotName] = {
      actualCal: st.calories,
      calLow: st.target_cal_low,
      calHigh: st.target_cal_high,
      actualWeight: st.weight,
      weightLow: remainingWeightLow * pct * 0.9,
      weightHigh: remainingWeightHigh * pct * 1.1,
    };
  }

  // Drink mix targets: average per-serving × budget
  const drinkMixes = (tripDetail?.snacks || []).filter(s => s.category === 'drink_mix');
  const mixesPerDay = tripDetail?.drink_mixes_per_day || 2;
  const budget = mixesPerDay * summary.total_days;
  let dmCalLow = 0, dmCalHigh = 0, dmWeightLow = 0, dmWeightHigh = 0;
  if (drinkMixes.length > 0 && budget > 0) {
    const avgCalPerServing = drinkMixes.reduce((s, m) => s + (m.total_calories / m.servings), 0) / drinkMixes.length;
    const avgWeightPerServing = drinkMixes.reduce((s, m) => s + (m.total_weight / m.servings), 0) / drinkMixes.length;
    const targetCal = avgCalPerServing * budget;
    const targetWeight = avgWeightPerServing * budget;
    dmCalLow = targetCal * 0.9; dmCalHigh = targetCal * 1.1;
    dmWeightLow = targetWeight * 0.9; dmWeightHigh = targetWeight * 1.1;
  }

  // Overall cal/oz
  const calPerOz = summary.combined_weight > 0
    ? Math.round(summary.combined_calories / summary.combined_weight)
    : null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {/* Combined totals */}
        <div className="space-y-2">
          <ProgressMeter
            label="Total calories"
            actual={summary.combined_calories}
            targetLow={summary.total_cal_low}
            targetHigh={summary.total_cal_high}
            unit="cal"
          />
          <ProgressMeter
            label="Total weight"
            actual={summary.combined_weight}
            targetLow={summary.total_weight_low}
            targetHigh={summary.total_weight_high}
            unit="oz"
          />
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>{(summary.combined_weight / 16).toFixed(1)} lbs</span>
            <span>{summary.weight_per_day} oz/day</span>
            <span>{summary.cal_per_day?.toLocaleString()} cal/day</span>
            {calPerOz != null && <span>{calPerOz} cal/oz</span>}
            <span>{summary.total_days} days</span>
          </div>
        </div>

        {/* Macro breakdown: actual vs target */}
        {summary.macro_actual && (
          <>
            <Separator />
            <div className="space-y-1">
              <div className="text-xs font-medium text-muted-foreground">Macronutrients</div>
              <div className="grid grid-cols-[auto_1fr_1fr_1fr] gap-x-3 gap-y-0.5 text-sm items-center">
                <span className="text-xs text-muted-foreground">Actual</span>
                <span>P {summary.macro_actual.protein_pct}%</span>
                <span>F {summary.macro_actual.fat_pct}%</span>
                <span>C {summary.macro_actual.carb_pct}%</span>
                {summary.macro_target && (
                  <>
                    <span className="text-xs text-muted-foreground">Target</span>
                    <span className="text-muted-foreground">P {summary.macro_target.protein_pct}%</span>
                    <span className="text-muted-foreground">F {summary.macro_target.fat_pct}%</span>
                    <span className="text-muted-foreground">C {summary.macro_target.carb_pct}%</span>
                  </>
                )}
              </div>
              <div className="flex gap-3 text-xs text-muted-foreground">
                <span>{summary.macro_actual.protein_g}g protein</span>
                <span>{summary.macro_actual.fat_g}g fat</span>
                <span>{summary.macro_actual.carb_g}g carb</span>
              </div>
              {summary.macro_coverage_pct != null && summary.macro_coverage_pct < 100 && (
                <div className="text-xs text-muted-foreground italic">
                  Based on {summary.macro_coverage_pct}% of calories
                </div>
              )}
            </div>
          </>
        )}

        <Separator />

        {/* Collapsible category grid */}
        <div>
          <button
            type="button"
            onClick={() => setCategoryOpen(o => !o)}
            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <svg
              width="12" height="12" viewBox="0 0 12 12"
              className={`transition-transform ${categoryOpen ? 'rotate-90' : ''}`}
            >
              <path d="M4 2 L9 6 L4 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Category Breakdown
          </button>

          {categoryOpen && (
            <div className="space-y-2 mt-2">
              {/* Grid header - desktop only */}
              <div className="hidden sm:grid sm:grid-cols-[8rem_1fr_1fr] gap-3 text-[10px] text-muted-foreground uppercase tracking-wide">
                <span></span>
                <span>Calories</span>
                <span>Weight</span>
              </div>

              {bkf && (
                <CategoryRow
                  label="Breakfast"
                  actualCal={summary.breakfast_calories} calLow={bkf.calLow} calHigh={bkf.calHigh}
                  actualWeight={summary.breakfast_weight} weightLow={bkf.weightLow} weightHigh={bkf.weightHigh}
                />
              )}
              {din && (
                <CategoryRow
                  label="Dinner"
                  actualCal={summary.dinner_calories} calLow={din.calLow} calHigh={din.calHigh}
                  actualWeight={summary.dinner_weight} weightLow={din.weightLow} weightHigh={din.weightHigh}
                />
              )}
              <CategoryRow
                label="Lunch"
                actualCal={slotData.lunch.actualCal} calLow={slotData.lunch.calLow} calHigh={slotData.lunch.calHigh}
                actualWeight={slotData.lunch.actualWeight} weightLow={slotData.lunch.weightLow} weightHigh={slotData.lunch.weightHigh}
              />
              <CategoryRow
                label="Snacks"
                actualCal={slotData.snacks.actualCal} calLow={slotData.snacks.calLow} calHigh={slotData.snacks.calHigh}
                actualWeight={slotData.snacks.actualWeight} weightLow={slotData.snacks.weightLow} weightHigh={slotData.snacks.weightHigh}
              />
              {(summary.drink_mix_weight > 0 || drinkMixes.length > 0) && (
                <CategoryRow
                  label="Drink Mixes"
                  actualCal={summary.drink_mix_calories} calLow={dmCalLow} calHigh={dmCalHigh}
                  actualWeight={summary.drink_mix_weight} weightLow={dmWeightLow} weightHigh={dmWeightHigh}
                />
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default TripSummary;
