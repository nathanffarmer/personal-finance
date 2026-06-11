<script lang="ts">
  import { formatCurrency } from "$api/monarch";

  let { label, value }: { label: string; value: number } = $props();
  let negative = $derived(value < 0);
</script>

<div class="rounded border border-slate-200 bg-white p-4">
  <div class="text-xs uppercase tracking-wide text-slate-500">{label}</div>
  <div class="mt-1 text-2xl font-semibold {negative ? 'text-rose-600' : 'text-ink'}">
    {formatCurrency(value)}
  </div>
</div>
