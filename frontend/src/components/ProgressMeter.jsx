function ProgressMeter({ label, actual, targetLow, targetHigh, unit, compact = false }) {
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

  const formatVal = (v) => unit === 'cal' ? v.toLocaleString() : v.toFixed(1);
  const barHeight = compact ? 'h-1.5' : 'h-2';

  if (compact) {
    return (
      <div className="space-y-0.5">
        <div className="flex items-center justify-between text-[10px]">
          <span className="font-medium text-muted-foreground">{label}</span>
          <span className="text-muted-foreground tabular-nums">
            {typeof actual === 'number' ? formatVal(actual) : '\u2014'} / {formatVal(mid)} {unit}
          </span>
        </div>
        <div className={`${barHeight} bg-muted rounded-full overflow-hidden`}>
          <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">{deltaText}</span>
      </div>
      <div className={`${barHeight} bg-muted rounded-full overflow-hidden`}>
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-[10px] text-muted-foreground">
        {typeof actual === 'number' ? formatVal(actual) : '\u2014'} / {formatVal(mid)} {unit}
      </div>
    </div>
  );
}

export default ProgressMeter;
