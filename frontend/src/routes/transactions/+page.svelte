<script lang="ts">
  import { createMutation, createQuery, useQueryClient } from "@tanstack/svelte-query";
  import { formatCurrency, monarchApi, type Transaction } from "$api/monarch";
  import CategoryPicker from "$components/CategoryPicker.svelte";

  const qc = useQueryClient();
  const limit = 100;
  let offset = $state(0);
  let uncategorizedOnly = $state(false);
  let selected = $state(new Set<string>());
  let bulkCategory = $state("");

  let txQueryKey = $derived(["transactions", { limit, offset }]);
  let txQuery = $derived(
    createQuery({
      queryKey: txQueryKey,
      queryFn: () => monarchApi.transactions({ limit, offset }),
    }),
  );

  const categoriesQuery = createQuery({
    queryKey: ["categories"],
    queryFn: monarchApi.categories,
  });

  const update = createMutation({
    mutationFn: (args: { id: string; category_id: string }) =>
      monarchApi.updateTransaction(args.id, { category_id: args.category_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });

  const bulkUpdate = createMutation({
    mutationFn: (items: { id: string; category_id: string }[]) =>
      monarchApi.categorizeBulk(items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      selected = new Set();
    },
  });

  let rows = $derived(
    ($txQuery.data ?? []).filter((t: Transaction) =>
      !uncategorizedOnly || t.category_id == null,
    ),
  );

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selected = next;
  }
</script>

<div class="max-w-6xl">
  <h2 class="text-2xl font-semibold mb-4">Transactions</h2>

  <div class="flex items-center gap-4 mb-4">
    <label class="text-sm flex items-center gap-2">
      <input type="checkbox" bind:checked={uncategorizedOnly} />
      Uncategorized only
    </label>
    <div class="flex items-center gap-2 text-sm">
      <button
        disabled={offset === 0}
        onclick={() => (offset = Math.max(0, offset - limit))}
        class="px-2 py-1 border border-slate-300 rounded disabled:opacity-40"
      >
        ‹ Prev
      </button>
      <span class="text-slate-600">Offset {offset}–{offset + limit}</span>
      <button
        onclick={() => (offset = offset + limit)}
        class="px-2 py-1 border border-slate-300 rounded"
      >
        Next ›
      </button>
    </div>
  </div>

  {#if selected.size > 0}
    <div
      class="mb-4 rounded border border-slate-300 bg-slate-50 px-3 py-2 flex items-center gap-3"
    >
      <span class="text-sm">{selected.size} selected</span>
      <select
        bind:value={bulkCategory}
        class="text-sm border border-slate-300 rounded px-2 py-1 bg-white"
      >
        <option value="">Choose category…</option>
        {#each $categoriesQuery.data ?? [] as c (c.id)}
          <option value={c.id}>{c.group ? `${c.group} · ` : ""}{c.name}</option>
        {/each}
      </select>
      <button
        disabled={!bulkCategory || $bulkUpdate.isPending}
        onclick={() =>
          $bulkUpdate.mutate(
            [...selected].map((id) => ({ id, category_id: bulkCategory })),
          )}
        class="px-3 py-1 text-sm rounded bg-ink text-white disabled:opacity-40"
      >
        Apply
      </button>
      <button onclick={() => (selected = new Set())} class="text-sm text-slate-600 underline">
        Clear
      </button>
    </div>
  {/if}

  <div class="rounded border border-slate-200 bg-white">
    <table class="w-full text-sm">
      <thead class="bg-slate-50">
        <tr class="text-left">
          <th class="px-3 py-2 w-8"></th>
          <th class="px-3 py-2">Date</th>
          <th class="px-3 py-2">Merchant</th>
          <th class="px-3 py-2">Category</th>
          <th class="px-3 py-2 text-right">Amount</th>
        </tr>
      </thead>
      <tbody>
        {#each rows as t (t.id)}
          <tr class="border-t border-slate-100">
            <td class="px-3 py-2">
              <input
                type="checkbox"
                checked={selected.has(t.id)}
                onchange={() => toggle(t.id)}
              />
            </td>
            <td class="px-3 py-2 text-slate-600">{t.date}</td>
            <td class="px-3 py-2">{t.merchant || t.description}</td>
            <td class="px-3 py-2">
              <CategoryPicker
                value={t.category_id}
                categories={$categoriesQuery.data ?? []}
                onchange={(category_id) =>
                  $update.mutate({ id: t.id, category_id })}
              />
            </td>
            <td
              class="px-3 py-2 text-right tabular-nums {t.amount < 0
                ? 'text-rose-600'
                : 'text-emerald-700'}"
            >
              {formatCurrency(t.amount)}
            </td>
          </tr>
        {/each}
        {#if !$txQuery.isLoading && rows.length === 0}
          <tr>
            <td colspan="5" class="px-3 py-6 text-center text-slate-500">
              No transactions match.
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>
</div>
