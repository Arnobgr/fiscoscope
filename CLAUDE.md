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
│   │   └── france_travail.py          # data.gouv.fr France Travail unemployment
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
| 3 | All fetchers | `insee_bdm.py`, `budget_execution.py`, `oecd.py`, `urssaf.py`, `france_travail.py` | ✅ done |
| 4 | Allocation & overhead KPIs | `processors/cofog.py`, `kpi_overhead.py`, `kpi_allocation.py` | ✅ done |
| 5 | Remaining KPIs | `kpi_friction.py`, `kpi_monthly.py`, `kpi_sustainability.py`, `kpi_outcomes.py` | ✅ done |
| 6 | Orchestration + publisher | `run_pipeline.py`, `publishers/r2_upload.py` | ✅ done |
| 7 | Integration test | Full `python run_pipeline.py --mode full`, fix any API surprises | ✅ done |

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

- **Session 5 — three PRD/data mismatches resolved with the user.** (1) *Friction Ratio*:
  PRD §5.3 names "total taxes collected" as the denominator, but no tax-revenue series is
  resolved in the INSEE idBanks. Per the user's call, total revenue is derived as
  `total_apu_expenditure + fiscal_balance (B9)`; friction spend is the administrative COFOG
  bucket (GF01+GF02+GF03), with debt interest left inside GF01 rather than added again.
  France-only. (2) *kpi_sustainability* and *kpi_outcomes* are OECD-heavy — same deferral as
  Session 4's overhead peers. `kpi_sustainability` emits the France deficit series (B9/GDP)
  with `peers: {}` and omits debt; `kpi_outcomes` emits a well-formed placeholder
  (`france: []`, `peers: {}`) since its outcome side (life expectancy, PISA) is entirely
  OECD-sourced — both to be wired up in Session 7. (3) *Tax Expenditure* (§5.8) has no
  fetcher module (the five fetchers are INSEE/budget/OECD/urssaf/france_travail); per the user,
  `compute_tax_expenditure()` raises `NotImplementedError` until a PLF "dépenses fiscales"
  fetcher (PRD §3.6) is built — `run_pipeline.py` must account for this gap in Session 6.
  **kpi_monthly** reshapes the cached `budget_execution` ODS dataset; its OpenDataSoft
  field names are only confirmed at runtime, so `_resolve_column` raises a detailed,
  resolver-style error listing the actual columns if the candidate `*_FIELDS` lists don't
  match — adjust them on the first live run. All four processors verified deterministic
  against synthetic SDMX + budget-execution fixtures.

---

- **Session 6 — orchestrator is fail-soft; one outage doesn't abort the run.** Each
  fetcher and processor runs inside `_run_step`, which records `status: ok | skipped |
  error` (with the exception message) into the `meta.json` `sources` block but never
  re-raises. `kpi_tax_expenditure` therefore lands as `skipped` rather than crashing the
  pipeline (Session 5 gap). `run_pipeline.py` adds a `--no-upload` flag for local dry runs
  and calls `load_dotenv()` from the repo-root `.env` *before* importing `config`, so R2
  credentials are picked up at config-load time. `publishers/r2_upload.py` validates all
  four R2 env vars upfront and raises a single `RuntimeError` listing the missing names —
  no boto3 stack trace if `.env` is empty. Verified end-to-end with `python run_pipeline.py
  --mode full --no-upload`: from this datacenter IP every live source 403s (expected per
  Sessions 2/3), `compute_outcomes` writes its placeholder, and `meta.json` is well-formed
  with all 16 steps recorded. **`meta.json` schema deviates slightly from PRD §9**: it
  reports `status` per step (one entry per fetcher *and* per processor) rather than per
  data source only, and omits `latest_year`/`latest_month` extraction. The richer
  per-step status was more useful while every source is still 403'ing; revisit in
  Session 7 once live runs make `latest_year` cheap to compute.

---

- **Session 7 prep (2026-05-15) — IP block lifted on this VPS; four upstream breakages
  found, split into follow-up sessions.** Datacenter `403`s are gone from every host
  (INSEE, OECD, data.gouv.fr, data.economie.gouv.fr, open.urssaf.fr), so the original
  Session 2/3 blockers no longer apply. Standalone re-runs surfaced four real upstream
  changes between the prior sessions and today: (1) **INSEE** migrated the idBank
  mapping from a flat CSV to a monthly ZIP (`YYYYMM_correspondance_idbank_dimension.zip`)
  whose CSV has 4 columns (`famille,idbank,list_mod,list_var`) with dimensions packed
  positionally into `list_mod` and names in `list_var`; dimension names also changed
  (`FREQ`→`PERIODICITE`, `SECT_INST`→`SECT-INST`, `COFOG`→`FONCTION`). (2) **OECD**
  `DSD_GOV_COFOG@DF_GOV_COFOG_2025` and `DSD_GOV_TRANSACTION@DF_GOV_TRANSACTION_2025`
  now require 8 key dimensions instead of 5 (`422 Not enough key values in query`);
  the endpoint is reachable, only the filter string needs rebuilding. (3) **France Travail**
  assurance-chômage dataset (id `561fa8bbc751df54a1cdbb48`) no longer matches the
  old keyword query and resources are **XLSX only**, no CSV. (4) `urssaf`
  and `budget_execution` work as-is (verified: 116 Urssaf rows; budget data through
  03/2026). **This session's prep work**: centralized a generic Firefox UA in
  `fetchers/__init__.py` (`DEFAULT_HEADERS`) and threaded it through every `requests.get`
  call (replacing the custom `fisc-o-scope/1.0` UA, which is more fingerprintable);
  pinned `requirements.txt` to exact versions ≥ 1 week old
  (`requests==2.33.1`, `pandas==2.3.3`, `boto3==1.43.6`, `python-dotenv==1.2.2`);
  cached the INSEE ZIP + extracted CSV at `data/raw/insee_idbank_mapping.{zip,csv}`
  so Session 7a can develop offline. **Plan for sessions 7a–7d** lives in
  `docs/superpowers/plans/2026-05-15-upstream-data-source-fixes.md`.

---

- **Session 7a — INSEE resolver ported to the new ZIP / positional schema.** The new
  mapping CSV has only 4 columns (`famille`, `idbank`, `list_mod`, `list_var`); every
  dimension is decoded by zipping `list_var.split('.')` with `list_mod.split('.')` per
  row. `download_mapping()` now scrapes
  `https://www.insee.fr/fr/information/2862759` for the latest
  `*_correspondance_idbank_dimension.zip` link and extracts the CSV from the ZIP.
  **Final SERIES_SEARCH_RULES surprises** (worth flagging because they're not derivable
  from the dimension-rename table alone):
    1. The `DEP-APU` family has **no `B9` or `D41` OPERATION** — only aggregate codes
       (`D1, D3, D4, D6M, D7, D9, OTE, P2, P5K2, D2951, SO`). `fiscal_balance` and
       `debt_interest` are resolved against `famille = "CNA-2014-CSI"` (sector accounts
       satellite) using `OPERATION=B9NF` / `D41` with `COMPTE=EA` (employments) — not
       `DEP-APU`.
    2. `FONCTION` accepts a synthetic value **`FONTOTAL`** that aggregates over all
       COFOG functions; APU-wide totals (D1, P5K2, D6M, OTE, …) need `FONCTION=FONTOTAL`
       to match a single row, not an empty/`SO` value.
    3. PRD's `OPERATION=P51` (gross fixed capital formation) appears in `DEP-APU` as
       **`P5K2`** (P5 + K2 aggregate); `OPERATION=P51` only exists in CNT-quarterly
       families. We map `public_investment → P5K2` from `CNA-2014-DEP-APU`.
    4. PRD's `social_benefits ≡ D62` is mapped to **`D6M`** in `CNA-2014-DEP-APU`
       (D6M = social benefits in cash + in-kind via market producers, the DEP-APU
       aggregate). A pure-D62 alternative is available from `CNA-2014-CSI` if a future
       processor needs the strict ESA D.62 series.
    5. `gdp_nominal` uses `famille = "CNA-2020-PIB"` (newest active base; CNA-2014-PIB
       has `SERIE_ARRETEE=TRUE`) with `PRIX_REF=VAL`, `NATURE=VALEUR_ABSOLUE`,
       `UNITE=EUROS_COURANTS`.
    6. `cpi` lives in `famille = "IPC-2025"`. It has no `OPERATION` dimension — match
       on `INDICATEUR=IPC`, `COICOP2018=00`, `PRIX_CONSO=00`, `NATURE=INDICE`,
       `MENAGES_IPC=ENSEMBLE`, `ZONE_GEO=FE`, `CORRECTION=BRUT`, `PERIODICITE=M`.
  All 19 logical series resolve to a single 9-digit idBank; `insee_idbanks.json` written
  successfully from the cached ZIP. Live-fetch path (metadata scrape + ZIP download)
  unverified in this session because the cache was warm — first scheduled refresh in
  ≤30 days will exercise it.

---

- **Session 7b — OECD 2025-edition DSDs use 8 dimensions; "% of GDP" code renamed.**
  Both Government-at-a-Glance 2025 dataflows now expose 8 key dimensions (was 5) in
  this order, confirmed live against the SDMX structure endpoint
  (`/public/rest/dataflow/OECD.GOV.GIP/<dsd>/latest?references=descendants`):
    - `DSD_GOV_COFOG`:       `FREQ . REF_AREA . MEASURE . UNIT_MEASURE . SECTOR . EXPENDITURE . EDITION . CATEGORY`
    - `DSD_GOV_TRANSACTION`: `FREQ . REF_AREA . MEASURE . UNIT_MEASURE . SECTOR . TRANSACTION . EDITION . CATEGORY`
  Filter strings now use 7 dots (`A.{peers}..PT_B1GQ....`). The plan's `PT_GDP` value
  was wrong: the actual SDMX `UNIT_MEASURE` code for "% of GDP" is **`PT_B1GQ`**
  (B1GQ is the SDMX concept for GDP at market prices). Other UNIT_MEASURE values
  available are `PT_OTE_S13*` (% of expenditure), `PT_PCOS_S13`, `PT_TAX_REV`,
  `USD_PPP`, etc. — switch as needed for non-ratio KPIs. Both fetchers verified
  live: COFOG → 4025 rows × 32 columns, fiscal → 1764 rows × 32 columns; raw cached
  at `data/raw/oecd_{cofog,fiscal}_2026-05-16.json`. When the 2027 edition ships,
  re-run the structure-discovery probe — dimension order is not guaranteed stable
  between editions.

---

- **Session 7c — France Travail fetcher: switched to XLSX reader.** Dataset
  `561fa8bbc751df54a1cdbb48` ("Allocataires de l'assurance chômage") is now
  XLSX-only and its title no longer contains the old keyword, so the
  prior search-based resolver returns nothing. Resolver now hits the data.gouv.fr dataset endpoint
  directly and picks the national XLSX resource (`format=excel`, URL
  contains `indem`, title without `region`). The published URL
  (`https://statistiques.francetravail.org/indem/teleindemalloc`) redirects
  cleanly 302→301→200 to a `pr-rooms.com` CDN — no cookies, no anti-bot,
  `DEFAULT_HEADERS` alone is enough; no `Referer` needed beyond what
  `data.gouv.fr` already provides via the resource record. The XLSX
  (`backend/data/raw/france_travail_indemnisation.xlsx`, ~630 KB) has 12
  sheets. The PRD-relevant one is **"Brut France"** (France métropolitaine
  + Dom, données brutes — the CVS variants are seasonally adjusted; "Brut
  France métropolitaine" excludes the Dom). Header layout is unusual: row 3
  carries top-level groupings (AC / ETAT / FORMATION / PRE RETRAITE /
  ASSURANCE CHOMAGE / ETAT / AUTRES), row 4 is blank, **row 5 carries the
  48 individual allocation columns** (header offset = 5, 0-indexed). Data
  starts row 6 and runs monthly from 2006-01 through the most recent month
  (verified: 240 rows × 49 cols). The sheet exposes **`indemnisés` per
  allocation**, not `allocataires` in the strict sense; it includes
  a final **`Total (1+2+3)`** column that aggregates all allocations and
  is the right column to read for the headline national indemnisés count.
  The fetcher returns the full wide DataFrame (no aggregation) so future
  KPIs can slice by allocation type if needed. `openpyxl==3.1.5` pinned
  (released 2024-06-28; PyPI's `pip index` confirms it's the latest stable
  and 22 months old, well past the project's ≥1-week pinning rule).

---

- **Session 7d — full-pipeline integration; three upstream changes patched.**
  Every step now reports `status: ok` except the two by-design `skipped`
  entries (`kpi_tax_expenditure`, `budget_plrg`). Final fixes:
    1. **INSEE BDM dropped JSON entirely.** `api.insee.fr/series/BDM/V1/data/...`
       no longer honours the `?format=sdmx-json` query param (returns `400
       "Unknown query parameter 'format'"`) and ignores `Accept:
       application/...+json` content negotiation, always serving SDMX 2.1
       `StructureSpecificData` XML. Rewrote `fetchers/insee_bdm.py` to drop the
       `format` param, parse the XML with `xml.etree.ElementTree`, and save
       pre-parsed `[{idbank, date, value}]` records (instead of the raw API
       blob). Key XML quirk: the root element declares prefixed namespaces only
       (`xmlns:message`, `xmlns:ss`, …) with no default xmlns, so the
       `<Series>` and `<Obs>` elements live in the **empty namespace** — use
       `root.iter("Series")` / `series.iter("Obs")`, *not*
       `iter("{<ss-uri>}Series")`. `_parse_sdmx_json` kept as a one-line
       `pd.DataFrame(cached_list)` shim so `processors/__init__.py::
       load_insee_series()` doesn't need to change.
    2. **`budget_plrg` is PDF-only now.** The slug varies year-to-year
       (`plrg-2024`, `projet-de-loi-relatif-aux-resultats-de-la-gestion-...-plrg-2025`)
       but every recent PLRG dataset on data.economie.gouv.fr exposes a single
       PDF "notice explicative" — the tabular CSV/Excel export of
       mission/program/title spending was discontinued. No KPI processor
       consumes PLRG, so `fetch_plrg_execution()` now raises
       `NotImplementedError` with a clear message; the orchestrator's existing
       `NotImplementedError → skipped` branch surfaces it cleanly (same
       pattern as `compute_tax_expenditure`).
    3. **`kpi_monthly` ODS dataset is wide-format.**
       `situations-mensuelles-budgetaires-series-longues` no longer exposes a
       long `(date, label, value)` shape. It's now one row per
       **`ligne_d_information`** label (26 rows) with one column per month-end
       named **`DD_MM_YYYY`** (e.g. `31_01_2024`, `29_02_2024`, …, `31_03_2026`).
       Other id columns: `niveau_hierarchique`, `niveau_hierarchique_de_la_ligne`,
       `categorie`, `sous_categorie`. Replaced the `DATE_FIELDS` / `LABEL_FIELDS`
       / `VALUE_FIELDS` resolver with: detect date columns via
       `re.compile(r"^\d{2}_\d{2}_\d{4}$")`, melt them, and parse `DD_MM_YYYY`
       → `YYYY-MM`. Updated `LABEL_FIELD = "ligne_d_information"` and the
       classifier substrings to match the dataset's actual line labels —
       `REVENUE_TOTAL_KEYS = ["total recettes nettes du budget général"]` and
       `SPENDING_TOTAL_KEYS = ["total dépenses nettes du budget général"]`
       (was previously a list of variant spellings; only the exact label
       appears in the data). Dropped `"tva"` from the TVA category keys because
       the dataset uses the spelled-out form `"Taxe sur la valeur ajoutée"`
       and `"tva"` would match nothing while inviting accidental false
       positives if a future row mentions e.g. `"sous-TVA"`. Run verified end
       to end: revenue / spending / balance series populate, YoY %s computed.
    4. **`meta.json` now carries `latest_year` / `latest_month`.** New
       `_extract_latest_period(output_path)` helper in `run_pipeline.py`
       best-effort reads `data/output/<step_name>.json`, peeks at
       `france[-1]["year"]` (and the payload-root `last_month` for the
       monthly KPI), and merges those keys into the per-step status dict
       inside `_run_step`. Wrapped in `try/except Exception: return {}` so
       fetcher steps (no output JSON) and any malformed file leave the
       existing `status` untouched — fail-soft contract preserved.
  **Known data gap (out of 7d scope):** The base-2014 APU series in
  `CNA-2014-DEP-APU` (used for `wage_bill_apu`, `social_benefits`,
  `total_apu_expenditure`, `public_investment`, and all `cofog_gf*`) end at
  **2020**, so `kpi_overhead_rate` / `kpi_friction_ratio` /
  `kpi_productive_spend` / `kpi_pension_investment` stop at 2020 (visible in
  `meta.json.sources.*.latest_year`). `gdp_nominal` is already on
  `CNA-2020-PIB` per the Session 7a fix; the matching `CNA-2020-DEP-APU`
  rebase for the COFOG / aggregate series is a separate follow-up.

---

- **Session 8 — killed the 2020 ceiling. `CNA-2020-DEP-APU` does not exist;
  used CNT-2020-CSI + OECD stitch instead.** Per-user goal: no KPI may stop at
  2020. The Session 7d follow-up assumed a `CNA-2020-DEP-APU` family — **it is
  not in the INSEE mapping.** The only base-2020 APU families are
  `CNA-2020-PIB` (GDP, already used) and `CNA-2020-CSI` (5 rows of *ratios*,
  useless). Two-part fix:
    1. **APU aggregates → `CNT-2020-CSI` (quarterly, base 2020).** This family
       carries D1, OTE, B9NF, D41, D62, P5K2 for `SECT-INST=S13` with
       `NATURE=VALEUR_ABSOLUE`, `UNITE=EUROS`, and — critically — data from
       **1949-Q1 (OTE: 1980) through 2025-Q4**, so it fully *replaces* the
       frozen `CNA-2014-DEP-APU`/`CNA-2014-CSI` aggregates with no stitch
       needed. Repointed `wage_bill_apu`, `total_apu_expenditure`,
       `public_investment`, `social_benefits`, `fiscal_balance`,
       `debt_interest` in `SERIES_SEARCH_RULES`. Disambiguators:
       `COMPTE=E` (emplois/uses) for the flows, `COMPTE=SO` for the B9NF
       balance line. No `FONCTION` dimension here (it's sector accounts, not
       DEP-APU). **`wage_bill_central` (S13111) deleted** — CNT-2020-CSI has
       no central-state breakdown and no KPI consumed it.
    2. **Quarterly→annual in `annual_values()`.** It now detects period format:
       `YYYY` passes through; `YYYY-QN` is summed across the 4 quarters with
       **incomplete years dropped** (so a partial 2026 won't appear until
       Q4 lands); monthly `YYYY-MM` raises (CPI is loaded but no processor
       aggregates it, so this never fires in practice).
    3. **COFOG has no base-2020 home → stitch INSEE+OECD in `cofog.py`.** No
       INSEE family carries the FON01..FON10 functional breakdown past 2020
       (CNT-2020 families have no FONCTION dim). So `cofog_gf01..gf10` stay on
       `CNA-2014-DEP-APU` (frozen at 2020) and `processors/cofog.py` now
       *stitches* OECD GIP 2025 COFOG for France (already cached, 2007–2023,
       `MEASURE=GE`, `UNIT_MEASURE=PT_B1GQ` = % of GDP) for years after the
       last INSEE year. OECD %-of-GDP is converted to EUR via `gdp_nominal`
       so every downstream ratio stays in EUR/EUR and methodology-consistent.
       New API: `bucket_cofog(series, gdp_by_year)` (was `bucket_cofog(series)`)
       returns a DataFrame with a `total` column and a per-row `source`
       tag (`"INSEE"|"OECD"`); `function_eur_stitched(gf, series, gdp)` returns
       a single function's stitched EUR series (used by pension/investment for
       GF10). `base_break_note()` was **removed** — the per-datapoint `source`
       tag in each KPI JSON now self-documents the seam. **Seam quality:** at
       the 2020 overlap INSEE vs OECD agree within ±0.44pp of GDP per bucket
       (productive bucket: INSEE 14.28% vs OECD 14.72%). The visible jump at
       2020→2021 in productive_spend (14.28→15.49) is mostly the real
       post-COVID GF04 (economic-affairs) surge, ~0.44pp of it is the seam.
  **Result (verified via `--mode annual --no-upload`):** every KPI advances —
  `kpi_overhead_rate` → 2025, `kpi_sustainability` → 2024 (GDP-limited),
  `kpi_friction_ratio` / `kpi_productive_spend` / `kpi_pension_investment` →
  2023 (OECD COFOG limit). The new upstream ceiling is OECD's 2023, not 2020.
  **Each KPI now carries a `"source"` field per France datapoint.** Peer
  benchmarking remains deferred per the user (Phase 1.5); OECD COFOG is used
  here only as France's own post-2020 COFOG source, not for peer overlays.

---

- **Session 9 — PLF "dépenses fiscales" fetcher abandoned (no costed tabular
  data). `kpi_tax_expenditure` stays `skipped`.** Per-user decision after a
  full catalog probe: option 1 (skip cleanly), with options 2 & 3 documented
  below as future paths. **What exists** on data.gouv.fr / data.economie.gouv.fr:
    - `plf-2024-vm-tome-2_depenses-fiscales` — 468 rows, the most recent full
      list, but **uncosted**: only `(impôt, sous-catégorie, type, code numérique,
      description, finalité)`. No montant, no year columns. (data.gouv.fr id
      `655d451f3950fa796da6435b`; mirror ODS dataset same name.)
    - `top-8-depenses-fiscales-ir2021dlf-bces` — **8 rows only**, but costed:
      `cout_2021/2022/2023_en_millions_d_euros`, `nombre_beneficiaires_2021`.
      A one-off top-IR snapshot, not the full list.
    - `plf2023_voies_et_moyens_t2_liste_des_depenses_fiscales` and the
      `plf-201x-recettes-fiscales-nettes` sets — **0 records** (deprecated).
  KPI 5.8 needs count + total cost + ratio-to-revenue + YoY; 3 of 4 need cost,
  which is **PDF-only** (PLF *Voies et Moyens, Tome II*). So no usable fetcher.
  `compute_tax_expenditure()` keeps raising `NotImplementedError` (message
  updated to state the real reason), surfaced by the orchestrator as `skipped`
  — same pattern as `budget_plrg`. No fetcher file was created (a stub that
  only raises would be dead code; the existing processor skip is enough).
  **Fallback option 2 — parse the Tome II PDF (if this KPI becomes a priority):**
  The full costed table (one row per dépense fiscale, with chiffrage for years
  N-2 executed / N-1 estimated / N forecast) is published annually as a PDF
  on the Bercy/budget site (~September–October, alongside the PLF). Process:
  (a) resolve the latest "Voies et Moyens Tome II" PDF URL — slug varies
  year-to-year, search the data.gouv.fr/budget catalog; (b) extract tables
  with `pdfplumber` or `camelot` (pin a version per the ≥1-week rule); (c) the
  layout shifts between editions, so detect the chiffrage columns by header
  text ("Chiffrage pour 20NN") rather than position; (d) cache raw extracted
  rows to `data/raw/plf_depenses_fiscales_*.json`. This is a brittle, sizeable
  fetcher — give it its own session and budget for yearly maintenance.
  **Fallback option 3 — headline aggregate only (cheaper, lower fidelity):**
  France publishes a single national total dépenses-fiscales figure (~€80–90Bn/yr)
  in the budget documents. Track just `total_cost_eur_bn` and
  `ratio_to_revenue_pct` (revenue denominator already available from
  CNT-2020-CSI). Drop the per-expenditure breakdown and count. Caveat: the
  total is still PDF/text-sourced, so this needs either a small PDF scrape of
  the summary line or a documented manual-update step — which bumps against the
  project's "no hardcoded data" constraint, so treat it as a stopgap only.

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
