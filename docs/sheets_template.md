# Google Sheets contract

The app reads from two tabs and writes to three. To adapt your existing sheet, create the named ranges below (Data → Named ranges in Google Sheets).

## Read: `Assumptions` tab

| Named range | Cell type | Example | Meaning |
|---|---|---|---|
| `assumption_current_age` | int | 35 | Your age today |
| `assumption_retirement_age` | int | 55 | Planned retirement age |
| `assumption_end_age` | int | 95 | Plan horizon |
| `assumption_annual_spend_real` | currency | 80000 | Annual real spend in today's dollars |
| `assumption_annual_contributions` | currency | 40000 | Pre-retirement annual contributions |
| `assumption_swr` | percent | 0.04 | Safe withdrawal rate |
| `assumption_equity_mean` | percent | 0.07 | Lognormal equity real return (annual) |
| `assumption_equity_sd` | percent | 0.17 | Equity SD |
| `assumption_bond_mean` | percent | 0.02 | Bond real return |
| `assumption_bond_sd` | percent | 0.06 | Bond SD |
| `assumption_correlation` | float | 0.1 | Stock/bond correlation |
| `assumption_glide_kind` | string | `static`, `bond_tent`, or `rising_equity` | Glide path type |
| `assumption_glide_params` | JSON cell | `{"start_equity":0.8,"trough_equity":0.4,"end_equity":0.6,"recovery_years":10}` | Glide params |
| `assumption_withdrawal_kind` | string | `fixed_real`, `four_percent`, `guyton_klinger`, `vpw` | Withdrawal strategy |
| `assumption_withdrawal_params` | JSON cell | `{"initial_rate":0.05,"upper_pct":0.2,"lower_pct":0.2,"adjustment_pct":0.1,"prosperity_years":15}` | Withdrawal params |
| `social_security_table` | 2-col table | start_age, monthly_real | (3rd col optional: cola true/false) |
| `pensions_table` | 2-3 col table | start_age, monthly_real, cola | One row per pension |
| `one_offs_table` | 2-col table | age, amount_real | One-time cashflows (positive=inflow, negative=outflow) |

## Read: `Targets` tab

| Named range | Format | Meaning |
|---|---|---|
| `targets_table` | 2-col table: `age, target_net_worth` | Net-worth-by-age targets used for UI comparison |

## Write: `Accounts` tab

Overwritten by `POST /api/sheets/push/accounts`. Columns:
`account_id, name, type, subtype, institution, balance_current, currency, updated_at`

## Write: `Holdings` tab

Overwritten by `POST /api/sheets/push/holdings`. Columns:
`account_id, ticker, name, quantity, market_value, cost_basis, asset_class, snapshot_at`

## Write: `Projections` tab

Overwritten by `POST /api/sheets/push/projection` (M4). Columns:
`year, age, p5, p25, p50, p75, p95, deterministic, withdrawal_p50, success_rate_at_age`

## Setup steps

1. Open your sheet → Data → Named ranges → Add range for each of the values above.
2. Make sure tab names match `.env` overrides (`SHEETS_TAB_*`) or use the defaults: `Assumptions`, `Targets`, `Accounts`, `Holdings`, `Projections`.
3. Set `SHEET_ID` in `.env` to the long string in your sheet URL (`docs.google.com/spreadsheets/d/<SHEET_ID>/edit`).
4. Run `python scripts/bootstrap_oauth.py` once to authorize the app.
