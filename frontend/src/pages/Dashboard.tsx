import { useQuery, useQueryClient } from "@tanstack/react-query";
import { monarchApi } from "@/api/monarch";
import { ApiError } from "@/api/client";
import { KpiCard } from "@/components/KpiCard";
import { AccountTable } from "@/components/AccountTable";

export default function Dashboard() {
  const qc = useQueryClient();
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: monarchApi.accounts });
  const netWorth = useQuery({ queryKey: ["net_worth"], queryFn: monarchApi.netWorth });

  const refresh = async () => {
    await monarchApi.clearCache();
    await qc.invalidateQueries({ queryKey: ["accounts"] });
    await qc.invalidateQueries({ queryKey: ["net_worth"] });
  };

  const error = accounts.error ?? netWorth.error;

  return (
    <div className="max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <button
          onClick={refresh}
          className="px-3 py-1.5 text-sm rounded border border-slate-300 hover:bg-slate-50"
        >
          Refresh
        </button>
      </div>

      {error && <ErrorBanner error={error} />}

      {netWorth.data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <KpiCard label="Net worth" value={netWorth.data.total} />
          <KpiCard
            label="Liquid (cash)"
            value={netWorth.data.by_type.cash}
          />
          <KpiCard label="Investments" value={netWorth.data.by_type.investment} />
          <KpiCard
            label="Debt"
            value={netWorth.data.by_type.credit + netWorth.data.by_type.loan}
          />
        </div>
      )}

      {accounts.isLoading && <div className="text-sm text-slate-500">Loading accounts…</div>}
      {accounts.data && <AccountTable accounts={accounts.data} />}
    </div>
  );
}

function ErrorBanner({ error }: { error: Error }) {
  let detail = error.message;
  if (error instanceof ApiError && error.body && typeof error.body === "object") {
    const body = error.body as { detail?: string };
    if (body.detail) detail = body.detail;
  }
  return (
    <div className="mb-4 rounded border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      {detail}
    </div>
  );
}
