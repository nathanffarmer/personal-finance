import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  FireNumbers,
  MonteCarloResult,
  ScenarioInput,
  defaultScenario,
  retirementApi,
} from "@/api/retirement";
import { formatCurrency } from "@/api/monarch";
import { sheetsApi } from "@/api/sheets";
import { ApiError } from "@/api/client";
import { ScenarioForm } from "@/components/ScenarioForm";
import { ProjectionChart } from "@/components/ProjectionChart";
import { FanChart } from "@/components/FanChart";
import { SuccessGauge } from "@/components/SuccessGauge";
import { KpiCard } from "@/components/KpiCard";

type Tab = "deterministic" | "monte_carlo" | "fire";

function errMsg(e: unknown): string {
  if (e instanceof ApiError && e.body && typeof e.body === "object" && "detail" in e.body) {
    return String((e.body as { detail: unknown }).detail);
  }
  return e instanceof Error ? e.message : String(e);
}

export default function Retirement() {
  const [scenario, setScenario] = useState<ScenarioInput>(defaultScenario());
  const [tab, setTab] = useState<Tab>("monte_carlo");
  const [trials, setTrials] = useState(10000);
  const [method, setMethod] = useState<"bootstrap" | "lognormal">("bootstrap");
  const [includeCash, setIncludeCash] = useState(true);

  const deterministic = useMutation({
    mutationFn: () => retirementApi.deterministic(scenario),
  });
  const monteCarlo = useMutation({
    mutationFn: () => retirementApi.monteCarlo(scenario, { trials, method }),
  });
  const fire = useMutation({
    mutationFn: () =>
      retirementApi.fire({
        annual_spend: scenario.annual_spend_real,
        current_age: scenario.current_age,
        target_age: scenario.retirement_age,
        swr: 0.04,
        real_return: scenario.return_assumptions.equity_mean,
        lean_factor: 0.6,
        fat_factor: 2.0,
      }),
  });
  const loadMonarch = useMutation({
    mutationFn: () => retirementApi.fromMonarch(scenario, includeCash),
    onSuccess: (s) => setScenario(s),
  });
  const loadSheets = useMutation({
    mutationFn: () => sheetsApi.assumptions(),
    onSuccess: (a) => {
      setScenario((prev) => ({
        ...prev,
        current_age: a.current_age ?? prev.current_age,
        retirement_age: a.retirement_age ?? prev.retirement_age,
        end_age: a.end_age ?? prev.end_age,
        annual_spend_real: a.annual_spend_real ?? prev.annual_spend_real,
        annual_contributions: a.annual_contributions ?? prev.annual_contributions,
      }));
    },
  });
  const pushProjection = useMutation({
    mutationFn: (result: MonteCarloResult) => sheetsApi.pushProjection(result),
  });

  const runActive = () => {
    if (tab === "deterministic") deterministic.mutate();
    else if (tab === "monte_carlo") monteCarlo.mutate();
    else fire.mutate();
  };

  return (
    <div className="max-w-6xl">
      <h2 className="text-2xl font-semibold mb-4">Retirement</h2>
      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">
        {/* Left: scenario form */}
        <div className="rounded border border-slate-200 bg-white p-4">
          <div className="flex gap-2 mb-3">
            <button
              onClick={() => loadMonarch.mutate()}
              disabled={loadMonarch.isPending}
              className="flex-1 text-xs px-2 py-1.5 border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-40"
            >
              {loadMonarch.isPending ? "Loading…" : "Load from Monarch"}
            </button>
            <button
              onClick={() => loadSheets.mutate()}
              disabled={loadSheets.isPending}
              className="flex-1 text-xs px-2 py-1.5 border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-40"
            >
              {loadSheets.isPending ? "Loading…" : "Load from Sheets"}
            </button>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-500 mb-3">
            <input
              type="checkbox"
              checked={includeCash}
              onChange={(e) => setIncludeCash(e.target.checked)}
            />
            Include checking/savings balances in portfolio
          </label>
          {loadMonarch.error && (
            <p className="text-xs text-amber-700 mb-2">{errMsg(loadMonarch.error)}</p>
          )}
          {loadSheets.error && (
            <p className="text-xs text-amber-700 mb-2">{errMsg(loadSheets.error)}</p>
          )}
          <ScenarioForm scenario={scenario} onChange={setScenario} />
        </div>

        {/* Right: results */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex gap-1">
              {(["deterministic", "monte_carlo", "fire"] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-3 py-1.5 text-sm rounded ${
                    tab === t ? "bg-ink text-white" : "hover:bg-slate-100"
                  }`}
                >
                  {t === "deterministic"
                    ? "Deterministic"
                    : t === "monte_carlo"
                      ? "Monte Carlo"
                      : "FIRE numbers"}
                </button>
              ))}
            </div>
            <button
              onClick={runActive}
              className="px-4 py-1.5 text-sm rounded bg-emerald-600 text-white"
            >
              Run
            </button>
          </div>

          {tab === "deterministic" && (
            <ResultCard title="Deterministic projection">
              {deterministic.isPending && <Loading />}
              {deterministic.error && <ErrBox msg={errMsg(deterministic.error)} />}
              {deterministic.data && (
                <>
                  <ProjectionChart data={deterministic.data} />
                  <p className="text-sm mt-2 text-slate-600">
                    {deterministic.data.depleted_age
                      ? `Portfolio depletes at age ${deterministic.data.depleted_age}.`
                      : `Ends at ${formatCurrency(
                          deterministic.data.balance_real.at(-1) ?? 0,
                        )} (real).`}
                  </p>
                </>
              )}
              {!deterministic.data && !deterministic.isPending && (
                <Hint>Press Run to project a single deterministic path.</Hint>
              )}
            </ResultCard>
          )}

          {tab === "monte_carlo" && (
            <ResultCard title="Monte Carlo">
              <div className="flex items-center gap-4 mb-3 text-sm">
                <label className="flex items-center gap-1">
                  Trials
                  <input
                    type="number"
                    value={trials}
                    step={1000}
                    min={100}
                    max={50000}
                    onChange={(e) => setTrials(parseInt(e.target.value, 10))}
                    className="w-24 border border-slate-300 rounded px-2 py-1"
                  />
                </label>
                <label className="flex items-center gap-1">
                  Method
                  <select
                    value={method}
                    onChange={(e) =>
                      setMethod(e.target.value as "bootstrap" | "lognormal")
                    }
                    className="border border-slate-300 rounded px-2 py-1"
                  >
                    <option value="bootstrap">Historical bootstrap</option>
                    <option value="lognormal">Lognormal</option>
                  </select>
                </label>
              </div>
              {monteCarlo.isPending && <Loading />}
              {monteCarlo.error && <ErrBox msg={errMsg(monteCarlo.error)} />}
              {monteCarlo.data && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center mb-4">
                    <SuccessGauge rate={monteCarlo.data.success_rate} />
                    <div className="grid grid-cols-1 gap-2">
                      <KpiCard
                        label="Median terminal (real)"
                        value={monteCarlo.data.median_terminal_real}
                      />
                      <div className="grid grid-cols-2 gap-2">
                        <KpiCard
                          label="Terminal p5"
                          value={monteCarlo.data.terminal_p5}
                        />
                        <KpiCard
                          label="Terminal p95"
                          value={monteCarlo.data.terminal_p95}
                        />
                      </div>
                    </div>
                  </div>
                  <FanChart result={monteCarlo.data} />
                  <button
                    onClick={() => pushProjection.mutate(monteCarlo.data!)}
                    disabled={pushProjection.isPending}
                    className="mt-3 px-3 py-1.5 text-sm rounded bg-ink text-white disabled:opacity-40"
                  >
                    {pushProjection.isPending ? "Pushing…" : "Push to Sheets"}
                  </button>
                  {pushProjection.isSuccess && (
                    <span className="ml-3 text-sm text-emerald-700">
                      Wrote {pushProjection.data.written_rows} rows.
                    </span>
                  )}
                  {pushProjection.error && (
                    <span className="ml-3 text-sm text-amber-700">
                      {errMsg(pushProjection.error)}
                    </span>
                  )}
                </>
              )}
              {!monteCarlo.data && !monteCarlo.isPending && (
                <Hint>
                  Press Run to simulate {trials.toLocaleString()} portfolio paths.
                </Hint>
              )}
            </ResultCard>
          )}

          {tab === "fire" && (
            <ResultCard title="FIRE numbers">
              {fire.isPending && <Loading />}
              {fire.error && <ErrBox msg={errMsg(fire.error)} />}
              {fire.data && <FireCards data={fire.data} />}
              {!fire.data && !fire.isPending && (
                <Hint>Press Run to compute Coast / Lean / Regular / Fat FIRE.</Hint>
              )}
            </ResultCard>
          )}
        </div>
      </div>
    </div>
  );
}

function FireCards({ data }: { data: FireNumbers }) {
  const items: { label: string; value: number; note: string }[] = [
    { label: "Coast FIRE", value: data.coast_fire, note: "Stop saving today" },
    { label: "Lean FIRE", value: data.lean_fire, note: "60% of spend" },
    { label: "Regular FIRE", value: data.regular_fire, note: "Full spend" },
    { label: "Fat FIRE", value: data.fat_fire, note: "200% of spend" },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {items.map((it) => (
        <div key={it.label} className="rounded border border-slate-200 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">
            {it.label}
          </div>
          <div className="text-xl font-semibold mt-1">
            {formatCurrency(it.value)}
          </div>
          <div className="text-xs text-slate-400 mt-1">{it.note}</div>
        </div>
      ))}
    </div>
  );
}

function ResultCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded border border-slate-200 bg-white p-4">
      <h3 className="font-semibold mb-3">{title}</h3>
      {children}
    </div>
  );
}

const Loading = () => <div className="text-sm text-slate-500">Running…</div>;
const Hint = ({ children }: { children: React.ReactNode }) => (
  <div className="text-sm text-slate-400 py-8 text-center">{children}</div>
);
const ErrBox = ({ msg }: { msg: string }) => (
  <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
    {msg}
  </div>
);
