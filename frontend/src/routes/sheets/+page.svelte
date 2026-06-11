<script lang="ts">
  import { createMutation, createQuery, useQueryClient } from "@tanstack/svelte-query";
  import { sheetsApi } from "$api/sheets";
  import { formatCurrency } from "$api/monarch";
  import { ApiError } from "$api/client";

  const qc = useQueryClient();
  const status = createQuery({ queryKey: ["sheets", "status"], queryFn: sheetsApi.status });
  let assumptions = $derived(
    createQuery({
      queryKey: ["sheets", "assumptions"],
      queryFn: sheetsApi.assumptions,
      enabled: $status.data?.authorized === true,
    }),
  );
  let targets = $derived(
    createQuery({
      queryKey: ["sheets", "targets"],
      queryFn: sheetsApi.targets,
      enabled: $status.data?.authorized === true,
    }),
  );

  const pushAccounts = createMutation({
    mutationFn: sheetsApi.pushAccounts,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sheets", "status"] }),
  });
  const pushHoldings = createMutation({
    mutationFn: sheetsApi.pushHoldings,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sheets", "status"] }),
  });

  function errMsg(e: unknown): string {
    if (e instanceof ApiError && e.body && typeof e.body === "object" && "detail" in e.body) {
      return String((e.body as { detail: unknown }).detail);
    }
    return e instanceof Error ? e.message : String(e);
  }
</script>

<div class="max-w-4xl">
  <h2 class="text-2xl font-semibold mb-4">Sheets</h2>

  <section class="mb-6 rounded border border-slate-200 bg-white p-4">
    <h3 class="font-semibold mb-2">Status</h3>
    {#if $status.isLoading}
      <div class="text-sm text-slate-500">Checking…</div>
    {/if}
    {#if $status.data}
      <dl class="text-sm grid grid-cols-2 gap-y-1 max-w-md">
        <dt class="text-slate-500">Authorized</dt>
        <dd>{$status.data.authorized ? "Yes" : "No"}</dd>
        <dt class="text-slate-500">Sheet ID</dt>
        <dd class="font-mono text-xs break-all">
          {$status.data.sheet_id || "(not set)"}
        </dd>
        <dt class="text-slate-500">Last write</dt>
        <dd>{$status.data.last_write_at || "—"}</dd>
        {#if $status.data.error}
          <dt class="text-slate-500">Error</dt>
          <dd class="text-amber-700">{$status.data.error}</dd>
        {/if}
      </dl>
    {/if}
  </section>

  <section class="mb-6 rounded border border-slate-200 bg-white p-4">
    <h3 class="font-semibold mb-2">Push snapshots</h3>
    <div class="flex gap-3">
      <button
        disabled={$pushAccounts.isPending}
        onclick={() => $pushAccounts.mutate()}
        class="px-3 py-2 text-sm rounded bg-ink text-white disabled:opacity-40"
      >
        {$pushAccounts.isPending ? "Pushing…" : "Push accounts"}
      </button>
      <button
        disabled={$pushHoldings.isPending}
        onclick={() => $pushHoldings.mutate()}
        class="px-3 py-2 text-sm rounded bg-ink text-white disabled:opacity-40"
      >
        {$pushHoldings.isPending ? "Pushing…" : "Push holdings"}
      </button>
    </div>
    {#if $pushAccounts.isSuccess}
      <p class="mt-2 text-sm text-emerald-700">
        Wrote {$pushAccounts.data.written_rows} rows to {$pushAccounts.data.range}.
      </p>
    {/if}
    {#if $pushHoldings.isSuccess}
      <p class="mt-2 text-sm text-emerald-700">
        Wrote {$pushHoldings.data.written_rows} rows to {$pushHoldings.data.range}.
      </p>
    {/if}
    {#if $pushAccounts.error}
      <p class="mt-2 text-sm text-amber-700">{errMsg($pushAccounts.error)}</p>
    {/if}
    {#if $pushHoldings.error}
      <p class="mt-2 text-sm text-amber-700">{errMsg($pushHoldings.error)}</p>
    {/if}
  </section>

  <section class="mb-6 rounded border border-slate-200 bg-white p-4">
    <h3 class="font-semibold mb-2">Assumptions (read)</h3>
    {#if $assumptions.data}
      <dl class="text-sm grid grid-cols-2 gap-y-1 max-w-md">
        <dt class="text-slate-500">Current age</dt>
        <dd>{$assumptions.data.current_age ?? "—"}</dd>
        <dt class="text-slate-500">Retirement age</dt>
        <dd>{$assumptions.data.retirement_age ?? "—"}</dd>
        <dt class="text-slate-500">End age</dt>
        <dd>{$assumptions.data.end_age ?? "—"}</dd>
        <dt class="text-slate-500">Annual spend (real)</dt>
        <dd>
          {$assumptions.data.annual_spend_real != null
            ? formatCurrency($assumptions.data.annual_spend_real)
            : "—"}
        </dd>
        <dt class="text-slate-500">Annual contributions</dt>
        <dd>
          {$assumptions.data.annual_contributions != null
            ? formatCurrency($assumptions.data.annual_contributions)
            : "—"}
        </dd>
        <dt class="text-slate-500">SWR</dt>
        <dd>
          {$assumptions.data.swr != null
            ? `${($assumptions.data.swr * 100).toFixed(2)}%`
            : "—"}
        </dd>
        <dt class="text-slate-500">Withdrawal strategy</dt>
        <dd>{$assumptions.data.withdrawal_kind ?? "—"}</dd>
        <dt class="text-slate-500">Glide path</dt>
        <dd>{$assumptions.data.glide_kind ?? "—"}</dd>
      </dl>
    {:else}
      <p class="text-sm text-slate-500">
        {$status.data?.authorized
          ? "Loading…"
          : "Authorize Google OAuth and set SHEET_ID to enable."}
      </p>
    {/if}
  </section>

  <section class="rounded border border-slate-200 bg-white p-4">
    <h3 class="font-semibold mb-2">Targets</h3>
    {#if $targets.data && $targets.data.length > 0}
      <table class="text-sm w-full">
        <thead>
          <tr class="text-left">
            <th class="px-2 py-1">Age</th>
            <th class="px-2 py-1 text-right">Target net worth</th>
          </tr>
        </thead>
        <tbody>
          {#each $targets.data as t (t.age)}
            <tr class="border-t border-slate-100">
              <td class="px-2 py-1">{t.age}</td>
              <td class="px-2 py-1 text-right">{formatCurrency(t.target_net_worth)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p class="text-sm text-slate-500">No targets table found.</p>
    {/if}
  </section>
</div>
