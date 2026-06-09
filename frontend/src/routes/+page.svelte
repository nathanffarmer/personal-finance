<script lang="ts">
  import { createQuery, useQueryClient } from "@tanstack/svelte-query";
  import { monarchApi } from "$api/monarch";
  import { ApiError } from "$api/client";
  import KpiCard from "$components/KpiCard.svelte";
  import AccountTable from "$components/AccountTable.svelte";

  const qc = useQueryClient();
  const accounts = createQuery({ queryKey: ["accounts"], queryFn: monarchApi.accounts });
  const netWorth = createQuery({ queryKey: ["net_worth"], queryFn: monarchApi.netWorth });

  async function refresh() {
    await monarchApi.clearCache();
    await qc.invalidateQueries({ queryKey: ["accounts"] });
    await qc.invalidateQueries({ queryKey: ["net_worth"] });
  }

  function errDetail(err: unknown): string {
    if (err instanceof ApiError && err.body && typeof err.body === "object") {
      const body = err.body as { detail?: string };
      if (body.detail) return body.detail;
    }
    return err instanceof Error ? err.message : String(err);
  }
</script>

<div class="max-w-5xl">
  <div class="flex items-center justify-between mb-6">
    <h2 class="text-2xl font-semibold">Dashboard</h2>
    <button
      onclick={refresh}
      class="px-3 py-1.5 text-sm rounded border border-slate-300 hover:bg-slate-50"
    >
      Refresh
    </button>
  </div>

  {#if $accounts.error || $netWorth.error}
    <div
      class="mb-4 rounded border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      {errDetail($accounts.error ?? $netWorth.error)}
    </div>
  {/if}

  {#if $netWorth.data}
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <KpiCard label="Net worth" value={$netWorth.data.total} />
      <KpiCard label="Liquid (cash)" value={$netWorth.data.by_type.cash} />
      <KpiCard label="Investments" value={$netWorth.data.by_type.investment} />
      <KpiCard
        label="Debt"
        value={$netWorth.data.by_type.credit + $netWorth.data.by_type.loan}
      />
    </div>
  {/if}

  {#if $accounts.isLoading}
    <div class="text-sm text-slate-500">Loading accounts…</div>
  {/if}
  {#if $accounts.data}
    <AccountTable accounts={$accounts.data} />
  {/if}
</div>
