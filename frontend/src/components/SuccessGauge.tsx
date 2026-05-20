export function SuccessGauge({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  const color =
    rate >= 0.9 ? "#16a34a" : rate >= 0.75 ? "#d97706" : "#dc2626";
  // Simple SVG arc gauge.
  const radius = 70;
  const circumference = Math.PI * radius;
  const offset = circumference * (1 - rate);

  return (
    <div className="flex flex-col items-center">
      <svg width="180" height="110" viewBox="0 0 180 110">
        <path
          d={`M 20 100 A ${radius} ${radius} 0 0 1 160 100`}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="16"
          strokeLinecap="round"
        />
        <path
          d={`M 20 100 A ${radius} ${radius} 0 0 1 160 100`}
          fill="none"
          stroke={color}
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
        <text
          x="90"
          y="92"
          textAnchor="middle"
          fontSize="28"
          fontWeight="600"
          fill={color}
        >
          {pct}%
        </text>
      </svg>
      <div className="text-sm text-slate-500 -mt-2">Probability of success</div>
    </div>
  );
}
