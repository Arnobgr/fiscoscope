# CLAUDE.md — fisc-o-scope

This file is read at the start of every session. It holds only what's needed to
start work. The build history and the blocked-work reference live in `docs/`:

- **Session-by-session runtime discoveries** (methodology decisions behind every
  KPI; append new session notes here, not in this file): `docs/runtime-discoveries.md`
- **Known gaps & blocked attempts** (don't re-attempt without new upstream data):
  `docs/known-gaps.md`
- **Full specification:** `PRD.md`

---

## Behavioral guidelines (Karpathy)

These four principles apply to every session, every file, every change.

### 1. Think before coding
Surface assumptions and confusion upfront — don't assume, don't hide confusion,
surface trade-offs. When a task has multiple plausible interpretations, name them
and ask which is intended rather than choosing silently.

### 2. Simplicity first
Write minimal code that solves exactly what was asked. No features beyond scope.
No abstractions for single-use code. If 200 lines could be 50, rewrite it. Avoid
speculative error handling for scenarios that cannot happen.

### 3. Surgical changes
When editing existing code, modify only what is necessary. Do not improve adjacent
code, comments, or formatting unless that is the task. Match the existing style.
Remove only imports/variables that your changes made unused — not pre-existing dead
code unless explicitly asked.

### 4. Goal-driven execution
Transform every task into a verifiable objective with clear success criteria. For
multi-step work, state a brief plan upfront with explicit verification points for
each step. Bias toward caution over speed.

---

## Project overview

**fisc-o-scope** — an open-source dashboard measuring the productivity and
efficiency of the French public administration using publicly available fiscal data.

- Ratio-focused (efficiency per euro, not raw accounting figures)
- Longitudinal (1995–present time series)
- Peer-benchmarked (France vs. DE, GB, IT, ES, NL, SE, OECD average)
- Fully automated (cron pipeline → static JSON → FastAPI → frontend)
- Backend API: a small FastAPI app on the VPS serves pre-computed static JSON
  over read-only HTTP; the frontend (Cloudflare Pages) fetches it. HTTPS via an
  `<ip>.sslip.io` Let's Encrypt cert (no custom domain).

---

## Current status

Backend is **feature-complete**: all 8 PRD KPIs (§5.2–5.9) plus 2 extra (wage
ratio, debt service) compute `status: ok`; `budget_plrg` is the only by-design
`skipped` step. Output is served by `backend/api.py` (FastAPI; the old R2 upload
was retired in Session E).

Remaining **build** work (not blocked — just not started):
- First live VPS deployment of the FastAPI app (`docs/superpowers/plans/2026-05-22-vps-deployment.md`).
- Frontend, Phase 2 — Vite + React + Recharts (`docs/superpowers/plans/2026-05-22-frontend-implementation.md`).

For the asterisks on "complete" (orphaned inputs, peer-benchmarking limits,
upstream blocks) see `docs/known-gaps.md`. For why each KPI is built the way it
is, see `docs/runtime-discoveries.md`.

---

## Repository layout

```
french-efficiency-dashboard/
├── backend/
│   ├── fetchers/
│   │   ├── insee_idbank_resolver.py   # Step 0 of pipeline — resolves idBanks
│   │   ├── insee_bdm.py               # INSEE BDM SDMX API
│   │   ├── budget_execution.py        # data.economie.gouv.fr monthly execution
│   │   ├── oecd.py                    # OECD Data Explorer SDMX API
│   │   ├── urssaf.py                  # open.urssaf.fr private wage bill
│   │   └── france_travail.py          # data.gouv.fr France Travail unemployment
│   ├── processors/
│   │   ├── cofog.py                   # COFOG bucketing (productive/redis./admin.)
│   │   ├── kpi_overhead.py            # Administrative Overhead Rate
│   │   ├── kpi_friction.py            # Friction Ratio
│   │   ├── kpi_allocation.py          # Productive Spend Ratio + Pension/Investment
│   │   ├── kpi_outcomes.py            # Spend vs. Outcome + Tax Expenditure
│   │   ├── kpi_sustainability.py      # Fiscal Deficit Trend
│   │   └── kpi_monthly.py             # Monthly Budget Execution
│   ├── api.py                         # FastAPI read-only server for data/output/*.json
│   ├── data/
│   │   ├── raw/                       # Cached API responses (not committed)
│   │   └── output/                    # Final JSON files served by api.py (not committed)
│   ├── config.py                      # All constants and environment variables
│   └── run_pipeline.py                # Main entry point (--mode monthly|annual|full)
├── frontend/                          # Phase 2 — Vite + React + Recharts (not started)
├── .env                               # Environment settings (ALLOWED_ORIGINS, RATE_LIMIT) — never commit
├── PRD.md
└── CLAUDE.md                          # ← this file
```

---

## Key constraints (from PRD §12)

1. **idBank resolution is runtime-only** — never hardcode idBanks; always load
   from `data/raw/insee_idbanks.json`.
2. **OECD dataset IDs** reference the 2025 edition — update when 2027 ships.
3. **Raw data must be cached** — every fetcher saves its response before processing.
4. **Reproducibility** — processors are deterministic; same raw → same output.
5. **COFOG base change 2020** — detect and flag structural breaks in output metadata.
6. **No secrets in git** — `.env` is gitignored; all credentials via env vars.

---

## Running the pipeline locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# No secrets needed — all data sources are public. The API reads optional
# ALLOWED_ORIGINS / RATE_LIMIT from the environment.

# Validate idBank resolution first (Session 2+):
python -m fetchers.insee_idbank_resolver

# Full pipeline run (Session 6+):
python run_pipeline.py --mode full

# Serve the output over HTTP (separate always-on process):
ALLOWED_ORIGINS="https://your-frontend.pages.dev" \
    uvicorn api:app --host 127.0.0.1 --port 8000 --proxy-headers
```
