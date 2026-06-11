<script lang="ts">
  import { createMutation } from "@tanstack/svelte-query";
  import {
    type FireNumbers,
    type MonteCarloResult,
    type ScenarioInput,
    defaultScenario,
    retirementApi,
  } from "$api/retirement";
  import { formatCurrency } from "$api/monarch";
  import { sheetsApi } from "$api/sheets";
  import { ApiError } from "$api/client";
  import ScenarioForm from "$components/ScenarioForm.svelte";
  import ProjectionChart from "$components/ProjectionChart.svelte";
  import FanChart from "$components/FanChart.svelte";
  import FailureHistogram from "$components/FailureHistogram.svelte";
  import SuccessGauge from "$components/SuccessGauge.svelte";
  import KpiCard from "$components/KpiCard.svelte";

  type Tab = "deterministic" | "monte_carlo" | "fire";

  let scenario = $state<ScenarioInput>(defaultScenario());
  let tab = $state<Tab>("monte_carlo");
  let trials = $state(10000);
  let method = $state<"bootstrap" | "lognormal">("bootstrap");
  let includeCash = $state(true);

  const deterministic = createMutation({
    mutationFn: () => retirementApi.deterministic(scenario),
  });
  const monteCarlo = createMutation({
    mutationFn: () => retirementApi.monteCarlo(scenario, { trials, method }),
  });
  const fire = createMutation({
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
  const loadMonarch = createMutation({
    mutationFn: () => retirementApi.fromMonarch(scenario, includeCash),
    onSuccess: (s) => (scenario = s),
  });
  const loadSheets = createMutation({
    mutationFn: () => sheetsApi.assumptions(),
    onSuccess: (a) => {
      scenario = {
        ...scenario,
        current_age: a.current_age ?? scenario.current_age,
        retirement_age: a.retirement_age ?? scenario.retirement_age,
        end_age: a.end_age ?? scenario.end_age,
        annual_spend_real: a.annual_spend_real ?? scenario.annual_spend_real,
        annual_contributions:
          a.annual_contributions ?? scenario.annual_contributions,
      };
    },
  });
  const pushProjection = createMutation({
    mutationFn: (result: MonteCarloResult) => sheetsApi.pushProjection(result),
  });

  function runActive() {
    if (tab === "deterministic") $deterministic.mutate();
    else if (tab === "monte_carlo") $monteCarlo.mutate();
    else $fire.mutate();
  }

  function errMsg(e: unknown): string {
    if (e instanceof ApiError && e.body && typeof e.body === "object" && "detail" in e.body) {
      return String((e.body as { detail: unknown }).detail);
    }
    return e instanceof Error ? e.message : String(e);
  }

  function fireRow(label: string, value: number, note: string) {
    return { label, value, note };
  }

  let fireCards = $derived.by(() => {
    const data = $fire.data;
    if (!data) return [];
    return [
      fireRow("Coast FIRE", data.coast_fire, "Stop saving today"),
      fireRow("Lean FIRE", data.lean_fire, "60% of spend"),
      fireRow("Regular FIRE", data.regular_fire, "Full spend"),
      fireRow("Fat FIRE", data.fat_fire, "200% of spend"),
    ];
  });
</script>

<div class="max-w-6xl">
  <h2 class="text-2xl font-semibold mb-4">Retirement</h2>
  <div class="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">
    <!-- Left: scenario form -->
    <div class="rounded border border-slate-200 bg-white p-4">
      <div class="flex gap-2 mb-3">
        <button
          onclick={() => $loadMonarch.mutate()}
          disabled={$loadMonarch.isPending}
          class="flex-1 text-xs px-2 py-1.5 border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-40"
        >
          {$loadMonarch.isPending ? "Loading…" : "Load from Monarch"}
        </button>
        <button
          onclick={() => $loadSheets.mutate()}
          disabled={$loadSheets.isPending}
          class="flex-1 text-xs px-2 py-1.5 border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-40"
        >
          {$loadSheets.isPending ? "Loading…" : "Load from Sheets"}
        </button>
      </div>
      <label class="flex items-center gap-2 text-xs text-slate-500 mb-3">
        <input type="checkbox" bind:checked={includeCash} />
        Include checking/savings balances in portfolio
      </label>
      {#if $loadMonarch.error}
        <p class="text-xs text-amber-700 mb-2">{errMsg($loadMonarch.error)}</p>
      {/if}
      {#if $loadSheets.error}
        <p class="text-xs text-amber-700 mb-2">{errMsg($loadSheets.error)}</p>
      {/if}
      <ScenarioForm bind:scenario />
    </div>

    <!-- Right: results -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <div class="flex gap-1">
          {#each ["deterministic", "monte_carlo", "fire"] as t}
            <button
              onclick={() => (tab = t as Tab)}
              class="px-3 py-1.5 text-sm rounded {tab === t
                ? 'bg-ink text-white'
                : 'hover:bg-slate-100'}"
            >
              {t === "deterministic"
                ? "Deterministic"
                : t === "monte_carlo"
                  ? "Monte Carlo"
                  : "FIRE numbers"}
            </button>
          {/each}
        </div>
        <button
          onclick={runActive}
          class="px-4 py-1.5 text-sm rounded bg-emerald-600 text-white"
        >
          Run
        </button>
      </div>

      {#if tab === "deterministic"}
        <div class="rounded border border-slate-200 bg-white p-4">
          <h3 class="font-semibold mb-3">Deterministic projection</h3>
          {#if $deterministic.isPending}
            <div class="text-sm text-slate-500">Running…</div>
          {/if}
          {#if $deterministic.error}
            <div
              class="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            >
              {errMsg($deterministic.error)}
            </div>
          {/if}
          {#if $deterministic.data}
            <ProjectionChart data={$deterministic.data} />
            <p class="text-sm mt-2 text-slate-600">
              {$deterministic.data.depleted_age
                ? `Portfolio depletes at age ${$deterministic.data.depleted_age}.`
                : `Ends at ${formatCurrency($deterministic.data.balance_real.at(-1) ?? 0)} (real).`}
            </p>
          {:else if !$deterministic.isPending}
            <div class="text-sm text-slate-400 py-8 text-center">
              Press Run to project a single deterministic path.
            </div>
          {/if}
        </div>
      {/if}

      {#if tab === "monte_carlo"}
        <div class="rounded border border-slate-200 bg-white p-4">
          <h3 class="font-semibold mb-3">Monte Carlo</h3>
          <div class="flex items-center gap-4 mb-3 text-sm">
            <label class="flex items-center gap-1">
              Trials
              <input
                type="number"
                bind:value={trials}
                step="1000"
                min="100"
                max="50000"
                class="w-24 border border-slate-300 rounded px-2 py-1"
              />
            </label>
            <label class="flex items-center gap-1">
              Method
              <select
                bind:value={method}
                class="border border-slate-300 rounded px-2 py-1"
              >
                <option value="bootstrap">Historical bootstrap</option>
                <option value="lognormal">Lognormal</option>
              </select>
            </label>
          </div>

          {#if $monteCarlo.isPending}
            <div class="text-sm text-slate-500">Running…</div>
          {/if}
          {#if $monteCarlo.error}
            <div
              class="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            >
              {errMsg($monteCarlo.error)}
            </div>
          {/if}
          {#if $monteCarlo.data}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 items-center mb-4">
              <SuccessGauge rate={$monteCarlo.data.success_rate} />
              <div class="grid grid-cols-1 gap-2">
                <KpiCard
                  label="Median terminal (real)"
                  value={$monteCarlo.data.median_terminal_real}
                />
                <div class="grid grid-cols-2 gap-2">
                  <KpiCard label="Terminal p5" value={$monteCarlo.data.terminal_p5} />
                  <KpiCard label="Terminal p95" value={$monteCarlo.data.terminal_p95} />
                </div>
              </div>
            </div>
            <FanChart result={$monteCarlo.data} />
            <div class="mt-4">
              <h4 class="text-sm font-semibold mb-1">Failure ages</h4>
              <FailureHistogram bins={$monteCarlo.data.failure_ages} />
            </div>
            <button
              onclick={() => $pushProjection.mutate($monteCarlo.data!)}
              disabled={$pushProjection.isPending}
              class="mt-3 px-3 py-1.5 text-sm rounded bg-ink text-white disabled:opacity-40"
            >
              {$pushProjection.isPending ? "Pushing…" : "Push to Sheets"}
            </button>
            {#if $pushProjection.isSuccess}
              <span class="ml-3 text-sm text-emerald-700">
                Wrote {$pushProjection.data.written_rows} rows.
              </span>
            {/if}
            {#if $pushProjection.error}
              <span class="ml-3 text-sm text-amber-700">
                {errMsg($pushProjection.error)}
              </span>
            {/if}
          {:else if !$monteCarlo.isPending}
            <div class="text-sm text-slate-400 py-8 text-center">
              Press Run to simulate {trials.toLocaleString()} portfolio paths.
            </div>
          {/if}
        </div>
      {/if}

      {#if tab === "fire"}
        <div class="rounded border border-slate-200 bg-white p-4">
          <h3 class="font-semibold mb-3">FIRE numbers</h3>
          {#if $fire.isPending}
            <div class="text-sm text-slate-500">Running…</div>
          {/if}
          {#if $fire.error}
            <div
              class="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            >
              {errMsg($fire.error)}
            </div>
          {/if}
          {#if $fire.data}
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              {#each fireCards as it (it.label)}
                <div class="rounded border border-slate-200 p-4">
                  <div class="text-xs uppercase tracking-wide text-slate-500">
                    {it.label}
                  </div>
                  <div class="text-xl font-semibold mt-1">
                    {formatCurrency(it.value)}
                  </div>
                  <div class="text-xs text-slate-400 mt-1">{it.note}</div>
                </div>
              {/each}
            </div>
          {:else if !$fire.isPending}
            <div class="text-sm text-slate-400 py-8 text-center">
              Press Run to compute Coast / Lean / Regular / Fat FIRE.
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div>
