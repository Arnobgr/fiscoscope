# Fiscoscope

A dashboard for asking a question the official numbers don't really answer: for every euro France collects in tax, how much actually does anything useful?

Government communications tend to report spending the way a household reports its grocery bill ("we spent €X on education"). That tells you nothing about what the money produced, what fraction was eaten by the apparatus moving it around, or whether other countries get more out of the same euro. Fiscoscope tries to compute that.

The dashboard is built for people who want to look at public finance numbers without someone explaining first why they're good or bad. Mostly: journalists, researchers, and anyone who's tired of budget debates that never cite a denominator.

> **Status:** Backend is feature-complete (all 8 KPIs computing). VPS deployment and the React frontend are still to come. `CLAUDE.md` has the current state.

---

## What it does differently

It reports ratios, not totals. Total spending tells you almost nothing on its own; ratios at least let you compare across years and across countries.

Wherever the data goes back that far, series start in 1995, not just the last election cycle. A lot of trends only show up over decades.

Peers are Germany, the UK, Italy, Spain, the Netherlands, Sweden, and the OECD average. France-only numbers are usually misleading.

The whole pipeline runs on a cron schedule. Nobody is editing spreadsheets by hand, which means the numbers can't drift from whatever INSEE and the OECD publish.

No institutional backing. The code and the methodology are in this repo.

---

## KPIs

| KPI | What it measures |
|---|---|
| Administrative Overhead Rate | Public sector wage bill as % of total public expenditure |
| Friction Ratio | Share of taxes consumed by administrative overhead and debt interest before reaching beneficiaries |
| Productive Spend Ratio | Share of expenditure flowing to productive COFOG functions (infrastructure, R&D, environment) |
| Pension / Investment Ratio | Social protection spending vs. gross fixed capital formation |
| Monthly Budget Execution | Live cumulative revenues, spending, and balance for the current year |
| Fiscal Deficit Trend | Balance and debt as % of GDP, France vs. peers |
| Tax Expenditure Cost | Total cost of *niches fiscales* as % of tax revenues |
| Spend vs. Outcome | Health and education spend indexed against life expectancy and PISA scores |

Full KPI specifications and methodology are in [`docs/PRD.md`](docs/PRD.md) §5.

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│                  VPS (Hetzner)                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Python pipeline (systemd timer)             │  │
│  │  fetch → cache → compute KPIs → write JSON   │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │  FastAPI app (uvicorn, always-on)            │  │
│  │  read-only, CORS-restricted, rate-limited    │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
                       │ HTTPS (Let's Encrypt via <ip>.sslip.io)
                       ▼
┌────────────────────────────────────────────────────┐
│   Cloudflare Pages — Vite + React + Recharts       │
└────────────────────────────────────────────────────┘
```

Two systemd timers drive the pipeline: a monthly one for budget execution, Urssaf, and France Travail, and an annual one for INSEE COFOG, OECD, and the PLF annexes.

The FastAPI app serves `data/output/*.json` over read-only HTTP. No auth, because the data is public anyway. Abuse is bounded by `slowapi` rate limiting and a CORS allowlist, which is enough for a small read-only API.

The frontend is a static site on Cloudflare Pages that fetches from the VPS API at page load.

---

## Data sources

All sources are public. None require an API key.

- **INSEE BDM** for national accounts time series (COFOG, wage bill, GDP, CPI), via the SDMX API. idBanks are resolved at runtime from INSEE's official mapping file.
- **data.economie.gouv.fr** for monthly budget execution (`situations mensuelles budgétaires`) and annual final execution (PLRG).
- **OECD Data Explorer** for COFOG and fiscal indicators on peer countries.
- **open.urssaf.fr** for the private sector wage bill, used in the public/private ratio.
- **data.gouv.fr / France Travail** for monthly unemployment-insurance allocataires.
- **PLF tax expenditure annexes** for the annual cost of tax expenditures.

---

## Quick start

```bash
git clone https://github.com/Arnobgr/french-efficiency-dashboard.git
cd french-efficiency-dashboard/backend

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Validate INSEE idBank resolution first:
python -m fetchers.insee_idbank_resolver

# Full pipeline run (writes data/output/*.json):
python run_pipeline.py --mode full

# Serve the output over HTTP:
ALLOWED_ORIGINS="http://localhost:5173" \
    uvicorn api:app --host 127.0.0.1 --port 8000 --proxy-headers
```

Requirements: Python 3.11+. No secrets needed because all data sources are public.

### Pipeline modes

| Mode | What it runs | Cadence |
|---|---|---|
| `--mode monthly` | Budget execution, Urssaf, France Travail | 1st of each month |
| `--mode annual` | INSEE COFOG, OECD, PLRG, structural KPIs | 1st February (and June, after PLF) |
| `--mode full` | Both | Initial setup or manual refresh |

### API endpoints

- `GET /healthz` — liveness check
- `GET /api/meta` — pipeline run metadata
- `GET /api/kpis` — list of available KPI names
- `GET /api/kpi/{name}` — one KPI's JSON

---

## Repository layout

```
french-efficiency-dashboard/
├── backend/
│   ├── fetchers/        # One module per data source
│   ├── processors/      # One module per KPI
│   ├── data/
│   │   ├── raw/         # Cached API responses (not committed)
│   │   └── output/      # Final JSON served by api.py
│   ├── api.py           # FastAPI read-only server
│   ├── config.py        # Constants and env-var loading
│   └── run_pipeline.py  # Entry point
├── frontend/            # Phase 2 — Vite + React + Recharts
├── docs/
│   ├── PRD.md                  # Full specification
│   ├── runtime-discoveries.md  # Methodology decisions per KPI
│   └── known-gaps.md           # Documented limitations
├── CLAUDE.md
└── README.md
```

---

## Methodology notes

The one place where this project actually editorializes is COFOG bucketing: sorting the 10 COFOG functions into productive, redistributive, and administrative. No official source does this for you, and the choice is debatable. The bucketing lives in `backend/processors/cofog.py` and is repeated in each KPI's output `methodology` field so anyone reading the JSON sees what was assumed.

Education (GF09) and Health (GF07) both mix investment and transfers, so any bucketing of them is approximate. The output flags it. INSEE rebased the national accounts in 2020, which can create a structural break in long series; the processors detect and flag that too.

For per-KPI methodology decisions and the reasoning behind them, see [`docs/runtime-discoveries.md`](docs/runtime-discoveries.md). For things we tried and couldn't make work, see [`docs/known-gaps.md`](docs/known-gaps.md).

---

## Contributing

PRs and issues welcome. A few things that make review easier:

- Target the `dev` branch.
- Keep changes scoped. One KPI or one fetcher per PR is ideal.
- Processors must be deterministic given the same raw input.
- Update `docs/runtime-discoveries.md` when a methodology choice is made or revised.
- For changes that affect KPI computation, include a before/after of the relevant JSON output.

---

## License

[MIT](LICENSE). Do what you want with it, just keep the copyright notice. Commercial use is fine and unrestricted; there are no royalties.

---

## Acknowledgements

Built on top of the open data published by INSEE, the Direction du Budget, the OECD, the Urssaf, France Travail, and data.gouv.fr.
