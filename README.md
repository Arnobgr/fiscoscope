# Fiscoscope

A dashboard for asking a question the official numbers don't really answer: for every euro France collects in tax, how much actually does anything useful?

Government communications tend to report spending the way a household reports its grocery bill ("we spent €X on education"). That tells you nothing about what the money produced, what fraction was eaten by the apparatus moving it around, or whether other countries get more out of the same euro. Fiscoscope tries to compute that.

The dashboard is built for people who want to look at public finance numbers without someone explaining first why they're good or bad. Mostly: journalists, researchers, and anyone who's tired of budget debates that never cite a denominator.

It is available [here](https://fiscoscope.pages.dev/)

---

## What it does differently

It reports ratios, not totals. Total spending tells you almost nothing on its own; ratios at least let you compare across years and across countries.

Wherever the data goes back that far, series start in 1995, not just the last election cycle. A lot of trends only show up over decades.

Peers are Germany, the UK, Italy, Spain, the Netherlands and Sweden, next to an average labelled for what it is: the EU27 aggregate (Eurostat), the OECD average, or the six countries' unweighted mean. France-only numbers are usually misleading.

The whole pipeline runs on a cron schedule. Nobody is editing spreadsheets by hand, which means the numbers can't drift from whatever INSEE, Eurostat and the OECD publish.

No institutional backing. The code and the methodology are in this repo.

---

## KPIs

| KPI | What it measures |
|---|---|
| Public Wage Bill Share | Public sector wage bill as % of total public expenditure — all public employees (teachers, health staff, police…), not an administrative-overhead measure |
| General Public Services Wage Share | Compensation of staff in general public services (COFOG GF01: executive and legislative bodies, tax and financial administration, foreign affairs, general services) as % of total expenditure — the closest COFOG gets to administrative overhead |
| Friction Ratio | Share of revenue absorbed by the State's core support and sovereign functions (general services, defence, public order) — the running cost of the apparatus, not a measure of waste |
| Public Employment | General-government employment as % of total employment (OECD) |
| Public / Private Wage Bill | Public wage bill relative to the private-sector wage bill (France-only) |
| Fiscal Deficit Trend | Balance and debt as % of GDP, France vs. peers, plus who holds the debt (non-residents, Banque de France, other residents) |
| Deficit by Sub-sector | Balance of central government, local government and social security, in % of GDP and € bn |
| Tax Burden | Taxes and social contributions as % of GDP since 1965 (OECD definition), vs. peers and the OECD average |
| Debt Service Burden | Interest paid on public debt as % of government revenue |
| Social Protection / Investment Ratio | Total social protection spending (COFOG GF10 — pensions, unemployment, family, etc.) vs. gross fixed capital formation, as a multiple |
| Economic Affairs, Environment & Housing Share | Share of expenditure on COFOG GF04–GF06 (economic affairs, environmental protection, housing & community amenities) |
| Old-Age Expenditure | Pensions and old-age care (COFOG GF1002) as % of public spending and of GDP |
| Spend vs. Outcome (health) | Public health spend (% of GDP) and life expectancy at birth, shown as two parallel series (education/PISA not yet available) |
| State Performance Targets Met | Share of the State budget's performance indicators whose target was met, per annual performance report since 2007 (the ministry's own targets and results), with a page listing every indicator's target and result, mission by mission, for 2022–2025 |
| Tax Expenditure Cost | Cost of *niches fiscales* (GTED estimate; lower than the official PLF figure) as % of revenue |
| Monthly Budget Execution | Live cumulative revenues, spending, and balance for the current year |

The original KPI specifications are in [`docs/PRD.md`](docs/PRD.md) §5; the indicators added since are specified in [`docs/roadmap.md`](docs/roadmap.md).

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│                  VPS (Hetzner)                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Python pipeline (cron, Docker Compose)      │  │
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

Two cron jobs drive the pipeline: a monthly one for budget execution, Urssaf, and France Travail, and an annual one for INSEE, Eurostat, the OECD, and the GTED tax-expenditure data.

The FastAPI app serves `data/output/*.json` over read-only HTTP. No auth, because the data is public anyway. Abuse is bounded by `slowapi` rate limiting and a CORS allowlist, which is enough for a small read-only API.

The frontend is a static site on Cloudflare Pages that fetches from the VPS API at page load.

---

## Data sources

All sources are public. None require an API key.

- **INSEE BDM** for France's quarterly national accounts (wage bill, expenditure, balance, interest), GDP and Maastricht debt, via the SDMX API. idBanks are resolved at runtime from INSEE's official mapping file.
- **Eurostat** for government accounts on one basis from 1995, for France and its EU peers: spending by COFOG function and transaction, balances by sub-sector, interest and revenue, and who holds the debt. Eurostat no longer covers the UK, so the UK appears only on OECD-sourced charts.
- **data.economie.gouv.fr** for monthly budget execution (`situations mensuelles budgétaires`) and annual final execution (PLRG).
- **OECD Data Explorer**: Government at a Glance (peer deficit, debt and wage bill; public employment), Revenue Statistics (tax-to-GDP since 1965), and Health Statistics (life expectancy).
- **open.urssaf.fr** for the private sector wage bill, used in the public/private ratio.
- **data.gouv.fr / France Travail** for monthly unemployment-insurance allocataires.
- **GTED (Global Tax Expenditures Database)** for the annual cost of tax expenditures — a CC-BY academic compilation of France's PLF *Voies et Moyens* tome II (not the official annex directly, and narrower in scope than it).

---

## Quick start

```bash
git clone https://github.com/Arnobgr/fiscoscope.git
cd fiscoscope/backend

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
| `--mode annual` | INSEE, Eurostat, OECD, GTED, PLRG, State performance indicators, structural KPIs | 1st February, June and November (June and November follow Eurostat's April and October updates) |
| `--mode full` | Both | Initial setup or manual refresh |

### API endpoints

- `GET /healthz` — liveness check
- `GET /api/meta` — pipeline run metadata
- `GET /api/kpis` — list of available KPI names
- `GET /api/kpi/{name}` — one KPI's JSON

---

## Repository layout

```
fiscoscope/
├── backend/
│   ├── fetchers/        # One module per data source
│   ├── processors/      # KPI computations (one module per KPI family)
│   ├── data/
│   │   ├── raw/         # Cached API responses (not committed)
│   │   └── output/      # Final JSON served by api.py
│   ├── api.py           # FastAPI read-only server
│   ├── config.py        # Constants and env-var loading
│   └── run_pipeline.py  # Entry point
├── frontend/            # Vite + React + Recharts (Cloudflare Pages)
├── docs/
│   ├── PRD.md                  # Full specification
│   ├── roadmap.md              # Forward plan and vetted data sources
│   ├── runtime-discoveries.md  # Methodology decisions per KPI
│   └── known-gaps.md           # Documented limitations
├── CLAUDE.md
└── README.md
```

---

## Methodology notes

The project tries not to tell you whether a number is good or bad. Each KPI is named after what it measures — usually a COFOG function or a national-accounts aggregate — rather than a judgement like "productive" or "administrative", and the year-on-year arrow is coloured only where a rise is uncontroversially better or worse.

KPIs in euros or in % of GDP (deficit and debt, deficit by sub-sector, debt interest, pensions, health spending, tax burden, tax expenditure) also have a "€ par habitant" view: the annual amount divided by INSEE's average population and converted to constant euros of the latest full year with INSEE's consumer price index (from 1996). That view is France-only, because comparing euros per head across countries would need purchasing-power corrections; cross-country comparisons stay on the ratios.

Functional breakdowns (COFOG) come from Eurostat on a single basis from 1995, for France and its peers alike, so long series have no change of source. Each KPI's sources and methodology are shown on its page and repeated in its JSON output (`source`, `methodology`), so anyone reading the data sees what was assumed.

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

[MIT](LICENSE).

---

## Acknowledgements

Built on top of the open data published by INSEE, Eurostat, the Direction du Budget, the OECD, the Urssaf, France Travail, and data.gouv.fr.
