# Personal Finance App — Implementation Plan

## Context

The repo at `/home/user/personal-finance` is empty except for a README. The goal is a single-user, self-hosted personal finance app that consolidates three workflows currently scattered across Monarch Money, ad-hoc retirement math, and a Google Sheets budget:

1. **Operate Monarch Money** — pull accounts, balances, holdings, and transactions; categorize transactions (with write-back).
2. **Model retirement scenarios** against *real* portfolio data: deterministic projections, Monte Carlo with probability of success, withdrawal strategies (4%, Guyton-Klinger guardrails, bond tent), and Coast/Lean/Fat FIRE numbers.
3. **Integrate with the existing Google Sheets budget** — read assumptions/targets from the sheet, write Monarch snapshots and projection results back into it.

**Confirmed decisions:** Python + FastAPI backend, React + Vite + TS frontend, run locally for now (Docker Compose), single user, on-demand fetch (no DB initially). Outcome: one place to see live finances, categorize transactions, and answer "can I retire?" with the actual portfolio rather than back-of-the-envelope numbers.

## Locked research findings

- **Monarch client:** use `monarchmoneycommunity` (PyPI) — actively maintained fork; original `hammem/monarchmoney` is stale. Async API. Auth uses email + password + `mfa_secret_key` (TOTP seed exported from Monarch Settings → Security). `save_session()` / `load_session()` keep logins durable for months. Key calls: `get_accounts`, `get_account_holdings`, `get_account_history`, `get_transactions`, `get_transaction_categories`, `update_transaction`. No documented rate limits; cache aggressively client-side.
- **Google Sheets:** OAuth *installed-app* flow with cached `token.json` (not service account — your sheet lives in your personal Drive). Libraries: `google-api-python-client` + `google-auth-oauthlib`. Scope `https://www.googleapis.com/auth/spreadsheets`.
- **Retirement math:** write it ourselves with numpy/scipy. No mature Python lib is worth the dependency. Primary MC engine = block-bootstrap of Shiller real return series (preserves correlation + serial autocorrelation); lognormal mode as toggle.
- **Charting:** Recharts (declarative, good TS types). visx reserved for a future fan chart if needed.

## Project layout

```
/home/user/personal-finance
  README.md  docker-compose.yml  .env.example  .gitignore  Makefile  pyproject.toml
  backend/app/
    main.py  config.py  deps.py  auth.py
    routers/{monarch,sheets,retirement,health}.py
    services/{monarch_client,sheets_client,cache}.py
    models/{monarch,sheets,retirement}.py
    modeling/{returns,deterministic,monte_carlo,withdrawal,glide_path,fire,tax}.py
    data/shiller_real_returns.csv
    tests/{unit,integration}/
  frontend/
    package.json  vite.config.ts  tsconfig.json  tailwind.config.ts  index.html
    src/
      main.tsx  App.tsx  router.tsx
      api/{client,monarch,sheets,retirement}.ts
      pages/{Dashboard,Transactions,Retirement,Sheets,Settings}.tsx
      components/{AccountTable,HoldingsTable,TransactionRow,CategoryPicker,
                  ScenarioForm,ProjectionChart,FanChart,SuccessGauge,NumberInput}.tsx
      hooks/{useAccounts,useTransactions,useScenario}.ts
      types/   styles/index.css
  shared/openapi.json
  scripts/{bootstrap_oauth,monarch_login}.py
  secrets/  (gitignored: .env, token.json, mm_session.pickle, client_secrets.json)
```

## Backend modules

- `config.py` — pydantic-settings: `MONARCH_EMAIL/PASSWORD/MFA_SECRET`, `GOOGLE_CLIENT_SECRETS_FILE`, `GOOGLE_TOKEN_FILE`, `SHEET_ID`, `APP_PASSWORD`, `MM_SESSION_FILE`, `CACHE_TTL_SECONDS`.
- `auth.py` — `require_app_auth` dependency; checks `X-App-Password` header against `APP_PASSWORD`. Empty password disables auth (localhost dev).
- `services/monarch_client.py` — singleton wrapping `monarchmoneycommunity`. Loads pickled session if present, else logs in with email+password+TOTP from MFA secret. Maps library dicts → our Pydantic schemas. Concurrency lock on login.
- `services/sheets_client.py` — wraps `googleapiclient.discovery.build('sheets','v4')`. Methods: `read_named_range`, `read_tab`, `write_range`, `batch_update`. Surfaces a clear error pointing at `scripts/bootstrap_oauth.py` when token is missing/expired.
- `services/cache.py` — `cachetools.TTLCache` for Monarch reads (60s transactions, 300s accounts/holdings); `POST /api/cache/clear` flushes.
- `modeling/*` — pure numpy functions, no I/O. Inputs/outputs are dataclasses or numpy arrays. Tested against published reference cases (Trinity Study, Bengen, Kitces examples).

## REST endpoints

**Monarch** (`/api/monarch`):
- `GET /accounts` · `GET /accounts/{id}/holdings` · `GET /accounts/{id}/history?days=N`
- `GET /net_worth` → `{total, by_type}`
- `GET /transactions?start&end&account_id&category_id&limit&offset` · `GET /categories`
- `PATCH /transactions/{id}` body `{category_id?, notes?, tags?}`
- `POST /transactions/categorize_bulk` body `[{id, category_id}, ...]`
- `POST /cache/clear`

**Sheets** (`/api/sheets`):
- `GET /assumptions` · `GET /tab/{name}` · `GET /status`
- `POST /push/accounts` · `POST /push/holdings` · `POST /push/projection` (body = `MonteCarloResult`)

**Retirement** (`/api/retirement`):
- `POST /project/deterministic` body `ScenarioInput`
- `POST /project/monte_carlo` body `ScenarioInput & {trials, method:"bootstrap"|"lognormal"}`
- `POST /fire/numbers` body `{annual_spend, current_age, target_age, swr, real_return}`
- `POST /scenario/from_monarch` — hydrates `current_portfolio` + `asset_allocation` from live holdings

Key schemas (Pydantic):

```python
ScenarioInput {
  current_age, retirement_age, end_age, current_portfolio,
  asset_allocation: {equity, bond, cash},
  annual_contributions, annual_spend_real,
  social_security: {start_age, monthly_real} | None,
  pensions: [...], one_off_cashflows: [...],
  withdrawal_strategy: {kind, params},      # fixed_real | four_percent | guyton_klinger | vpw
  glide_path: {kind, params},                # static | bond_tent | rising_equity
  tax: {enabled, filing_status, taxable_basis_fraction, pretax/roth/taxable shares},
  inflation_rate: float | None,              # None = real-returns mode (default)
  return_assumptions: {equity/bond mean+sd, correlation}  # lognormal mode only
}

MonteCarloResult {
  trials, method, success_rate, median_terminal_real,
  percentiles: {p5,p25,p50,p75,p95},        # per year
  failure_ages_histogram, guardrail_events, scenario_echo
}
```

## Retirement modeling spec

- **Convention:** all math in *real* (inflation-adjusted) dollars by default. Shiller historical series is pre-deflated by CPI.
- **Historical data:** bundle `shiller_real_returns.csv` (S&P 500 total return + 10y Treasury + CPI, 1871–present). Convert to annual real returns at module load.
- **Deterministic** (year-by-year): apply glide-path allocation → expected real return → pre-retirement adds contributions, post-retirement subtracts gross withdrawal + tax. Track balance, withdrawals, taxes, allocation per year.
- **Monte Carlo (bootstrap, default):** vectorized — sample blocks of length 5 from joint (equity, bond) historical draws to preserve correlation + serial autocorrelation. Default 10,000 trials. `bal[t+1] = (bal[t] - withdrawal[t] - tax[t]) * (1 + portfolio_return[t])`. Success = `bal[end_age] > 0`.
- **Withdrawal strategies:**
  - `fixed_real` — constant real spend.
  - `four_percent` — Bengen: 4% of portfolio at retirement, then inflation-indexed.
  - `guyton_klinger` — initial 5%; upper guardrail +20%, lower −20% (Kitces convention); cut 10% / raise 10% on breach; skip cuts in final `prosperity_years`. Record each event.
  - `vpw` — Bogleheads VPW table, age-indexed.
- **Glide paths:** `static`, `bond_tent` (drop to trough at retirement, recover linearly), `rising_equity`.
- **FIRE numbers:** `regular = spend / swr`; `lean = lean_spend * 25`; `fat = fat_spend * 25`; `coast = regular / (1 + real_return)^(target_age − current_age)`.
- **Tax (approximate):** withdraw taxable → pre-tax → Roth. 2025 ordinary + LTCG brackets bundled. Explicitly labeled an approximation.

## Google Sheets contract

Five tabs. App **reads** Assumptions/Targets, **writes** Accounts/Holdings/Projections.

- `Assumptions` (read, all named ranges): `assumption_current_age`, `_retirement_age`, `_end_age`, `_annual_spend_real`, `_annual_contributions`, `_swr`, `_equity_mean/_sd`, `_bond_mean/_sd`, `_correlation`, `_glide_kind`, `_glide_params` (JSON), `_withdrawal_kind`, `_withdrawal_params`, `social_security_table`, `pensions_table`, `one_offs_table`.
- `Targets` (read): `targets_table` — net worth by age for UI comparison.
- `Accounts` (write): `account_id, name, type, subtype, institution, balance_current, currency, updated_at`.
- `Holdings` (write): `account_id, ticker, name, quantity, market_value, cost_basis, asset_class, snapshot_at`.
- `Projections` (write): `year, age, p5, p25, p50, p75, p95, deterministic, withdrawal_p50, success_rate_at_age`.

Ship `docs/sheets_template.md` enumerating every named range + example values so the existing sheet can be adapted.

## Frontend pages

- **Dashboard** `/` — KPI row (net worth, liquid, investments, debt); accounts grouped by type; sparkline per investment account; last-sync + refresh.
- **Transactions** `/transactions` — paginated table; filters (account, category, date, uncategorized-only); inline `CategoryPicker` → `PATCH /transactions/{id}`; bulk-select → `categorize_bulk`. TanStack Query optimistic updates.
- **Retirement** `/retirement` — left: collapsible `ScenarioForm` with "Load from Monarch" and "Load from Sheets" buttons. Right: tabs for Deterministic (line), Monte Carlo (fan chart + success gauge + terminal histogram), FIRE Numbers (cards). "Push to Sheets" writes percentiles to `Projections`.
- **Sheets** `/sheets` — shows parsed assumptions; renders `targets_table`; manual push buttons.
- **Settings** `/settings` — Monarch session status, Google OAuth status, sheet ID input, cache TTL knobs, re-auth + clear-cache buttons.

Stack: React Router v6, TanStack Query v5, Zod for API validation, Tailwind, Recharts, `openapi-typescript` regenerates `src/types/` from `shared/openapi.json`.

## Auth & secrets

- **App auth:** `APP_PASSWORD` env var. Empty = no auth (localhost). Set value → frontend prompts once, stores in `localStorage`, sends `X-App-Password` header.
- **Monarch:** `MONARCH_EMAIL`, `MONARCH_PASSWORD`, `MONARCH_MFA_SECRET` (TOTP seed from Monarch when MFA was enabled). Session pickled to `secrets/mm_session.pickle`.
- **Google:** download Desktop-app `client_secrets.json` from Google Cloud Console into `secrets/`; run `python scripts/bootstrap_oauth.py` once → writes `secrets/token.json`; refresh token persists.
- `secrets/*` and `.env` gitignored; `docker-compose.yml` mounts `./secrets`.

## No-DB caveats (explicitly accepted) + future migration

**Loses without a DB:** historical cross-account net worth chart, categorization audit/undo, fast page loads (3–10s live fetch), background refresh, persisted MC results, cache survives restart.

**Future migration (designed-for, not built):** add Postgres + SQLAlchemy + Alembic; tables `account_snapshot`, `holding_snapshot`, `transaction`, `category_override`, `scenario`, `monte_carlo_run`. APScheduler worker runs `MonarchSync` every N hours. Routers default to DB, `?live=true` forces Monarch. Because routers depend on `services/*` (not the library directly), migration = add `services/repository.py`, switch deps factory. Pydantic models stay as the contract.

## Phased delivery

1. **M1 — Plumbing (1–2d):** repo skeleton, docker-compose, `/api/health`, Vite hello, Makefile, settings, app-password middleware, test scaffolds.
2. **M2 — Monarch read + Dashboard (3–4d):** `monarch_client`, `/accounts`, `/holdings`, `/net_worth`, bootstrap script, Dashboard page, cache, fixture-replay tests.
3. **M3 — Transactions + Sheets read (3–4d):** transactions endpoints + bulk, Transactions page with inline edit, `sheets_client`, OAuth bootstrap, `/sheets/assumptions`, Sheets page.
4. **M4 — Retirement engine + Sheets push (5–6d):** full `modeling/` package with reference-case tests, retirement endpoints, ScenarioForm + ProjectionChart + FanChart + SuccessGauge, push-to-sheet endpoints, Settings page.

(Stretch M5: VPW, regime-based MC, multi-scenario compare, tax refinement.)

## Critical files to create

- `backend/app/services/monarch_client.py` — riskiest external integration (auth, session, schema mapping).
- `backend/app/modeling/monte_carlo.py` — vectorized engine powering the headline feature.
- `backend/app/modeling/withdrawal.py` — Guyton-Klinger + friends; drives every retirement number.
- `backend/app/services/sheets_client.py` — OAuth flow + read/write helpers.
- `frontend/src/pages/Retirement.tsx` — surface where modeling + Monarch + Sheets converge.

## Verification

**Local run.**
1. `cp .env.example .env`, fill creds.
2. `python scripts/bootstrap_oauth.py` (once).
3. `docker compose up` or `make dev`.
4. Visit `http://localhost:5173`.

**Per-feature smoke tests.**
- Monarch: Dashboard net worth matches Monarch web UI; refresh updates `updated_at`.
- Transactions: edit category in app → confirm change in Monarch web; bulk-categorize 5.
- Sheets read: Sheets page shows current assumption values matching the spreadsheet.
- Sheets write: click "Push Accounts" → Accounts tab in sheet updates.
- Retirement deterministic: $1M, 4% rule, 60/40, 30y, ~5% real return → terminal balance matches hand calc.
- Monte Carlo: 10,000 trials, 4% rule, 60/40, 30y → success rate ~95% (Trinity Study sanity check).
- Guardrails: GK at 5% initial > fixed-real 5% on same inputs.

**Automated tests.**
- Backend: `pytest backend/app/tests`. Modeling asserts numeric outputs against published reference cases. Services use replayed fixtures (`pytest-recording`).
- Frontend: `vitest` for components; optional Playwright smoke against recorded backend.
- OpenAPI drift: `make openapi` regenerates `shared/openapi.json` + `frontend/src/types`; CI fails on dirty.
