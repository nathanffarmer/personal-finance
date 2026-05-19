import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { sheetsApi } from "@/api/sheets";
import { formatCurrency } from "@/api/monarch";
import { ApiError } from "@/api/client";

export default function Sheets() {
  const qc = useQueryClient();
  const status = useQuery({ queryKey: ["sheets", "status"], queryFn: sheetsApi.status });
  const assumptions = useQuery({
    queryKey: ["sheets", "assumptions"],
    queryFn: sheetsApi.assumptions,
    enabled: status.data?.authorized === true,
  });
  const targets = useQuery({
    queryKey: ["sheets", "targets"],
    queryFn: sheetsApi.targets,
    enabled: status.data?.authorized === true,
  });

  const pushAccounts = useMutation({
    mutationFn: sheetsApi.pushAccounts,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sheets", "status"] }),
  });
  const pushHoldings = useMutation({
    mutationFn: sheetsApi.pushHoldings,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sheets", "status"] }),
  });

  const errMsg = (e: unknown) =>
    e instanceof ApiError && typeof e.body === "object" && e.body && "detail" in e.body
      ? String((e.body as { detail: unknown }).detail)
      : e instanceof Error
        ? e.message
        : String(e);

  return (
    <div className="max-w-4xl">
      <h2 className="text-2xl font-semibold mb-4">Sheets</h2>

      <section className="mb-6 rounded border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-2">Status</h3>
        {status.isLoading && <div className="text-sm text-slate-500">Checking…</div>}
        {status.data && (
          <dl className="text-sm grid grid-cols-2 gap-y-1 max-w-md">
            <dt className="text-slate-500">Authorized</dt>
            <dd>{status.data.authorized ? "Yes" : "No"}</dd>
            <dt className="text-slate-500">Sheet ID</dt>
            <dd className="font-mono text-xs break-all">
              {status.data.sheet_id || "(not set)"}
            </dd>
            <dt className="text-slate-500">Last write</dt>
            <dd>{status.data.last_write_at || "—"}</dd>
            {status.data.error && (
              <>
                <dt className="text-slate-500">Error</dt>
                <dd className="text-amber-700">{status.data.error}</dd>
              </>
            )}
          </dl>
        )}
      </section>

      <section className="mb-6 rounded border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-2">Push snapshots</h3>
        <div className="flex gap-3">
          <button
            disabled={pushAccounts.isPending}
            onClick={() => pushAccounts.mutate()}
            className="px-3 py-2 text-sm rounded bg-ink text-white disabled:opacity-40"
          >
            {pushAccounts.isPending ? "Pushing…" : "Push accounts"}
          </button>
          <button
            disabled={pushHoldings.isPending}
            onClick={() => pushHoldings.mutate()}
            className="px-3 py-2 text-sm rounded bg-ink text-white disabled:opacity-40"
          >
            {pushHoldings.isPending ? "Pushing…" : "Push holdings"}
          </button>
        </div>
        {pushAccounts.isSuccess && (
          <p className="mt-2 text-sm text-emerald-700">
            Wrote {pushAccounts.data.written_rows} rows to {pushAccounts.data.range}.
          </p>
        )}
        {pushHoldings.isSuccess && (
          <p className="mt-2 text-sm text-emerald-700">
            Wrote {pushHoldings.data.written_rows} rows to {pushHoldings.data.range}.
          </p>
        )}
        {pushAccounts.error && (
          <p className="mt-2 text-sm text-amber-700">{errMsg(pushAccounts.error)}</p>
        )}
        {pushHoldings.error && (
          <p className="mt-2 text-sm text-amber-700">{errMsg(pushHoldings.error)}</p>
        )}
      </section>

      <section className="mb-6 rounded border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-2">Assumptions (read)</h3>
        {assumptions.data ? (
          <dl className="text-sm grid grid-cols-2 gap-y-1 max-w-md">
            <dt className="text-slate-500">Current age</dt>
            <dd>{assumptions.data.current_age ?? "—"}</dd>
            <dt className="text-slate-500">Retirement age</dt>
            <dd>{assumptions.data.retirement_age ?? "—"}</dd>
            <dt className="text-slate-500">End age</dt>
            <dd>{assumptions.data.end_age ?? "—"}</dd>
            <dt className="text-slate-500">Annual spend (real)</dt>
            <dd>
              {assumptions.data.annual_spend_real != null
                ? formatCurrency(assumptions.data.annual_spend_real)
                : "—"}
            </dd>
            <dt className="text-slate-500">Annual contributions</dt>
            <dd>
              {assumptions.data.annual_contributions != null
                ? formatCurrency(assumptions.data.annual_contributions)
                : "—"}
            </dd>
            <dt className="text-slate-500">SWR</dt>
            <dd>
              {assumptions.data.swr != null
                ? `${(assumptions.data.swr * 100).toFixed(2)}%`
                : "—"}
            </dd>
            <dt className="text-slate-500">Withdrawal strategy</dt>
            <dd>{assumptions.data.withdrawal_kind ?? "—"}</dd>
            <dt className="text-slate-500">Glide path</dt>
            <dd>{assumptions.data.glide_kind ?? "—"}</dd>
          </dl>
        ) : (
          <p className="text-sm text-slate-500">
            {status.data?.authorized
              ? "Loading…"
              : "Authorize Google OAuth and set SHEET_ID to enable."}
          </p>
        )}
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-2">Targets</h3>
        {targets.data && targets.data.length > 0 ? (
          <table className="text-sm w-full">
            <thead>
              <tr className="text-left">
                <th className="px-2 py-1">Age</th>
                <th className="px-2 py-1 text-right">Target net worth</th>
              </tr>
            </thead>
            <tbody>
              {targets.data.map((t) => (
                <tr key={t.age} className="border-t border-slate-100">
                  <td className="px-2 py-1">{t.age}</td>
                  <td className="px-2 py-1 text-right">
                    {formatCurrency(t.target_net_worth)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-slate-500">No targets table found.</p>
        )}
      </section>
    </div>
  );
}
