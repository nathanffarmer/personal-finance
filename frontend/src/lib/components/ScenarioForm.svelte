<script lang="ts">
  import type { GlideKind, ScenarioInput, WithdrawalKind } from "$api/retirement";
  import NumberInput from "./NumberInput.svelte";
  import PercentInput from "./PercentInput.svelte";

  let {
    scenario = $bindable(),
  }: {
    scenario: ScenarioInput;
  } = $props();

  const WITHDRAWAL_KINDS: { value: WithdrawalKind; label: string }[] = [
    { value: "fixed_real", label: "Fixed real spend" },
    { value: "four_percent", label: "4% rule (Bengen)" },
    { value: "guyton_klinger", label: "Guyton-Klinger guardrails" },
    { value: "vpw", label: "Variable percentage (VPW)" },
  ];

  const GLIDE_KINDS: { value: GlideKind; label: string }[] = [
    { value: "static", label: "Static allocation" },
    { value: "bond_tent", label: "Bond tent" },
    { value: "rising_equity", label: "Rising equity" },
  ];

  let allocSum = $derived(
    scenario.asset_allocation.equity +
      scenario.asset_allocation.bond +
      scenario.asset_allocation.cash,
  );
</script>

<div class="space-y-5 text-sm">
  <section>
    <h4 class="font-semibold text-xs uppercase tracking-wide text-slate-500 mb-2">
      Timeline
    </h4>
    <div class="grid grid-cols-3 gap-2">
      <NumberInput label="Current age" value={scenario.current_age}
        onchange={(v) => (scenario.current_age = v)} />
      <NumberInput label="Retire age" value={scenario.retirement_age}
        onchange={(v) => (scenario.retirement_age = v)} />
      <NumberInput label="End age" value={scenario.end_age}
        onchange={(v) => (scenario.end_age = v)} />
    </div>
  </section>

  <section>
    <h4 class="font-semibold text-xs uppercase tracking-wide text-slate-500 mb-2">
      Portfolio
    </h4>
    <div class="grid grid-cols-2 gap-2">
      <NumberInput label="Current portfolio" value={scenario.current_portfolio}
        step={1000} onchange={(v) => (scenario.current_portfolio = v)} />
      <NumberInput label="Annual contributions" value={scenario.annual_contributions}
        step={1000} onchange={(v) => (scenario.annual_contributions = v)} />
      <NumberInput label="Annual spend (real)" value={scenario.annual_spend_real}
        step={1000} onchange={(v) => (scenario.annual_spend_real = v)} />
    </div>
  </section>

  <section>
    <h4 class="font-semibold text-xs uppercase tracking-wide text-slate-500 mb-2">
      Asset allocation
    </h4>
    <div class="grid grid-cols-3 gap-2">
      <PercentInput label="Equity" value={scenario.asset_allocation.equity}
        onchange={(v) => (scenario.asset_allocation.equity = v)} />
      <PercentInput label="Bond" value={scenario.asset_allocation.bond}
        onchange={(v) => (scenario.asset_allocation.bond = v)} />
      <PercentInput label="Cash" value={scenario.asset_allocation.cash}
        onchange={(v) => (scenario.asset_allocation.cash = v)} />
    </div>
    <p class="text-xs text-slate-400 mt-1">Sum: {(allocSum * 100).toFixed(0)}%</p>
  </section>

  <section>
    <h4 class="font-semibold text-xs uppercase tracking-wide text-slate-500 mb-2">
      Withdrawal strategy
    </h4>
    <select
      bind:value={scenario.withdrawal_strategy.kind}
      class="w-full border border-slate-300 rounded px-2 py-1"
    >
      {#each WITHDRAWAL_KINDS as w}
        <option value={w.value}>{w.label}</option>
      {/each}
    </select>
    {#if scenario.withdrawal_strategy.kind === "guyton_klinger"}
      <div class="grid grid-cols-2 gap-2 mt-2">
        <PercentInput
          label="Initial rate"
          value={scenario.withdrawal_strategy.params.initial_rate ?? 0.05}
          onchange={(v) => (scenario.withdrawal_strategy.params.initial_rate = v)}
        />
      </div>
    {:else if scenario.withdrawal_strategy.kind === "four_percent"}
      <div class="mt-2">
        <PercentInput
          label="Initial rate"
          value={scenario.withdrawal_strategy.params.initial_rate ?? 0.04}
          onchange={(v) => (scenario.withdrawal_strategy.params.initial_rate = v)}
        />
      </div>
    {/if}
  </section>

  <section>
    <h4 class="font-semibold text-xs uppercase tracking-wide text-slate-500 mb-2">
      Glide path
    </h4>
    <select
      bind:value={scenario.glide_path.kind}
      class="w-full border border-slate-300 rounded px-2 py-1"
    >
      {#each GLIDE_KINDS as g}
        <option value={g.value}>{g.label}</option>
      {/each}
    </select>
  </section>

  <section>
    <h4 class="font-semibold text-xs uppercase tracking-wide text-slate-500 mb-2">
      Return assumptions (lognormal mode)
    </h4>
    <div class="grid grid-cols-2 gap-2">
      <PercentInput label="Equity mean" value={scenario.return_assumptions.equity_mean}
        onchange={(v) => (scenario.return_assumptions.equity_mean = v)} />
      <PercentInput label="Equity SD" value={scenario.return_assumptions.equity_sd}
        onchange={(v) => (scenario.return_assumptions.equity_sd = v)} />
      <PercentInput label="Bond mean" value={scenario.return_assumptions.bond_mean}
        onchange={(v) => (scenario.return_assumptions.bond_mean = v)} />
      <PercentInput label="Bond SD" value={scenario.return_assumptions.bond_sd}
        onchange={(v) => (scenario.return_assumptions.bond_sd = v)} />
    </div>
  </section>
</div>
