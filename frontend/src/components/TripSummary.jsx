import { useState, useEffect } from 'react';
import { get } from '../api';
import { useTrip } from '../context/TripContext';

function TripSummary() {
  const { tripDetail } = useTrip();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!tripDetail) { setSummary(null); return; }
    get(`/trips/${tripDetail.id}/summary`).then(setSummary).catch(() => {});
  }, [tripDetail]);

  if (!summary) return null;

  function rangeStatus(actual, low, high) {
    if (actual >= low && actual <= high) return { color: 'green', label: 'in range' };
    return { color: '#cc8800', label: actual < low ? 'below' : 'above' };
  }

  const snackStatus = rangeStatus(summary.snack_weight, summary.daytime_weight_low, summary.daytime_weight_high);
  const totalStatus = rangeStatus(summary.combined_weight, summary.total_weight_low, summary.total_weight_high);

  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem' }}>
      <h3 style={{ marginTop: 0 }}>Summary</h3>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <tbody>
          <tr>
            <td style={labelStyle}>Snack weight</td>
            <td style={{ ...valStyle, color: snackStatus.color }}>
              {summary.snack_weight} oz ({(summary.snack_weight / 16).toFixed(1)} lbs)
              <small> — target {summary.daytime_weight_low.toFixed(1)}–{summary.daytime_weight_high.toFixed(1)} oz [{snackStatus.label}]</small>
            </td>
          </tr>
          <tr>
            <td style={labelStyle}>Snack calories</td>
            <td style={valStyle}>
              {summary.snack_calories.toLocaleString()}
              <small> — target {summary.daytime_cal_low.toLocaleString()}–{summary.daytime_cal_high.toLocaleString()}</small>
            </td>
          </tr>
          <tr>
            <td style={labelStyle}>Snack cal/oz</td>
            <td style={valStyle}>{summary.snack_cal_per_oz ?? '—'}</td>
          </tr>
          <tr style={{ borderTop: '1px solid #ccc' }}>
            <td style={labelStyle}>Meal weight</td>
            <td style={valStyle}>{summary.meal_weight_actual} oz ({(summary.meal_weight_actual / 16).toFixed(1)} lbs)</td>
          </tr>
          <tr>
            <td style={labelStyle}>Meal calories</td>
            <td style={valStyle}>{summary.meal_calories_actual.toLocaleString()}</td>
          </tr>
          <tr style={{ borderTop: '2px solid #ccc' }}>
            <td style={labelStyle}><strong>Combined weight</strong></td>
            <td style={{ ...valStyle, color: totalStatus.color }}>
              <strong>{summary.combined_weight} oz ({(summary.combined_weight / 16).toFixed(1)} lbs)</strong>
              <small> — target {summary.total_weight_low.toFixed(1)}–{summary.total_weight_high.toFixed(1)} oz [{totalStatus.label}]</small>
            </td>
          </tr>
          <tr>
            <td style={labelStyle}><strong>Combined calories</strong></td>
            <td style={valStyle}><strong>{summary.combined_calories.toLocaleString()}</strong></td>
          </tr>
          <tr style={{ borderTop: '1px solid #ccc' }}>
            <td style={labelStyle}>Per day</td>
            <td style={valStyle}>
              {summary.weight_per_day} oz/day | {summary.cal_per_day?.toLocaleString()} cal/day
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

const labelStyle = { padding: '4px 8px', whiteSpace: 'nowrap' };
const valStyle = { padding: '4px 8px' };

export default TripSummary;
