<script lang="ts">
  let {
    label,
    value,
    onchange,
    step = 1,
    suffix,
    min,
    max,
  }: {
    label: string;
    value: number;
    onchange: (v: number) => void;
    step?: number;
    suffix?: string;
    min?: number;
    max?: number;
  } = $props();
</script>

<label class="block">
  <span class="text-xs text-slate-500">{label}</span>
  <div class="flex items-center gap-1">
    <input
      type="number"
      value={Number.isFinite(value) ? value : ""}
      {step}
      {min}
      {max}
      oninput={(e) => onchange(parseFloat((e.target as HTMLInputElement).value))}
      class="w-full border border-slate-300 rounded px-2 py-1 text-sm"
    />
    {#if suffix}
      <span class="text-xs text-slate-400">{suffix}</span>
    {/if}
  </div>
</label>
