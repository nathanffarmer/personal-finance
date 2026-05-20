import {
  GlideKind,
  ScenarioInput,
  WithdrawalKind,
} from "@/api/retirement";
import { NumberInput, PercentInput } from "./NumberInput";

const WITHDRAWAL_KINDS: { value: WithdrawalKind; label: string }[] = [
  { value: "fixed_real", label: "Fixed real spend" },
  { value: "four_percent", label: "4% rule (Bengen)" },
  { value: "guyton_klinger", label: "Guyton-Klinger guardrails" },
  { value: "vpw", label: "Variable percentage (VPW)" },
];

const GLIDE_KINDS: { value: GlideKind; label: string }[] = [
  { value: "static", label: "Static allocation" },
  { value: "bond_tent", label: "Bond tent" },
  { value: "rising_equity", label: "Rising equity" },
];

export function ScenarioForm({
  scenario,
  onChange,
}: {
  scenario: ScenarioInput;
  onChange: (s: ScenarioInput) => void;
}) {
  const patch = (p: Partial<ScenarioInput>) => onChange({ ...scenario, ...p });
  const alloc = scenario.asset_allocation;

  return (
    <div className="space-y-5 text-sm">
      <Section title="Timeline">
        <div className="grid grid-cols-3 gap-2">
          <NumberInput
            label="Current age"
            value={scenario.current_age}
            onChange={(v) => patch({ current_age: v })}
          />
          <NumberInput
            label="Retire age"
            value={scenario.retirement_age}
            onChange={(v) => patch({ retirement_age: v })}
          />
          <NumberInput
            label="End age"
            value={scenario.end_age}
            onChange={(v) => patch({ end_age: v })}
          />
        </div>
      </Section>

      <Section title="Portfolio">
        <div className="grid grid-cols-2 gap-2">
          <NumberInput
            label="Current portfolio"
            value={scenario.current_portfolio}
            step={1000}
            onChange={(v) => patch({ current_portfolio: v })}
          />
          <NumberInput
            label="Annual contributions"
            value={scenario.annual_contributions}
            step={1000}
            onChange={(v) => patch({ annual_contributions: v })}
          />
          <NumberInput
            label="Annual spend (real)"
            value={scenario.annual_spend_real}
            step={1000}
            onChange={(v) => patch({ annual_spend_real: v })}
          />
        </div>
      </Section>

      <Section title="Asset allocation">
        <div className="grid grid-cols-3 gap-2">
          <PercentInput
            label="Equity"
            value={alloc.equity}
            onChange={(v) =>
              patch({ asset_allocation: { ...alloc, equity: v } })
            }
          />
          <PercentInput
            label="Bond"
            value={alloc.bond}
            onChange={(v) => patch({ asset_allocation: { ...alloc, bond: v } })}
          />
          <PercentInput
            label="Cash"
            value={alloc.cash}
            onChange={(v) => patch({ asset_allocation: { ...alloc, cash: v } })}
          />
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Sum: {((alloc.equity + alloc.bond + alloc.cash) * 100).toFixed(0)}%
        </p>
      </Section>

      <Section title="Withdrawal strategy">
        <select
          value={scenario.withdrawal_strategy.kind}
          onChange={(e) =>
            patch({
              withdrawal_strategy: {
                kind: e.target.value as WithdrawalKind,
                params: scenario.withdrawal_strategy.params,
              },
            })
          }
          className="w-full border border-slate-300 rounded px-2 py-1"
        >
          {WITHDRAWAL_KINDS.map((w) => (
            <option key={w.value} value={w.value}>
              {w.label}
            </option>
          ))}
        </select>
        {scenario.withdrawal_strategy.kind === "guyton_klinger" && (
          <div className="grid grid-cols-2 gap-2 mt-2">
            <PercentInput
              label="Initial rate"
              value={scenario.withdrawal_strategy.params.initial_rate ?? 0.05}
              onChange={(v) =>
                patch({
                  withdrawal_strategy: {
                    ...scenario.withdrawal_strategy,
                    params: {
                      ...scenario.withdrawal_strategy.params,
                      initial_rate: v,
                    },
                  },
                })
              }
            />
          </div>
        )}
        {scenario.withdrawal_strategy.kind === "four_percent" && (
          <PercentInput
            label="Initial rate"
            value={scenario.withdrawal_strategy.params.initial_rate ?? 0.04}
            onChange={(v) =>
              patch({
                withdrawal_strategy: {
                  ...scenario.withdrawal_strategy,
                  params: {
                    ...scenario.withdrawal_strategy.params,
                    initial_rate: v,
                  },
                },
              })
            }
          />
        )}
      </Section>

      <Section title="Glide path">
        <select
          value={scenario.glide_path.kind}
          onChange={(e) =>
            patch({
              glide_path: {
                kind: e.target.value as GlideKind,
                params: scenario.glide_path.params,
              },
            })
          }
          className="w-full border border-slate-300 rounded px-2 py-1"
        >
          {GLIDE_KINDS.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
      </Section>

      <Section title="Return assumptions (lognormal mode)">
        <div className="grid grid-cols-2 gap-2">
          <PercentInput
            label="Equity mean"
            value={scenario.return_assumptions.equity_mean}
            onChange={(v) =>
              patch({
                return_assumptions: {
                  ...scenario.return_assumptions,
                  equity_mean: v,
                },
              })
            }
          />
          <PercentInput
            label="Equity SD"
            value={scenario.return_assumptions.equity_sd}
            onChange={(v) =>
              patch({
                return_assumptions: {
                  ...scenario.return_assumptions,
                  equity_sd: v,
                },
              })
            }
          />
          <PercentInput
            label="Bond mean"
            value={scenario.return_assumptions.bond_mean}
            onChange={(v) =>
              patch({
                return_assumptions: {
                  ...scenario.return_assumptions,
                  bond_mean: v,
                },
              })
            }
          />
          <PercentInput
            label="Bond SD"
            value={scenario.return_assumptions.bond_sd}
            onChange={(v) =>
              patch({
                return_assumptions: {
                  ...scenario.return_assumptions,
                  bond_sd: v,
                },
              })
            }
          />
        </div>
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4 className="font-semibold text-xs uppercase tracking-wide text-slate-500 mb-2">
        {title}
      </h4>
      {children}
    </div>
  );
}
