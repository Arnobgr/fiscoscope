# Runtime discoveries — fisc-o-scope

Session-by-session build log, moved out of `CLAUDE.md` (2026-05-22) so the
session-start file stays short. These notes persist across sessions; append a
new entry here (not in `CLAUDE.md`) when ending a session. Durable methodology
lives in these entries; the blocked-work reference is in `known-gaps.md`.

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
  and `NotImplementedError` lands as `skipped`. `run_pipeline.py` calls `load_dotenv()` from the repo-root `.env` *before* importing `config`. (The `--no-upload` flag and the R2 publisher were removed in Session E — output is now served by `api.py`, not uploaded.)

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

- **Session A (2026-05-20) — peer benchmarking wired for overhead, friction,
  productive spend (plan `docs/superpowers/plans/2026-05-20-backend-kpi-expansion.md`).**
  Three KPIs now carry a populated `peers` block; no new fetches (OECD COFOG +
  fiscal raw already cached). Shared helpers added to `processors/__init__.py`:
  `OECD_PEERS = [DEU,GBR,ITA,ESP,NLD,SWE]` (FRA excluded), `OECD_AVG_KEY`,
  `load_oecd_long(source)` (latest `data/raw/{source}_*.json` → long DF with
  `country/year/value` + lower-cased `transaction/expenditure/measure/unit_measure`),
  and `peer_series(df)` → `{country: [{year,value}], OECD_AVG: [...]}` where
  **OECD_AVG is the unweighted per-year mean across the 6 peers present**.
    - `kpi_overhead`: peers = D1 / total-expenditure (both % of GDP), level-comparable
      to France's D1/OTE.
    - `kpi_productive_spend`: peers = productive bucket (GF04+GF05+GF06) / total COFOG.
    - `kpi_friction_ratio`: peers = admin bucket (GF01+GF02+GF03) / total COFOG.
      **Trend-comparable only, not level-comparable** — France's denominator is
      revenue (expenditure+balance) but the peer denominator is total expenditure.
    The COFOG-bucket construction is a single helper `_cofog_bucket_peers(codes)`
    in `kpi_allocation.py`, imported by `kpi_friction.py`.
  - **Peer floor is 2007** (OECD GIP limit) vs. France's 1995/1998 — upstream, not a bug.
  - **Pension/investment peers stay deferred** — OECD fiscal raw has no P51
    (gross fixed capital formation) and PRD §5.5 names no peer source.
  - **PLAN DEVIATION (user-approved) — the A2 `_T` total-expenditure code does not
    exist under `MEASURE=GE` in the cached `oecd_fiscal`.** The plan assumed
    `tot = ge[ge['transaction']=='_T']`; in the cache, `MEASURE=GE` carries only
    component transactions (`D1,D3,D4,D6M,KE,P2,_O_CE`) and `_T` appears only under
    `MEASURE=OUT`/`PRCO` (neither is total expenditure — they give nonsensical
    ratios of 109%/44%). Total general-government expenditure is the **sum of the
    GE component transactions** (all % of GDP): ΣGE = 55.35% for FRA 2019, matching
    the real ~55%-of-GDP figure, and D1/ΣGE = 22.33% matches France's own KPI
    value 22.32%. So `kpi_overhead` uses
    `ge.groupby(["country","year"])["value"].sum()` as the denominator, not `_T`.
    The COFOG-bucket peers (A3) were unaffected — they already sum GF01..GF10.
  - **Verified** via each module's `__main__` + `--mode annual --no-upload`: all
    three KPIs `status: ok`, each `peers` has the 6 codes + `OECD_AVG` (FRA absent),
    France series unchanged (overhead 1995–2025, friction/productive 1995–2023).

---

- **Session B (2026-05-20) — sustainability gains France Maastricht debt + OECD
  deficit/debt peers** (same plan as Session A).
  - **France debt series — `DETTE-TRIM-APU-2020` (quarterly, base 2020).** New
    `public_debt_ratio` resolver rule. **PLAN DEVIATION (data-verified):** the
    plan's `DETTE_MAASTRICHT_INTRUMENTS=TOT` finds nothing — for the S13 Maastricht
    debt %-of-GDP series the instrument code is **`F`** (total financial
    liabilities); `TOT` never co-occurs with `NATURE=PROPORTION`/`UNITE=POURCENT`.
    Resolves uniquely to idbank `010777608`. Debt is a **STOCK** → annual figure is
    the year-end Q4 quarter (2024-Q4 = 112.6%), via new `year_end_value()` in
    `processors/__init__.py` (mirrors `annual_values` but takes Q4, not the sum;
    annual 'YYYY' input passes through).
  - **Peer deficit + debt — one GIP dataflow, NOT the plan's two.** **PLAN
    DEVIATION (data-verified):** the plan's `DSD_GOV_FIN_INSTR` debt dataflow has
    **no % of GDP** unit (only `PT_FD4_S13` = % of total debt, and `USD_PPP`), and
    the `SDD.NAD,DSD_NASEC10_IDC@DF_TABLE12_IDC` deficit set is a 135 MB unfiltered
    pull. Both peer series come instead from **`OECD.GOV.GIP,DSD_GOV@DF_GOV_PF_2025`**
    ("Public finance main indicators"), dims
    `FREQ.REF_AREA.MEASURE.UNIT_MEASURE.SECTOR.EDITION.CATEGORY` (7 → 6 dots).
    Keys: deficit `A.{countries}.GNLB.PT_B1GQ.S13..` (GNLB = net lending/borrowing),
    debt `A.{countries}.GGDM.PT_B1GQ.S13..` (**GGDM = Maastricht** gross debt —
    matches France's INSEE Maastricht line, e.g. FRA 2023 GGDM 109.9% vs INSEE
    109.5%; the alternative `GGD` SNA gross debt runs ~12pp higher and is NOT
    level-comparable). Both verified live: 7 countries, 2007–2024, 126 rows.
    `fetch_oecd_deficit()` / `fetch_oecd_debt()` cache `oecd_deficit_*` /
    `oecd_debt_*`; each key pins a single MEASURE+UNIT so `load_oecd_long` +
    `peer_series` need no extra filtering. Registered both in `run_annual()`.
  - **Payload shape grew:** `kpi_sustainability.json` now carries
    `"debt": {"france": [...]}` and a two-part `"peers": {"deficit": {...},
    "debt": {...}}` (each = 6 peers + `OECD_AVG`). France deficit series unchanged.
  - **Verified** via `--mode annual --no-upload`: no errors; `oecd_deficit`/
    `oecd_debt` `ok`, `kpi_sustainability` `ok` → 2024; France debt 31 pts
    (1995–2025), 2024 = 112.6%; peer blocks FRA-absent; DEU 2023 deficit −2.48%.

---

- **Session C (2026-05-20) — tax-expenditure source spike: DECISION = BUILD (GTED
  via Zenodo).** A spike, not a build — no fetcher/KPI written this session. Session 9
  deferred `kpi_tax_expenditure` because no costed, multi-year, full-list tabular source
  was known; this session re-checked every candidate and **found one**, so the decision
  flips to *build* (scheduled as Task C2 in the plan, gated on user go-ahead). Every
  source checked, with format / multi-year-costed availability / licence:
  - **data.gouv.fr catalog sweep** (the plan's hyper-specific multi-term queries all
    returned **0 results** — data.gouv's search needs broad terms; `q="depenses fiscales"`
    returns the real 6-dataset catalog). Confirms Session 9 at field level:
    - `plf-2024-vm-tome-2-depenses-fiscales` — CSV/JSON, licence **notspecified**, 468
      rows, columns = impôt / catégorie / type / **code numérique** / description /
      finalité. **UNCOSTED** (no montant, no year cols). Full list, no cost.
    - `plf2023-voies-et-moyens-t2-liste-des-depenses-fiscales` — CSV/XLSX/JSON, lov2;
      the ODS export now returns only record-metadata columns → **0 real records**
      (deprecated/empty).
    - `top-8-depenses-fiscales-ir2021dlf-bces` — CSV/JSON, licence **lov2** (Licence
      Ouverte 2.0, redistribution OK). **COSTED** (`Coût 2021/2022/2023 en M€`, nombre
      bénéficiaires 2021) but only **8 rows, impôt-sur-le-revenu subset**, a one-off
      (last modified 2023-03-10). Partial, not the full list.
    - `liste-des-8-depenses-fiscales-les-plus-couteuses-...-ir` — same shape, 8-row IR
      snapshot (2018), lov2.
    - Two Cour-des-comptes-style "efficience / gestion des dépenses fiscales" reports
      (2017/2019, odc-odbl) — thematic/narrative, not a full costed table.
    - `plf-201x-recettes-fiscales-nettes` sets — tax **revenue**, not tax expenditures.
    → data.gouv.fr verdict unchanged from Session 9: no full-list, costed, multi-year
    tabular source. Best costed = the 8-row IR snapshot.
  - **GTED — Global Tax Expenditures Database (the lead, CC-BY).** The website
    (`gted.net` → `gted.taxexpenditures.org`) sits behind a **Cloudflare JS challenge**
    ("Just a moment…", `server: cloudflare`) — `requests` + `DEFAULT_HEADERS` get `403`
    on every path, so the site itself is NOT scrapable without a headless browser. **But
    the full database is mirrored on Zenodo**, reachable via the Zenodo REST API with
    `DEFAULT_HEADERS` (no Cloudflare): concept record `12585656`; latest **v1.3.2 =
    record `17312217`** (published 2025-10-10), a single **18.57 MB XLSX**
    (`GTED_FullDatabase_20251010.xlsx`), download verified HTTP 200. Licence
    **CC-BY-4.0** (Zenodo metadata + GTED site agree) → redistribution permitted with
    attribution (cite Redonda, von Haldenwang & Aliu; DIE/CEP). Sheets: `Information,
    TEProvisions, RevenueForgone, NumberofBeneficiaries, Background_data, Source Tables`.
    The **`RevenueForgone`** sheet is the costed long table (150,705 rows total): columns
    `Country, ProvisionID, Year, RF (LCU), Projection/Estimate, Note, RF (USD),
    RF % of GDP, RF % of Tax`. **France (`Country=="FRA"`): 10,896 rows, 869 distinct
    provisions, years 1999–2025, every row costed** (`RF (LCU)` = EUR; ~400 provisions
    reported per year). Annual ΣRF (LCU) matches France's published dépenses-fiscales
    headline (2024 ≈ €79.8 Bn, 2018 ≈ €96.5 Bn — the real ~€80–90 Bn/yr). This is a
    **clean, costed, multi-year, redistribution-OK tabular source** → satisfies KPI 5.8's
    needs (count + total cost + ratio + YoY).
  - **Eurostat** `gov_10a_taxag` — tax **revenue** aggregates (ESA 2010 detailed
    receipts), **no** France tax-expenditure / niches-fiscales dataset. Not applicable.
  - **performance.gouv.fr / forge.dgfip, Cour des comptes / Assemblée nationale** — the
    official full costed list (Voies et Moyens *Tome II*) remains **PDF-only** in these
    channels; no tabular open-data mirror beyond what data.gouv.fr already carries. GTED
    supersedes the need to parse these.
  **Build caveats to honour in Task C2 (do not lose these):** (1) fetch from **Zenodo,
  not gted.net** — resolve the latest version from the concept record `12585656`
  (`/api/records/12585656` → follow to the newest version) so the fetcher tracks new
  releases without a hardcoded record id; (2) **CC-BY-4.0 requires attribution** — emit
  the GTED citation/DOI in the KPI JSON `source` and surface it in the frontend; (3) GTED
  is a **third-party academic compilation** of France's own PLF data, not a primary
  statistical-agency feed like the rest of the pipeline — its provision count (~400/yr)
  and Revenue-Forgone definition differ slightly from France's PLF (~468 lines), so state
  the methodology/source clearly; (4) data is an **annual XLSX snapshot** (one big file),
  read it with the pinned `openpyxl==3.1.5`. **Session 9's option-2 (PDF parse of Tome II)
  and option-3 (headline aggregate) are now FALLBACKS ONLY** — preferred path is GTED.
  - **BUILT (Task C2, same day, user-approved) — `kpi_tax_expenditure` is now `ok`, no
    longer `skipped`.** New `fetchers/tax_expenditure.py`: resolves the newest GTED release
    via the Zenodo **concept** record (conceptrecid **`5940165`**, concept DOI
    `10.5281/zenodo.5940165`) at `…/records/5940165/versions/latest` — **no version id
    hardcoded** (the earlier `12585656` is the v1.3.0 version record, *not* the concept).
    Downloads the XLSX from Zenodo (gted.net is Cloudflare-blocked; Zenodo is not), reads
    sheet `RevenueForgone`, filters `Country=="FRA"`, caches the 6 KPI columns
    (`ProvisionID, Year, RF (LCU), Projection/Estimate, RF % of GDP, RF % of Tax`) to
    `data/raw/tax_expenditure_*.json`. `compute_tax_expenditure()` (in `kpi_outcomes.py`,
    rewritten from the `NotImplementedError` stub) emits France `[{year,
    total_cost_eur_bn, count, projection, ratio_to_revenue_pct, yoy_change_pct}]`,
    `peers: {}`, 1999–2025 (27 pts). Decisions/gotchas:
      - **UNIT MISMATCH (the one real trap):** GTED `RF (LCU)` is in **absolute EUR**
        (e.g. 5.295e10), but INSEE CNT-2020-CSI revenue is in **millions of EUR**
        (2023 revenue = 1,456,129 = €1,456 Bn). The ratio scales revenue ×1e6:
        `total_eur / (revenue × 1e6) × 100`. Forgetting this gives ~7,000,000%.
      - `count` = provisions **reported** that year (~405–409; **includes ~300/yr costed
        at zero** — a zero-cost niche still exists). `FRA0000` is a real €1 Bn provision,
        not an aggregate/total row — nothing to exclude. No duplicate provision-year rows.
      - The **two most recent years (2024, 2025) are GTED `Projection`** (forecasts) →
        `"projection": true`; all earlier years are `Estimate` → `false`. The frontend
        must not present projected years as actuals.
      - Revenue denominator = `total_apu_expenditure (OTE) + fiscal_balance (B9NF)` (same
        as friction/debt-service), emitted only for years with INSEE revenue.
      - **No new dependency** (openpyxl/pandas/requests already pinned). Registered as the
        `tax_expenditure` fetch step in `run_annual()` (before the KPI block).
    **Verified** via `--mode annual --no-upload`: `tax_expenditure` + `kpi_tax_expenditure`
    both `ok`; series 1999→2025; 2018 peak €96.5 Bn / 7.58% of revenue, 2023 €81.7 Bn /
    5.61%, 2025 (projection) €75.6 Bn / 4.84%. All other KPIs unchanged; `budget_plrg`
    remains the only by-design `skipped` step.

---

- **Session D (2026-05-21) — orphaned-source KPI evaluation (plan
  `docs/superpowers/plans/2026-05-20-backend-kpi-expansion.md`).** Four orphaned
  inputs evaluated; two built (#1, #2), two deferred (#3, #4).
  - **D1 decision = BUILD #1 + #2, DEFER #3 + #4.** Sanity-checked the Urssaf
    annualization and ratio scale against the cached raw before building.
    - **Urssaf raw** (`data/raw/urssaf_2026-05-16.json`, 116 rows): every year
      **1997–2025 has all 4 quarters** (none dropped by the "complete-year"
      filter — the unsorted file made early rows *look* sparse, but `groupby`
      confirms 29 complete years). `ms_t_60j_cvs` is the seasonally-adjusted
      quarterly private wage bill in **absolute EUR** (1998 ≈ €78.5 Bn/quarter).
    - **UNIT MISMATCH (the trap the plan's D1 step exists to catch).** INSEE
      `wage_bill_apu` (D1_S13, CNT-2020-CSI) is in **millions of EUR**
      (2023 = 346,293 = €346.3 Bn), but Urssaf `ms_t_60j_cvs` is **absolute EUR**
      (2023 ΣQ = 703,264,232,755 = €703.3 Bn). The plan's literal D2 ratio
      `public / private × 100` is therefore **off by exactly 1e6** (yields
      ~5e-5%). **Fix (data-verified, documented CNT-2020-CSI convention from
      Session C): scale public ×1e6** → `public × 1e6 / private × 100`. Corrected
      ratio is **49–57%, trending down** (1997 ≈ 57% → 2023–25 ≈ 49–50%; public
      payroll grows slower than the private wage bill, with a real 2020 COVID blip
      to 54.8% as the private bill dipped) — squarely in the plan's expected
      40–55% band, so the build proceeds.
    - **#3 France Travail — DEFERRED (no efficiency ratio possible yet).** The
      cached `france_travail_*` table gives an indemnisés *count* (`Total (1+2+3)`),
      a level not a ratio. The natural efficiency metric — **benefit € per
      recipient** — needs a benefit-**spend** series the France-Travail file does
      not carry. To build it later, add one of: the COFOG **GF10.5 unemployment
      sub-function** (EUR spend, sliceable from the OECD GIP COFOG raw or an INSEE
      functional series) as numerator over the count, or a France-Travail
      *expenditure* (allocations versées, € montant) file. Until then it stays
      orphaned.
    - **#4 CPI deflation — DEFERRED (utility, not a KPI).** `cpi` is a
      transformation (constant-euro reframing), not a standalone metric. Build it
      only when a KPI wants constant-euro framing; `cpi` remains loaded but
      unconsumed.
  - **D2 BUILT — `kpi_wage_ratio` (`processors/kpi_wage_ratio.py`, new).** Formula:
    `wage_bill_apu (D1_S13, millions) × 1e6 / private wage bill (Σ4 Urssaf
    ms_t_60j_cvs quarters, absolute EUR) × 100`. The `× 1e6` is the unit
    correction above — **a deliberate deviation from the plan's literal
    `public / private × 100`**, which was off by 1e6. Private side hand-rolls the
    4-quarter sum (Urssaf isn't an INSEE BDM series, so `annual_values` can't read
    it; the standard helpers — `annual_values`, `build_latest`, `latest_raw`,
    `load_insee_series`, `now_iso`, `write_output` — are reused everywhere else).
    France-only (no peer source). Registered in **`run_monthly()`** after the
    `urssaf` fetch. Verified: 29 pts 1997–2025, 2025 = 49.77%.
  - **D3 BUILT — `kpi_debt_service` (`processors/kpi_debt_service.py`, new).**
    Formula: `debt_interest (D41_S13) / [total_apu_expenditure (OTE) +
    fiscal_balance (B9NF)] × 100` — the same revenue denominator as
    friction/tax-expenditure. All three legs are CNT-2020-CSI (millions), so units
    cancel — **no scaling needed** (unlike D2). France-only. Registered in
    **`run_annual()`** after `kpi_sustainability`. Verified: 31 pts 1995–2025,
    range 2.43–6.94% (1995 = 6.79% → 2020-era ZIRP trough → 2025 = 4.15%).
  - **Orphan status now:** `debt_interest` (D41) and **Urssaf are no longer
    orphaned** (consumed by D3 and D2 respectively). **`cpi`, `social_benefits`
    (D62), and France Travail remain unused** (corrected 2026-05-21 — an earlier
    version of this line omitted D62). France Travail would become a KPI only with
    a benefit-**spend** series (COFOG GF10.5 unemployment sub-function in EUR, or a
    France-Travail expenditure/montant file) to pair with its indemnisés count as
    € per recipient. See the consolidated "Known gaps & blocked attempts" section
    below for all orphaned inputs, peer-coverage feasibility, and upstream blocks.
  - **Verified** via `python run_pipeline.py --mode full --no-upload`:
    `kpi_wage_ratio` and `kpi_debt_service` both `status: ok` in `meta.json`
    (latest_year 2025). `budget_plrg` remains the only by-design `skipped`.
  - **WATCH ITEM TRIGGERED — `open.urssaf.fr` TLS still expired (2026-05-21).** The
    `urssaf` fetch step reported `status: error`
    (`CERTIFICATE_VERIFY_FAILED ... certificate has expired`), failing soft as
    designed — **`verify=False` was NOT added** (per the plan's standing
    instruction). `kpi_wage_ratio` still computed `ok` from the cached
    `data/raw/urssaf_2026-05-16.json`, so the wage-ratio output is **current as of
    that cache, not a fresh fetch** — it will go stale until the cert is renewed.

---

- **Session E (2026-05-21) — R2 retired; output now served by a FastAPI app.**
  Decision (user): drop the Cloudflare R2 upload entirely and serve the ~80 KB
  `data/output/*.json` directly from a small always-on FastAPI app on the VPS.
  This reverses the PRD's original "no backend API / static JSON from R2" design.
    - **New `backend/api.py`** (FastAPI + uvicorn): read-only endpoints
      `/healthz`, `/api/meta`, `/api/kpis`, `/api/kpi/{name}`, reading
      `OUTPUT_DATA_DIR`. CORS allowlist (`config.ALLOWED_ORIGINS`) + global
      `slowapi` rate limit (`config.RATE_LIMIT`, default `60/minute`). KPI names
      are regex-guarded (`^[a-z0-9_]+$`) against path traversal. `OUTPUT_DIR` is
      module-level so tests monkeypatch it. Tests in `backend/tests/test_api.py`
      (pytest + FastAPI TestClient).
    - **Removed:** `publishers/r2_upload.py` (+ the now-empty `publishers/`),
      its `run_pipeline.py` import / `--no-upload` flag / upload block, the
      `R2_*` vars in `config.py`, and `boto3` from `requirements.txt`. Added
      `fastapi`, `uvicorn[standard]`, `slowapi` (runtime) and a
      `requirements-dev.txt` with `pytest`, `httpx`.
    - **Deploy model (not in this repo):** Cloudflare Pages frontend →
      `<ip>.sslip.io` (Let's Encrypt) → uvicorn, with `ufw` (only 80/443+SSH)
      and rate limiting. "Only the frontend can call the API" is *not* a goal —
      impossible for a public SPA + public API, and unneeded for public data;
      CORS only enables the frontend, rate-limit + firewall bound abuse.
    - The first live deployment + the frontend (Phase 2) remain to be built.
