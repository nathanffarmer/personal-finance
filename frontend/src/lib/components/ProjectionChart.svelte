<script lang="ts">
  import { Chart, Svg, Axis, Spline, Highlight, Tooltip } from "layerchart";
  import { scaleLinear } from "d3-scale";
  import type { DeterministicProjection } from "$api/retirement";
  import { formatCurrency } from "$api/monarch";

  let { data }: { data: DeterministicProjection } = $props();

  let rows = $derived(
    data.ages.map((age, i) => ({ age, balance: data.balance_real[i] })),
  );
</script>

<div class="h-80">
  <Chart
    data={rows}
    x="age"
    y="balance"
    xScale={scaleLinear()}
    yScale={scaleLinear()}
    padding={{ left: 64, bottom: 28, top: 8, right: 16 }}
    tooltip={{ mode: "voronoi" }}
  >
    <Svg>
      <Axis placement="left" grid rule format={(v: number) => `${Math.round(v / 1000)}k`} />
      <Axis placement="bottom" rule />
      <Spline class="stroke-ink stroke-2" />
      <Highlight points lines />
    </Svg>
    <Tooltip.Root let:data>
      <Tooltip.Header>Age {data.age}</Tooltip.Header>
      <Tooltip.List>
        <Tooltip.Item label="Balance" value={formatCurrency(data.balance)} />
      </Tooltip.List>
    </Tooltip.Root>
  </Chart>
</div>
