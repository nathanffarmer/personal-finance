<script lang="ts">
  // Stores 0..1, displays 0..100.
  let {
    label,
    value,
    onchange,
    step = 0.5,
  }: {
    label: string;
    value: number;
    onchange: (v: number) => void;
    step?: number;
  } = $props();
</script>

<label class="block">
  <span class="text-xs text-slate-500">{label}</span>
  <div class="flex items-center gap-1">
    <input
      type="number"
      value={Number.isFinite(value) ? +(value * 100).toFixed(2) : ""}
      {step}
      oninput={(e) =>
        onchange(parseFloat((e.target as HTMLInputElement).value) / 100)}
      class="w-full border border-slate-300 rounded px-2 py-1 text-sm"
    />
    <span class="text-xs text-slate-400">%</span>
  </div>
</label>
