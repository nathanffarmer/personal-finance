<script lang="ts">
  import { Chart, Svg, Axis, Area, Spline, Highlight, Tooltip } from "layerchart";
  import { scaleLinear } from "d3-scale";
  import type { MonteCarloResult } from "$api/retirement";
  import { formatCurrency } from "$api/monarch";

  let { result }: { result: MonteCarloResult } = $props();

  let rows = $derived(
    result.ages.map((age, i) => ({
      age,
      p5: result.percentiles.p5[i],
      p25: result.percentiles.p25[i],
      p50: result.percentiles.p50[i],
      p75: result.percentiles.p75[i],
      p95: result.percentiles.p95[i],
    })),
  );
</script>

<div class="h-80">
  <Chart
    data={rows}
    x="age"
    xScale={scaleLinear()}
    yScale={scaleLinear()}
    yDomain={[0, undefined]}
    yNice
    padding={{ left: 64, bottom: 28, top: 8, right: 16 }}
    tooltip={{ mode: "voronoi" }}
  >
    <Svg>
      <Axis placement="left" grid rule format={(v: number) => `${Math.round(v / 1000)}k`} />
      <Axis placement="bottom" rule />
      <!-- 5–95% outer band (lightest) -->
      <Area y0Accessor={(d: any) => d.p5} y1Accessor={(d: any) => d.p95} class="fill-slate-200" />
      <!-- 25–75% inner band (mid) -->
      <Area y0Accessor={(d: any) => d.p25} y1Accessor={(d: any) => d.p75} class="fill-slate-400/60" />
      <!-- Median line -->
      <Spline y="p50" class="stroke-ink stroke-2" />
      <Highlight points lines y="p50" />
    </Svg>
    <Tooltip.Root let:data>
      <Tooltip.Header>Age {data.age}</Tooltip.Header>
      <Tooltip.List>
        <Tooltip.Item label="p95" value={formatCurrency(data.p95)} />
        <Tooltip.Item label="p75" value={formatCurrency(data.p75)} />
        <Tooltip.Item label="Median" value={formatCurrency(data.p50)} />
        <Tooltip.Item label="p25" value={formatCurrency(data.p25)} />
        <Tooltip.Item label="p5" value={formatCurrency(data.p5)} />
      </Tooltip.List>
    </Tooltip.Root>
  </Chart>
</div>
