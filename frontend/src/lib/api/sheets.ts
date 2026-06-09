import { api } from "./client";

export interface GlideParams {
  start_equity: number;
  trough_equity: number;
  end_equity: number;
  recovery_years: number;
}

export interface WithdrawalParams {
  initial_rate: number;
  upper_pct: number;
  lower_pct: number;
  adjustment_pct: number;
  prosperity_years: number;
}

export interface CashFlow {
  start_age: number;
  monthly_real: number;
  cola: boolean;
}

export interface OneOff {
  age: number;
  amount_real: number;
}

export interface Assumptions {
  current_age: number | null;
  retirement_age: number | null;
  end_age: number | null;
  annual_spend_real: number | null;
  annual_contributions: number | null;
  swr: number | null;
  equity_mean: number | null;
  equity_sd: number | null;
  bond_mean: number | null;
  bond_sd: number | null;
  correlation: number | null;
  glide_kind: string | null;
  glide_params: GlideParams | null;
  withdrawal_kind: string | null;
  withdrawal_params: WithdrawalParams | null;
  social_security: CashFlow | null;
  pensions: CashFlow[];
  one_offs: OneOff[];
}

export interface SheetsStatus {
  authorized: boolean;
  sheet_id: string | null;
  last_write_at: string | null;
  error: string | null;
}

export interface TargetRow {
  age: number;
  target_net_worth: number;
}

export interface PushResult {
  written_rows: number;
  range: string;
}

export const sheetsApi = {
  status: () => api<SheetsStatus>("/api/sheets/status"),
  assumptions: () => api<Assumptions>("/api/sheets/assumptions"),
  targets: () => api<TargetRow[]>("/api/sheets/targets"),
  readTab: (name: string) => api<unknown[][]>(`/api/sheets/tab/${encodeURIComponent(name)}`),
  pushAccounts: () => api<PushResult>("/api/sheets/push/accounts", { method: "POST" }),
  pushHoldings: () => api<PushResult>("/api/sheets/push/holdings", { method: "POST" }),
  pushProjection: (result: unknown) =>
    api<PushResult>("/api/sheets/push/projection", {
      method: "POST",
      body: JSON.stringify(result),
    }),
};
