<script lang="ts">
  import { Chart, Svg, Axis, Bars, Tooltip } from "layerchart";
  import { scaleBand, scaleLinear } from "d3-scale";
  import type { FailureBin } from "$api/retirement";

  let { bins }: { bins: FailureBin[] } = $props();
</script>

{#if bins.length > 0}
  <div class="h-48">
    <Chart
      data={bins}
      x="age"
      y="count"
      xScale={scaleBand().padding(0.2)}
      yScale={scaleLinear()}
      padding={{ left: 48, bottom: 28, top: 8, right: 12 }}
      tooltip={{ mode: "band" }}
    >
      <Svg>
        <Axis placement="left" grid rule />
        <Axis placement="bottom" rule />
        <Bars class="fill-rose-400" />
      </Svg>
      <Tooltip.Root let:data>
        <Tooltip.Header>Failed by age {data.age}</Tooltip.Header>
        <Tooltip.List>
          <Tooltip.Item label="Trials" value={data.count} />
        </Tooltip.List>
      </Tooltip.Root>
    </Chart>
  </div>
{:else}
  <p class="text-sm text-emerald-700">No trial failures.</p>
{/if}
