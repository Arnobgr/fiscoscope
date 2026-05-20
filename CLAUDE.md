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

## Runtime discoveries

> Fill this in as sessions progress. These notes persist across sessions.
> Per-session task briefs for the completed Sessions 1–7 were removed once
> their work shipped; the durable outcomes are recorded below. Original briefs
> remain in git history if ever needed.

- **Sessions 2–3 — datacenter IP block (OBSOLETE).** INSEE/OECD/data.gouv.fr/
  data.economie.gouv.fr/open.urssaf.fr originally `403`'d from this VPS. The block
  was lifted before Session 7 (see Session 7 prep); ignore unless 403s return.

- **Session 4 — processor helpers (still current).** `processors/__init__.py` holds the
  shared helpers: `load_insee_series()` (rebuilds logical_name → DataFrame from the latest
  `data/raw/insee_bdm_*.json` + `insee_idbanks.json`), plus `annual_values`, `build_latest`,
  `write_output`, `now_iso`, `to_year`, `latest_raw`. `cofog.py` holds the COFOG bucketing
  (its API changed in Session 8 — see there). Processors read the raw cache only, never
  re-fetch, and are deterministic. `requirements.txt` lists `pandas` (runtime dep).

- **Session 5 — Friction Ratio denominator decision (still the live methodology).** PRD §5.3
  names "total taxes collected" but no tax-revenue series is resolved, so total revenue is
  derived as `total_apu_expenditure + fiscal_balance (B9)`; friction spend is the
  administrative COFOG bucket (GF01+GF02+GF03), debt interest left inside GF01 (not added
  again). France-only. (Other Session 5 notes — tax-expenditure, kpi_monthly, outcomes,
  sustainability — are superseded by Sessions 7d/8/9/10.)

- **Session 6 — orchestrator is fail-soft (still current).** Every fetcher/processor runs
  inside `_run_step`, which records `status: ok | skipped | error` (with the exception
  message) into `meta.json.sources` and never re-raises — one outage can't abort the run,
  and `NotImplementedError` lands as `skipped`. `run_pipeline.py` has a `--no-upload` flag
  and calls `load_dotenv()` from the repo-root `.env` *before* importing `config`.
  `publishers/r2_upload.py` validates all four R2 env vars upfront and raises one
  `RuntimeError` listing any missing names.

---

- **Session 7 prep (2026-05-15) — IP block lifted; durable prep work.** The datacenter
  `403`s are gone from every host. Four upstream breakages found here were all fixed in
  Sessions 7a–7d (INSEE ZIP/positional schema → 7a; OECD 8-dim DSDs → 7b; France Travail
  XLSX → 7c; INSEE BDM XML + budget/monthly → 7d). Still-live prep: a generic Firefox UA
  in `fetchers/__init__.py` (`DEFAULT_HEADERS`) threaded through every `requests.get`;
  `requirements.txt` pinned to exact versions (`requests==2.33.1`, `pandas==2.3.3`,
  `boto3==1.43.6`, `python-dotenv==1.2.2`). Plan for 7a–7d:
  `docs/superpowers/plans/2026-05-15-upstream-data-source-fixes.md`.

---

- **Session 7a — INSEE resolver ported to the new ZIP / positional schema (still current).**
  The mapping CSV has only 4 columns (`famille`, `idbank`, `list_mod`, `list_var`); every
  dimension is decoded by zipping `list_var.split('.')` with `list_mod.split('.')` per row.
  `download_mapping()` scrapes `https://www.insee.fr/fr/information/2862759` for the latest
  `*_correspondance_idbank_dimension.zip` link and extracts the CSV. Dimension names
  changed from the old flat CSV (`FREQ`→`PERIODICITE`, `SECT_INST`→`SECT-INST`,
  `COFOG`→`FONCTION`). Two resolver rules set here are **still live** (the rest — the APU
  aggregates D1/OTE/P5K2/D62/B9NF/D41 — were re-pointed to CNT-2020-CSI in Session 8):
    - `gdp_nominal`: `famille=CNA-2020-PIB`, `PRIX_REF=VAL`, `NATURE=VALEUR_ABSOLUE`,
      `UNITE=EUROS_COURANTS` (CNA-2014-PIB is `SERIE_ARRETEE=TRUE`).
    - `cpi`: `famille=IPC-2025`, no `OPERATION` dim — match `INDICATEUR=IPC`,
      `COICOP2018=00`, `PRIX_CONSO=00`, `NATURE=INDICE`, `MENAGES_IPC=ENSEMBLE`,
      `ZONE_GEO=FE`, `CORRECTION=BRUT`, `PERIODICITE=M`.
  COFOG `cofog_gf01..gf10` stay on `CNA-2014-DEP-APU` (`FONCTION=FON01..FON10`,
  `OPERATION=OTE`, `SECT-INST=S13`) — frozen at 2020, stitched with OECD in Session 8.

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
  (The 7d "base-2014 stops at 2020" data gap was resolved in Session 8.)

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

- **Session 10 — Outcomes KPI shipped HEALTH-ONLY as dual time series.**
  Per-user decisions: (a) ship health only — **PISA is not in OECD's SDMX API**
  (the dataflow catalog has enrolment, per-student expenditure `DSD_EAG_UOE_FIN`,
  instruction time, and TALIS, but no student-performance scores; PISA ships via
  separate downloads/the PISA explorer), so the education side is a documented
  gap; (b) **dual time series**, not "indexed to OECD average" — peer
  benchmarking is deferred, so the KPI emits France health spend and life
  expectancy as two parallel series and lets the reader judge whether outcomes
  track spend. Implementation:
    - **New fetcher `fetch_oecd_life_expectancy()`** in `fetchers/oecd.py`.
      Dataset `OECD.ELS.HD,DSD_HEALTH_STAT@DF_LE`. The DSD has **13 dimensions**
      in order `REF_AREA.FREQ.MEASURE.UNIT_MEASURE.AGE.SEX.SOCIO_ECON_STATUS.
      DEATH_CAUSE.CALC_METHODOLOGY.GESTATION_THRESHOLD.HEALTH_STATUS.DISEASE.
      CANCER_SITE`, so the France key is `FRA.A.LFEXP.Y.Y0._T.......` (12 dots,
      7 trailing wildcards). `MEASURE=LFEXP`, `AGE=Y0` (at birth), `SEX=_T`
      (total), `UNIT_MEASURE=Y` (years). Defaulted `start_year=INSEE_START_YEAR`
      (1995, not OECD's 2000) so it spans the same range as the health-spend
      series. Verified live: France 1995→2023, 29 annual points (78.1y→83.0y).
    - **`compute_outcomes()` rewritten** (`processors/kpi_outcomes.py`): health
      spend = GF07 COFOG `function_eur_stitched("GF07", …)` / nominal GDP × 100
      (so it reuses the Session 8 INSEE+OECD stitch and inherits `source` tags);
      life expectancy read from the cached `oecd_life_expectancy` raw filtered to
      `LFEXP/Y0/_T`. Output schema changed from the old `france/peers/latest`
      placeholder to `{health: {spend_pct_gdp[], life_expectancy_years[]},
      education: null, peers: {}, latest: {...}}`. Registered
      `oecd_life_expectancy` in `run_pipeline.run_annual()`.
  Verified end to end: both series 1995–2023 (29 pts). Note the intended signal
  is already visible — 2015→2020 spend +0.86pp of GDP while life expectancy was
  flat (82.4→82.3y). **Education gap reopen path:** if PISA becomes a priority,
  source it from the OECD PISA explorer bulk download or a data.gouv.fr mirror
  (not SDMX), interpolate the triennial surveys linearly per PRD §5.9, and add
  an `education` block mirroring `health`. `write_output` still logs "0 France
  data points" for this KPI because the payload has no `france` key — cosmetic,
  left as-is.

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
