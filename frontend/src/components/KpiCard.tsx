import { formatCurrency } from "@/api/monarch";

export function KpiCard({ label, value }: { label: string; value: number }) {
  const negative = value < 0;
  return (
    <div className="rounded border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div
        className={`mt-1 text-2xl font-semibold ${negative ? "text-rose-600" : "text-ink"}`}
      >
        {formatCurrency(value)}
      </div>
    </div>
  );
}
