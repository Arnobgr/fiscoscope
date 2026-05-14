# CLAUDE.md — fisc-o-scope

This file is read at the start of every session. Update the session checklist and
runtime discoveries sections before ending a session.

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
- Fully automated (cron pipeline → static JSON → Cloudflare R2 → frontend)
- No backend API — frontend fetches pre-computed static JSON from R2

Full specification: `PRD.md`

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
│   │   └── unedic.py                  # data.gouv.fr Unédic unemployment
│   ├── processors/
│   │   ├── cofog.py                   # COFOG bucketing (productive/redis./admin.)
│   │   ├── kpi_overhead.py            # Administrative Overhead Rate
│   │   ├── kpi_friction.py            # Friction Ratio
│   │   ├── kpi_allocation.py          # Productive Spend Ratio + Pension/Investment
│   │   ├── kpi_outcomes.py            # Spend vs. Outcome + Tax Expenditure
│   │   ├── kpi_sustainability.py      # Fiscal Deficit Trend
│   │   └── kpi_monthly.py             # Monthly Budget Execution
│   ├── publishers/
│   │   └── r2_upload.py               # Upload output JSON to Cloudflare R2
│   ├── data/
│   │   ├── raw/                       # Cached API responses (not committed)
│   │   └── output/                    # Final JSON files before upload (not committed)
│   ├── config.py                      # All constants and environment variables
│   └── run_pipeline.py                # Main entry point (--mode monthly|annual|full)
├── frontend/                          # Phase 2 — Vite + React + Recharts (not started)
├── .env                               # Secrets — never commit (in .gitignore)
├── PRD.md
└── CLAUDE.md                          # ← this file
```

---

## Session implementation plan

Work one session per row. Always start by reading this file and the relevant PRD
sections. Always end by updating the status column and the Runtime discoveries
section below, then commit.

| # | Scope | Key files | Status |
|---|-------|-----------|--------|
| 1 | Scaffolding — structure, config, stubs, CLAUDE.md | `config.py`, `requirements.txt`, `.gitignore`, all stubs | ✅ done |
| 2 | INSEE idBank resolver | `fetchers/insee_idbank_resolver.py` | ✅ done |
| 3 | All fetchers | `insee_bdm.py`, `budget_execution.py`, `oecd.py`, `urssaf.py`, `unedic.py` | ✅ done |
| 4 | Allocation & overhead KPIs | `processors/cofog.py`, `kpi_overhead.py`, `kpi_allocation.py` | ✅ done |
| 5 | Remaining KPIs | `kpi_friction.py`, `kpi_monthly.py`, `kpi_sustainability.py`, `kpi_outcomes.py` | ⬜ pending |
| 6 | Orchestration + publisher | `run_pipeline.py`, `publishers/r2_upload.py` | ⬜ pending |
| 7 | Integration test | Full `python run_pipeline.py --mode full`, fix any API surprises | ⬜ pending |

---

## Session 2 brief — INSEE idBank resolver

**Goal:** `fetchers/insee_idbank_resolver.py` downloads
`correspondance_idbank_dimension.csv` from INSEE, filters it using
`SERIES_SEARCH_RULES`, writes `data/raw/insee_idbanks.json`, and raises a
detailed error for any unresolved or ambiguous series.

**Verification:** Run `python -m fetchers.insee_idbank_resolver` from `backend/`
and confirm all ~27 logical series names resolve to 9-digit idBanks with no
errors.

**Watch out for:**
- Column names in the CSV are only confirmed at runtime (log them on first run).
  Common names: `IDBANK`, `OPERATION`, `SECT_INST`, `COFOG`, `FREQ`, `UNITE`.
- The file uses `;` or `,` as separator — the loader tries both.
- OECD dataset IDs reference the 2025 edition; update when a new edition ships.

---

## Session 3 brief — Fetchers

**Goal:** Implement all five fetcher modules. Each must:
1. Call its API with appropriate pagination/batching.
2. Save the raw response to `data/raw/{source}_{YYYY-MM-DD}.json` before returning.
3. Return a clean `pd.DataFrame`.
4. Handle rate limits (OECD: 20 req/min — add `time.sleep(3)` between calls).

**Verification:** Run each fetcher's `if __name__ == "__main__"` block standalone
and confirm a non-empty DataFrame is returned and the raw file is written.

---

## Session 4 brief — Allocation & overhead KPIs

**Goal:** Implement `cofog.py` (bucket helper), `kpi_overhead.py`, and
`kpi_allocation.py`. Each processor must:
1. Read from `data/raw/` (never re-fetch).
2. Write a JSON file to `data/output/` matching the schema in PRD §5.1.
3. Be deterministic (same raw data → same output, always).

**Verification:** Run each processor standalone, open its output JSON, and
confirm structure matches PRD §5.1 schema.

---

## Session 5 brief — Remaining KPIs

Same contract as Session 4 for `kpi_friction.py`, `kpi_monthly.py`,
`kpi_sustainability.py`, `kpi_outcomes.py`.

Note: PISA data is triennial — interpolate linearly between survey years and
mark interpolated values with `"interpolated": true` in the data points.

---

## Session 6 brief — Orchestration + publisher

**Goal:** Implement `run_pipeline.py` (modes: monthly, annual, full) and
`publishers/r2_upload.py`. After all outputs are written, also write
`data/output/meta.json` (see PRD §9 for schema).

**Verification:** Run `python run_pipeline.py --mode full` with real R2
credentials and confirm all JSON files appear in the bucket and are valid JSON.

---

## Session 7 brief — Integration test

Run the full pipeline against live APIs. Fix any API surprises (changed column
names, SDMX structure changes, pagination edge cases). Document all findings in
Runtime discoveries below.

---

## Runtime discoveries

> Fill this in as sessions progress. These notes persist across sessions.

- **Session 2 — INSEE CDN blocks datacenter IPs.** Both `www.insee.fr` and `api.insee.fr`
  return `403 x-deny-reason: host_not_allowed` from cloud/VPS environments.
  The resolver code is correct; live verification of idBank resolution must be run from a
  residential IP or a French/EU VPS. The `download_mapping()` function already includes a
  `User-Agent` header; if the block persists on the target VPS, try adding a `Referer:
  https://www.insee.fr` header or downloading the mapping CSV manually once and placing it
  at `data/raw/insee_idbank_mapping.csv` (the resolver will use the cache and skip the
  download for up to 30 days).

- **Session 3 — all five data sources block datacenter IPs.** Standalone runs of every
  fetcher returned `403 Forbidden` from this environment: OECD (`sdmx.oecd.org`),
  `data.economie.gouv.fr`, `open.urssaf.fr`, and `data.gouv.fr` — same pattern as INSEE.
  The fetcher code is implemented and its offline paths (`_parse_sdmx_json`, `save_raw`,
  `fetch_ods_records` pagination) are verified, but live verification of all fetchers must
  run from a residential or French/EU IP. Shared helpers `save_raw` and `fetch_ods_records`
  live in `fetchers/__init__.py`. `fetch_all_insee_series` fetches all ~27 idBanks in one
  BDM call (well under the 400-idBank API limit).

- **Session 4 — processors read raw cache, never re-fetch.** Shared helpers live in
  `processors/__init__.py`: `load_insee_series()` rebuilds the logical_name → DataFrame
  mapping from the latest `data/raw/insee_bdm_*.json` plus `insee_idbanks.json` (reuses
  `_parse_sdmx_json` from the fetcher); `annual_values`, `build_latest`, `write_output`,
  `now_iso`, `to_year`, `latest_raw` round it out. `cofog.py` exposes `bucket_cofog()`
  (sums GF01–GF10 into the three buckets per year) and `base_break_note()` (flags the
  2020 base change when the year range spans it). All three KPI processors verified
  deterministic against a synthetic SDMX fixture. **Peer comparison deferred:** per the
  user's call, the Administrative Overhead Rate emits `peers: {}` for now — OECD peer
  series will be wired up in Session 7 when live OECD column layouts are inspectable.
  The Productive Spend and Pension/Investment KPIs are France-only by design (PRD names
  no peer source). `requirements.txt` lists `pandas` — processors need it at runtime.

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
cp ../.env.example .env   # fill in R2 credentials

# Validate idBank resolution first (Session 2+):
python -m fetchers.insee_idbank_resolver

# Full pipeline run (Session 6+):
python run_pipeline.py --mode full
```
