// The primary gauge on a structured trip: units filled against the trip's
// quota. Unlike ProgressMeter there is no band — a unit count is either short
// of the quota or it is complete.
function SnackUnitMeter({ label, filled, quota, secondary }) {
  const complete = quota > 0 && filled >= quota;
  const pct = quota > 0 ? Math.min((filled / quota) * 100, 100) : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground tabular-nums">
          {filled} of {quota}
          {complete && <span className="ml-1.5 text-green-600 dark:text-green-500">Complete</span>}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={`${label} filled`}
        aria-valuenow={filled}
        aria-valuemin={0}
        aria-valuemax={quota}
        className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden"
      >
        <div
          className={`h-full rounded-full transition-all ${complete ? 'bg-green-500' : 'bg-orange-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {secondary && (
        <div className="text-xs text-muted-foreground tabular-nums">{secondary}</div>
      )}
    </div>
  );
}

export default SnackUnitMeter;
