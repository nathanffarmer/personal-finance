import { api } from "./client";

export interface AssetAllocation {
  equity: number;
  bond: number;
  cash: number;
}

export interface CashFlowSpec {
  start_age: number;
  monthly_real: number;
  cola: boolean;
}

export interface OneOffCashFlow {
  age: number;
  amount_real: number;
}

export type WithdrawalKind =
  | "fixed_real"
  | "four_percent"
  | "guyton_klinger"
  | "vpw";
export type GlideKind = "static" | "bond_tent" | "rising_equity";

export interface WithdrawalStrategy {
  kind: WithdrawalKind;
  params: Record<string, number>;
}

export interface GlidePath {
  kind: GlideKind;
  params: Record<string, number>;
}

export interface TaxConfig {
  enabled: boolean;
  filing_status: "single" | "mfj";
  taxable_basis_fraction: number;
  pretax_share: number;
  roth_share: number;
  taxable_share: number;
}

export interface ReturnAssumptions {
  equity_mean: number;
  equity_sd: number;
  bond_mean: number;
  bond_sd: number;
  correlation: number;
}

export interface ScenarioInput {
  current_age: number;
  retirement_age: number;
  end_age: number;
  current_portfolio: number;
  asset_allocation: AssetAllocation;
  annual_contributions: number;
  annual_spend_real: number;
  social_security: CashFlowSpec | null;
  pensions: CashFlowSpec[];
  one_off_cashflows: OneOffCashFlow[];
  withdrawal_strategy: WithdrawalStrategy;
  glide_path: GlidePath;
  tax: TaxConfig;
  return_assumptions: ReturnAssumptions;
}

export interface DeterministicProjection {
  years: number[];
  ages: number[];
  balance_real: number[];
  contributions: number[];
  withdrawals: number[];
  taxes: number[];
  equity_share: number[];
  bond_share: number[];
  depleted_age: number | null;
}

export interface PercentileBands {
  p5: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p95: number[];
}

export interface FailureBin {
  age: number;
  count: number;
}

export interface MonteCarloResult {
  trials: number;
  method: "bootstrap" | "lognormal";
  success_rate: number;
  median_terminal_real: number;
  ages: number[];
  percentiles: PercentileBands;
  terminal_p5: number;
  terminal_p50: number;
  terminal_p95: number;
  failure_ages: FailureBin[];
  scenario_echo: ScenarioInput;
}

export interface FireRequest {
  annual_spend: number;
  current_age: number;
  target_age: number;
  swr: number;
  real_return: number;
  lean_factor: number;
  fat_factor: number;
}

export interface FireNumbers {
  lean_fire: number;
  regular_fire: number;
  fat_fire: number;
  coast_fire: number;
  swr_implied_multiple: number;
}

export const retirementApi = {
  deterministic: (scenario: ScenarioInput) =>
    api<DeterministicProjection>("/api/retirement/project/deterministic", {
      method: "POST",
      body: JSON.stringify(scenario),
    }),
  monteCarlo: (
    scenario: ScenarioInput,
    opts: { trials?: number; method?: "bootstrap" | "lognormal"; seed?: number } = {},
  ) =>
    api<MonteCarloResult>("/api/retirement/project/monte_carlo", {
      method: "POST",
      body: JSON.stringify({
        scenario,
        trials: opts.trials ?? 10000,
        method: opts.method ?? "bootstrap",
        seed: opts.seed ?? null,
      }),
    }),
  fire: (req: FireRequest) =>
    api<FireNumbers>("/api/retirement/fire/numbers", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  fromMonarch: (partial: ScenarioInput) =>
    api<ScenarioInput>("/api/retirement/scenario/from_monarch", {
      method: "POST",
      body: JSON.stringify(partial),
    }),
};

export function defaultScenario(): ScenarioInput {
  return {
    current_age: 40,
    retirement_age: 60,
    end_age: 95,
    current_portfolio: 500000,
    asset_allocation: { equity: 0.7, bond: 0.3, cash: 0.0 },
    annual_contributions: 40000,
    annual_spend_real: 80000,
    social_security: null,
    pensions: [],
    one_off_cashflows: [],
    withdrawal_strategy: { kind: "four_percent", params: {} },
    glide_path: { kind: "static", params: {} },
    tax: {
      enabled: false,
      filing_status: "mfj",
      taxable_basis_fraction: 0.5,
      pretax_share: 0.5,
      roth_share: 0.1,
      taxable_share: 0.4,
    },
    return_assumptions: {
      equity_mean: 0.06,
      equity_sd: 0.17,
      bond_mean: 0.02,
      bond_sd: 0.06,
      correlation: 0.1,
    },
  };
}
