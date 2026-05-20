import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DeterministicProjection } from "@/api/retirement";
import { formatCurrency } from "@/api/monarch";

export function ProjectionChart({ data }: { data: DeterministicProjection }) {
  const rows = data.ages.map((age, i) => ({
    age,
    balance: data.balance_real[i],
  }));
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="age" tick={{ fontSize: 12 }} />
          <YAxis
            tickFormatter={(v) => `${Math.round(v / 1000)}k`}
            tick={{ fontSize: 12 }}
            width={48}
          />
          <Tooltip
            formatter={(v: number) => formatCurrency(v)}
            labelFormatter={(l) => `Age ${l}`}
          />
          <Line
            type="monotone"
            dataKey="balance"
            stroke="#0b1220"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
