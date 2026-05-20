import { api } from "./client";

export interface Account {
  id: string;
  name: string;
  type: "depository" | "investment" | "credit" | "loan" | "real_estate" | "other";
  subtype: string | null;
  institution: string | null;
  balance_current: number;
  balance_available: number | null;
  currency: string;
  is_hidden: boolean;
  updated_at: string | null;
}

export interface Holding {
  account_id: string;
  ticker: string | null;
  name: string;
  quantity: number;
  market_value: number;
  cost_basis: number | null;
  asset_class: "us_equity" | "intl_equity" | "bond" | "cash" | "alt" | "unknown";
}

export interface BalancePoint {
  date: string;
  balance: number;
}

export interface NetWorthByType {
  cash: number;
  investment: number;
  credit: number;
  loan: number;
  real_estate: number;
  other: number;
}

export interface NetWorth {
  total: number;
  by_type: NetWorthByType;
}

export interface Category {
  id: string;
  name: string;
  group: string | null;
  icon: string | null;
}

export interface Transaction {
  id: string;
  date: string;
  amount: number;
  merchant: string;
  description: string;
  account_id: string;
  category_id: string | null;
  category_name: string | null;
  pending: boolean;
  notes: string | null;
  tags: string[];
}

export const monarchApi = {
  accounts: () => api<Account[]>("/api/monarch/accounts"),
  holdings: (id: string) => api<Holding[]>(`/api/monarch/accounts/${id}/holdings`),
  history: (id: string) => api<BalancePoint[]>(`/api/monarch/accounts/${id}/history`),
  netWorth: () => api<NetWorth>("/api/monarch/net_worth"),
  transactions: (params: {
    start?: string;
    end?: string;
    account_id?: string[];
    category_id?: string[];
    limit?: number;
    offset?: number;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.start) q.set("start", params.start);
    if (params.end) q.set("end", params.end);
    for (const a of params.account_id ?? []) q.append("account_id", a);
    for (const c of params.category_id ?? []) q.append("category_id", c);
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    if (params.offset !== undefined) q.set("offset", String(params.offset));
    return api<Transaction[]>(`/api/monarch/transactions?${q.toString()}`);
  },
  categories: () => api<Category[]>("/api/monarch/categories"),
  updateTransaction: (id: string, payload: { category_id?: string; notes?: string }) =>
    api<Transaction>(`/api/monarch/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  categorizeBulk: (items: { id: string; category_id: string }[]) =>
    api<{ updated: number }>("/api/monarch/transactions/categorize_bulk", {
      method: "POST",
      body: JSON.stringify(items),
    }),
  clearCache: () => api<{ cleared: number }>("/api/monarch/cache/clear", { method: "POST" }),
  status: () =>
    api<{
      credentials_configured: boolean;
      mfa_secret_configured: boolean;
      session_cached: boolean;
      logged_in: boolean;
    }>("/api/monarch/status"),
};

export function formatCurrency(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}
