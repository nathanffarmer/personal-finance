<script lang="ts">
  import type { Category } from "$api/monarch";

  let {
    value,
    categories,
    onchange,
  }: {
    value: string | null;
    categories: Category[];
    onchange: (categoryId: string) => void;
  } = $props();
</script>

<select
  value={value ?? ""}
  onchange={(e) => onchange((e.target as HTMLSelectElement).value)}
  class="text-sm border border-slate-300 rounded px-2 py-1 bg-white"
>
  <option value="">— Uncategorized —</option>
  {#each categories as c (c.id)}
    <option value={c.id}>
      {c.group ? `${c.group} · ` : ""}{c.name}
    </option>
  {/each}
</select>
