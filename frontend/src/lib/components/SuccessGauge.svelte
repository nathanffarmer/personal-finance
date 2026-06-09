<script lang="ts">
  let { rate }: { rate: number } = $props();
  let pct = $derived(Math.round(rate * 100));
  let color = $derived(rate >= 0.9 ? "#16a34a" : rate >= 0.75 ? "#d97706" : "#dc2626");

  const radius = 70;
  const circumference = Math.PI * radius;
  let offset = $derived(circumference * (1 - rate));
</script>

<div class="flex flex-col items-center">
  <svg width="180" height="110" viewBox="0 0 180 110">
    <path
      d="M 20 100 A {radius} {radius} 0 0 1 160 100"
      fill="none"
      stroke="#e2e8f0"
      stroke-width="16"
      stroke-linecap="round"
    />
    <path
      d="M 20 100 A {radius} {radius} 0 0 1 160 100"
      fill="none"
      stroke={color}
      stroke-width="16"
      stroke-linecap="round"
      stroke-dasharray={circumference}
      stroke-dashoffset={offset}
    />
    <text x="90" y="92" text-anchor="middle" font-size="28" font-weight="600" fill={color}>
      {pct}%
    </text>
  </svg>
  <div class="text-sm text-slate-500 -mt-2">Probability of success</div>
</div>
