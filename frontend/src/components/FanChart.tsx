import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { MonteCarloResult } from "@/api/retirement";
import { formatCurrency } from "@/api/monarch";

export function FanChart({ result }: { result: MonteCarloResult }) {
  const bands = result.percentiles;
  const rows = result.ages.map((age, i) => ({
    age,
    // Stacked areas: a transparent base + deltas so each band fills. These
    // are drawing-only series (tooltipType="none") because the deltas are
    // meaningless to read; the tooltip shows the absolute percentiles below.
    base: bands.p5[i],
    band5to25: bands.p25[i] - bands.p5[i],
    band25to75: bands.p75[i] - bands.p25[i],
    band75to95: bands.p95[i] - bands.p75[i],
    // Absolute percentile values, surfaced via invisible Lines.
    p5: bands.p5[i],
    p25: bands.p25[i],
    p50: bands.p50[i],
    p75: bands.p75[i],
    p95: bands.p95[i],
  }));

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="age" tick={{ fontSize: 12 }} />
          <YAxis
            tickFormatter={(v) => `${Math.round(v / 1000)}k`}
            tick={{ fontSize: 12 }}
            width={48}
          />
          <Tooltip
            formatter={(v: number, name) => [formatCurrency(v), name]}
            labelFormatter={(l) => `Age ${l}`}
          />
          <Legend />
          <Area
            dataKey="base"
            stackId="band"
            stroke="none"
            fill="transparent"
            legendType="none"
            tooltipType="none"
          />
          <Area
            dataKey="band5to25"
            stackId="band"
            stroke="none"
            fill="#cbd5e1"
            name="5-25%"
            tooltipType="none"
          />
          <Area
            dataKey="band25to75"
            stackId="band"
            stroke="none"
            fill="#94a3b8"
            name="25-75%"
            tooltipType="none"
          />
          <Area
            dataKey="band75to95"
            stackId="band"
            stroke="none"
            fill="#cbd5e1"
            name="75-95%"
            tooltipType="none"
          />
          <Line
            dataKey="p95"
            stroke="none"
            dot={false}
            activeDot={false}
            legendType="none"
            name="95th percentile"
          />
          <Line
            dataKey="p75"
            stroke="none"
            dot={false}
            activeDot={false}
            legendType="none"
            name="75th percentile"
          />
          <Line
            dataKey="p50"
            stroke="#0b1220"
            strokeWidth={2}
            dot={false}
            name="Median"
          />
          <Line
            dataKey="p25"
            stroke="none"
            dot={false}
            activeDot={false}
            legendType="none"
            name="25th percentile"
          />
          <Line
            dataKey="p5"
            stroke="none"
            dot={false}
            activeDot={false}
            legendType="none"
            name="5th percentile"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
