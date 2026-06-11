# personal-finance

Single-user, self-hosted personal finance app:

1. **Monarch Money** — read accounts, balances, holdings, transactions; categorize transactions with write-back.
2. **Retirement modeling** — deterministic projections, Monte Carlo with probability of success, withdrawal strategies (4%, Guyton-Klinger guardrails, bond tent), Coast/Lean/Fat FIRE numbers. Hydrates from real portfolio data.
3. **Google Sheets** — read budget assumptions + write Monarch snapshots and projection results back.

Backend: Python 3.11+ + FastAPI. Frontend: SvelteKit + TypeScript + Tailwind, with [LayerChart](https://layerchart.com/) for projections. Local-only for now.

## Quick start

```bash
# 1. Install dependencies
make install

# 2. Configure credentials
cp .env.example .env
# Edit .env: Monarch creds, SHEET_ID, etc.

# 3. (Once) Authorize Google OAuth
. .venv/bin/activate
python scripts/bootstrap_oauth.py

# 4. Run backend + frontend together
make dev
# Backend  → http://localhost:8000  (docs at /docs)
# Frontend → http://localhost:5173
```

Or with Docker:

```bash
docker compose up --build
```

## Layout

```
backend/app/
  main.py  config.py  auth.py
  routers/{health,monarch,sheets,retirement}.py
  services/{monarch_client,sheets_client,cache}.py
  models/{monarch,sheets,retirement}.py
  modeling/{returns,deterministic,monte_carlo,withdrawal,glide_path,fire,tax}.py
  tests/
frontend/src/
  routes/{+page,transactions,retirement,sheets,settings}    # SvelteKit pages
  lib/{components,api,stores}                               # .svelte + .ts
scripts/{bootstrap_oauth,monarch_login}.py
secrets/   (gitignored)
```

## Tests

```bash
make test          # backend + frontend
make test-backend  # pytest
make test-frontend # vitest
```

## Plan

See the implementation plan and roadmap at `docs/PLAN.md`.
