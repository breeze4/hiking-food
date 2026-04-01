import { useState, useEffect } from 'react';
import { put } from '../api';
import { useTrip } from '../context/TripContext';

function TripCalculator() {
  const { tripDetail, refreshTrip } = useTrip();
  const [form, setForm] = useState({ first_day_fraction: 1, full_days: 0, last_day_fraction: 0 });

  useEffect(() => {
    if (tripDetail) {
      setForm({
        first_day_fraction: tripDetail.first_day_fraction ?? 1,
        full_days: tripDetail.full_days ?? 0,
        last_day_fraction: tripDetail.last_day_fraction ?? 0,
      });
    }
  }, [tripDetail?.id]);

  if (!tripDetail) return null;

  const totalDays = form.first_day_fraction + form.full_days + form.last_day_fraction;
  const weightLow = (totalDays * 19).toFixed(1);
  const weightHigh = (totalDays * 24).toFixed(1);
  const calLow = Math.round(totalDays * 19 * 125);
  const calHigh = Math.round(totalDays * 24 * 125);

  let saveTimer = null;
  function handleChange(field, value) {
    const updated = { ...form, [field]: value };
    setForm(updated);
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      await put(`/trips/${tripDetail.id}`, updated);
      refreshTrip();
    }, 500);
  }

  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem', marginBottom: '1rem' }}>
      <h3 style={{ marginTop: 0 }}>Trip Calculator</h3>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <label>
          First day
          <input
            type="number"
            min="0" max="1" step="0.25"
            value={form.first_day_fraction}
            onChange={(e) => handleChange('first_day_fraction', parseFloat(e.target.value) || 0)}
            style={{ display: 'block', width: '80px', padding: '4px' }}
          />
        </label>
        <label>
          Full days
          <input
            type="number"
            min="0" step="1"
            value={form.full_days}
            onChange={(e) => handleChange('full_days', parseInt(e.target.value) || 0)}
            style={{ display: 'block', width: '80px', padding: '4px' }}
          />
        </label>
        <label>
          Last day
          <input
            type="number"
            min="0" max="1" step="0.25"
            value={form.last_day_fraction}
            onChange={(e) => handleChange('last_day_fraction', parseFloat(e.target.value) || 0)}
            style={{ display: 'block', width: '80px', padding: '4px' }}
          />
        </label>
      </div>
      <div style={{ marginTop: '0.5rem' }}>
        <strong>Total days: {totalDays}</strong> |
        Recommended: {weightLow}–{weightHigh} oz |
        {calLow.toLocaleString()}–{calHigh.toLocaleString()} cal
      </div>
    </div>
  );
}

export default TripCalculator;
