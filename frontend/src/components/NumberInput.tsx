export function NumberInput({
  label,
  value,
  onChange,
  step = 1,
  suffix,
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  suffix?: string;
  min?: number;
  max?: number;
}) {
  return (
    <label className="block">
      <span className="text-xs text-slate-500">{label}</span>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={Number.isFinite(value) ? value : ""}
          step={step}
          min={min}
          max={max}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
        />
        {suffix && <span className="text-xs text-slate-400">{suffix}</span>}
      </div>
    </label>
  );
}

/** Percent-valued input: stores 0..1, displays 0..100. */
export function PercentInput({
  label,
  value,
  onChange,
  step = 0.5,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="block">
      <span className="text-xs text-slate-500">{label}</span>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={Number.isFinite(value) ? +(value * 100).toFixed(2) : ""}
          step={step}
          onChange={(e) => onChange(parseFloat(e.target.value) / 100)}
          className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
        />
        <span className="text-xs text-slate-400">%</span>
      </div>
    </label>
  );
}
