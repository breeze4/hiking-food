import { useState, useEffect, useRef } from 'react';
import { put } from '../api';
import { useTrip } from '../context/TripContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

function TripCalculator() {
  const { tripDetail, refreshTrip } = useTrip();
  const [form, setForm] = useState({ first_day_fraction: 1, full_days: 0, last_day_fraction: 0, drink_mixes_per_day: 2, oz_per_day: 22, cal_per_oz: 125 });
  const [open, setOpen] = useState(true);
  const saveTimer = useRef(null);

  useEffect(() => {
    if (tripDetail) {
      setForm({
        first_day_fraction: tripDetail.first_day_fraction ?? 1,
        full_days: tripDetail.full_days ?? 0,
        last_day_fraction: tripDetail.last_day_fraction ?? 0,
        drink_mixes_per_day: tripDetail.drink_mixes_per_day ?? 2,
        oz_per_day: tripDetail.oz_per_day ?? 22,
        cal_per_oz: tripDetail.cal_per_oz ?? 125,
      });
    }
  }, [tripDetail?.id]);

  if (!tripDetail) return null;

  const totalDays = form.first_day_fraction + form.full_days + form.last_day_fraction;
  const totalWeight = (totalDays * form.oz_per_day).toFixed(1);
  const totalCal = Math.round(totalDays * form.oz_per_day * form.cal_per_oz);

  function handleChange(field, value) {
    const updated = { ...form, [field]: value };
    setForm(updated);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      await put(`/trips/${tripDetail.id}`, updated);
      refreshTrip();
    }, 500);
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Trip Calculator</CardTitle>
              <div className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground">
                  {totalDays} days &middot; {totalWeight} oz
                </span>
                <ChevronIcon open={open} />
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0">
            <div className="flex gap-4 flex-wrap">
              <div className="space-y-1">
                <Label htmlFor="first-day">First day</Label>
                <Input
                  id="first-day"
                  type="number"
                  min="0" max="1" step="0.25"
                  value={form.first_day_fraction}
                  onChange={(e) => handleChange('first_day_fraction', parseFloat(e.target.value) || 0)}
                  className="w-20"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="full-days">Full days</Label>
                <Input
                  id="full-days"
                  type="number"
                  min="0" step="1"
                  value={form.full_days}
                  onChange={(e) => handleChange('full_days', parseInt(e.target.value) || 0)}
                  className="w-20"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="last-day">Last day</Label>
                <Input
                  id="last-day"
                  type="number"
                  min="0" max="1" step="0.25"
                  value={form.last_day_fraction}
                  onChange={(e) => handleChange('last_day_fraction', parseFloat(e.target.value) || 0)}
                  className="w-20"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="drink-mixes">Mixes/day</Label>
                <Input
                  id="drink-mixes"
                  type="number"
                  min="0" step="1"
                  value={form.drink_mixes_per_day}
                  onChange={(e) => handleChange('drink_mixes_per_day', parseInt(e.target.value) || 0)}
                  className="w-20"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="oz-per-day">oz/day</Label>
                <Input
                  id="oz-per-day"
                  type="number"
                  min="0" step="0.5"
                  value={form.oz_per_day}
                  onChange={(e) => handleChange('oz_per_day', parseFloat(e.target.value) || 0)}
                  className="w-20"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="cal-per-oz">cal/oz</Label>
                <Input
                  id="cal-per-oz"
                  type="number"
                  min="0" step="1"
                  value={form.cal_per_oz}
                  onChange={(e) => handleChange('cal_per_oz', parseFloat(e.target.value) || 0)}
                  className="w-20"
                />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-3">
              <span className="font-medium text-foreground">Total days: {totalDays}</span>
              {' '}&middot; Target: {totalWeight} oz
              {' '}&middot; {totalCal.toLocaleString()} cal
            </p>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

function ChevronIcon({ open }) {
  return (
    <svg width="16" height="16" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"
      className={`transition-transform ${open ? 'rotate-180' : ''}`}>
      <path d="M3.13523 6.15803C3.3241 5.95657 3.64052 5.94637 3.84197 6.13523L7.5 9.56464L11.158 6.13523C11.3595 5.94637 11.6759 5.95657 11.8648 6.15803C12.0536 6.35949 12.0434 6.67591 11.842 6.86477L7.84197 10.6148C7.64964 10.7951 7.35036 10.7951 7.15803 10.6148L3.15803 6.86477C2.95657 6.67591 2.94637 6.35949 3.13523 6.15803Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd" />
    </svg>
  );
}

export default TripCalculator;
