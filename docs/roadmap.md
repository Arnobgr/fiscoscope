# Roadmap — Fiscoscope for citizens: transparency & accountability

Written 2026-10-26, last updated 2026-11-14. This is the forward plan;
`known-gaps.md` stays the reference for what is blocked and
`runtime-discoveries.md` for why existing KPIs are built the way they are.

**Status (2026-11-14).** Phase 0, Phase 1, 3.1 (State performance
scorecard + drill-down page), 2.1 (€ per inhabitant in constant euros on
7 KPIs, Session J) and 2.4 (automatic context sentence on 14 cards,
Session K; Part 6) are done — 2.4 is built and tested locally, not yet
deployed (Session K lists the deploy steps): 16 KPIs on the site. **The next item is
Phase 4** ("Ma commune", starting with 4.1, the OFGL fetcher). There is no
brief yet: write one in the format of Part 5 from S9 (Part 1.2) and the
appendix query.

**Start here (new session).**
1. Read this file top to bottom, then `known-gaps.md`. No other context is
   needed: Part 4 holds the repo conventions, environments and shipping steps,
   Part 5 the 3.1 brief (kept as the model brief and the reference for the
   performance datasets), Part 6 the decisions behind 2.4 (context
   sentences).
2. Take the next unchecked item from Part 3 (today: Phase 4, item 4.1).
3. Before writing code, re-run that source's queries (the appendix; Part 5.8
   for the performance datasets): dataset IDs and columns drift (Part 4.1).
4. Settle the open decisions with the owner before building (Part 5.5 shows
   the format used for 3.1, Part 6.4 the one used for 2.4).
5. When done, follow "After each item" at the end of Part 3.

Figures quoted in Parts 1–2 are as of 2026-10-26 unless dated otherwise; Part 5
was re-verified on 2026-11-08.

**Goal.** Give French citizens the clearest possible, independently computed view
of how public money is raised, spent and managed — surfacing what is published
but buried (in annexes, PDFs, sub-sector tables, other portals), and comparing
what the State *promised* with what it *delivered*.

**How every data source below was vetted.** Each one was queried live on
2026-10-26 and a sample was downloaded and decoded (exact queries in the
appendix). Status legend:

- ✅ **Verified** — API/file reachable, sample decoded, coverage and fields
  confirmed, usable as an automated pipeline input.
- ⚠️ **Usable with caveats** — works, but a stated limitation shapes how it may
  be used.
- ❌ **Rejected / deferred** — unreachable, stale, or not machine-readable.

---

## Guiding principles

1. **Credibility before reach.** One misleading label lets critics dismiss the
   whole site. Every number must survive a hostile fact-check; Phase 0 exists
   for that reason.
2. **Neutral facts, not verdicts.** Show who was in office, what was targeted,
   what happened — never editorialise about parties or people. Accountability
   comes from the juxtaposition, not from adjectives.
3. **Official primary sources first.** Third-party compilations (GTED, the DECP
   consolidation) are allowed only when labelled as such on screen.
4. **Automated, with one declared exception.** Everything is fetched by the
   pipeline. The only manual input allowed is a one-time backfill of archival
   files that cannot be scripted (see 3.2), committed with their source URLs.
5. **Ratios *and* euros per person.** Ratios for comparison; € per inhabitant
   (constant euros) so a citizen can relate to the number.

---

## Part 1 — Data-source verification results

### 1.1 Summary

| # | Source | Status | Unlocks |
|---|--------|--------|---------|
| S1 | Eurostat `gov_10a_exp` — COFOG level 2 × transaction | ✅ | True overhead KPI, pension isolation (GF1002), investment by function, peers, data to 2024 |
| S2 | Eurostat `gov_10a_main` — sub-sector accounts | ✅ | Deficit split State / local / social security, 1995–2025 |
| S3 | Eurostat `gov_10a_taxag` — tax burden | ✅ | Prélèvements obligatoires vs EU peers |
| S4 | Eurostat `gov_10dd_ggd` — debt structure | ⚠️ | Who holds French debt (non-residents, Banque de France) — France only from 2020 |
| S5 | OECD Revenue Statistics `DF_RSOECD` | ✅ | Tax-to-GDP 1965–2024 incl. UK and OECD average |
| S6 | OECD GaaG `DF_GOV_EMPPS_REP_2025` | ✅ | Public employment share vs peers, 2007–2023 |
| S7 | data.economie.gouv.fr — PAP/RAP performance indicators | ✅ | The State's own targets vs results, per programme |
| S8 | Eurostat EDP notification tables (PDF) | ⚠️ | Government's *planned* deficit/interest vs outturn |
| S9 | OFGL `data.ofgl.fr` — local-authority accounts | ✅ | "Ma commune / mon département / ma région" |
| S10 | DECP consolidated (data.gouv.fr) — public procurement | ⚠️ | Single-bid rate, no-competition procedures, supplier concentration — **not** amounts |
| S11 | OpenFisca-France | ✅ | "Where do *my* taxes go" archetype households |
| S12 | HATVP — lobbying register & declarations | ⚠️ | Lobbying activity targeting finance bills |
| S13 | Jaune "effort financier en faveur des associations" | ⚠️ | Per-recipient State subsidies to associations |
| S14 | AFA / SSMSI probity offences | ⚠️ | Context only: recorded corruption-type offences |
| S15 | PLF credits by destination (mission/programme/action) | ⚠️ | Voted credits — latest vintage on the portal is PLF 2025 |
| — | Rejected: Cour des comptes recommendations, DGAFP headcount, AFT, PLRG, ONDAM tabular | ❌ | See 1.3 |

### 1.2 Source details

#### S1 — Eurostat `gov_10a_exp` (government expenditure by function) ✅
- **Endpoint:** `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10a_exp`
  (JSON-stat 2.0, no key). Dataset updated 2026-10-21.
- **Coverage verified:** France 1995–2024, COFOG level 2 (e.g. `GF0103`,
  `GF0901`, `GF1002`), by transaction: `TE` total expenditure, `D1` compensation
  of employees, `P51G` investment. Peers DE/IT/ES/NL/SE + `EU27_2020` average.
  **No UK** (post-Brexit) — keep OECD for UK where needed.
- **Sample (France 2024, € bn):** total expenditure 1,671.8; compensation of
  employees 362.1; GF01 compensation 47.6; GF1002 old-age expenditure 392.0
  (23.4 % of all public spending).
- **Key finding for Phase 0:** of the 362 bn public wage bill, education is
  28.7 %, health 19.3 %, general public services only 13.1 % (public order 10.1 %,
  social protection 8.9 %, defence 5.9 %). The current "Coût administratif" KPI
  (= total D1 / total spending, 21.5 %) therefore counts teachers and nurses as
  overhead. *(Fixed in 0.1: renamed "Part de la masse salariale publique".)*
- **Unblocks** (`known-gaps.md`): pension isolation (GF1002 vs all of GF10);
  investment peers (P51G is present for all peers); COFOG past 2023 without the
  INSEE→OECD stitch; finer functional detail for all KPIs.

#### S2 — Eurostat `gov_10a_main` (main aggregates by sub-sector) ✅
- Same API. `sector` = `S13` (all), `S1311` (central government), `S1313`
  (local), `S1314` (social security); `na_item` = `B9` (balance), `TE`, `TR`,
  `D41PAY` (interest payable — verified: FR 2.2 % GDP vs DE 1.1 % in 2025,
  1995–2025, peers available → also gives `debt_service` the peers that
  `known-gaps.md` B lists as unconfirmed).
- **Coverage verified:** 1995–2025.
- **Sample (2025, € bn):** general government −151.6 = central government
  −130.3, local −15.6, social security −5.8. The deficit is overwhelmingly the
  State's — a fact rarely shown.

#### S3 — Eurostat `gov_10a_taxag` (tax burden) ✅
- `sector=S13_S212`, `unit=PC_GDP`, `na_item=D2_D5_D91_D61_M_D995`
  (taxes + net social contributions).
- **Sample 2024:** FR 45.3 %, DE 40.9 %, IT 42.3 %.
- Note: higher than OECD's figure (S5) because definitions differ (imputed
  contributions, EU taxes). Pick one per chart and say which.

#### S4 — Eurostat `gov_10dd_ggd` (structure of government debt) ⚠️
- Debt by holder (`sector2`: `S2` rest of world, `S121` central bank, …), by
  maturity, by instrument.
- **Sample 2025, % GDP:** total 115.6, held by non-residents 62.8, by the
  Banque de France 19.1. Germany: 63.5 / 32.6 / 12.4.
- **Caveat:** France's holder breakdown starts only in **2020** (DE from 1995).
  Fine for a "who owns the debt" snapshot, not for a long series.
- Does **not** give the inflation-indexed share (that is AFT-only, see 1.3).

#### S5 — OECD Revenue Statistics ✅
- `https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_REV_COMP_OECD@DF_RSOECD,/{AREAS}.TAX_REV.S13._T._T.PT_B1GQ.A`
  (7 dims: REF_AREA.MEASURE.SECTOR.STANDARD_REVENUE.CTRY_SPECIFIC_REVENUE.UNIT_MEASURE.FREQ).
- **Coverage verified:** 1965–2024, all 7 peers **including GBR** + `OECD_REP`
  average. Also splits by sub-sector and by tax type (`STANDARD_REVENUE`).
- **Sample 2024 tax-to-GDP:** FRA 43.5, DEU 38.0, ITA 42.8, SWE 41.4,
  NLD 38.5, ESP 36.7, GBR 34.4, OECD 34.1.
- Same host/rate limit as the existing `fetchers/oecd.py`.

#### S6 — OECD Government at a Glance: public employment ✅
- `OECD.GOV.GIP,DSD_GOV@DF_GOV_EMPPS_REP_2025`, `MEASURE=EMPG`,
  `UNIT_MEASURE=PT_EMP` (share of total employment).
- **Coverage verified:** 2007–2023, all peers.
- **Sample 2023:** FRA 20.7 %, DEU 11.5, NLD 12.3, ITA 13.7, ESP 15.3,
  GBR 17.1, SWE 28.2.
- The same dataflow family also lists `DF_GOV_PPROC_2025` (procurement as % of
  GDP) and `DF_GOV_INT_2025` — not sampled; check before use.

#### S7 — State performance indicators (PAP / RAP) ✅
The single most direct accountability source: every budget programme publishes
objectives, indicators, a **target** and the **result**.
- Portal: `https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/…`
  (OpenDataSoft, Licence Ouverte v2.0).
- Datasets verified:
  - `performance-atteinte-de-la-cible-generale-du-budget-de-l-etat-depuis-2007`
    — 18 rows, one per year 2007–2024: share of indicators with target met /
    improved / not improved / not reported.
    **Sample:** target met 41.8 % (2007), peak 46.3 % (2019), **38 % (2024)**;
    *not reported* 20–29 % every year.
  - `performance-execution-et-atteinte-de-la-cible-du-budget-de-l-etat-jusqu-au-niveau-sous-indicateur`
    — 6,338 rows, 2022–2024, per sub-indicator: mission, programme, objective,
    indicator, unit, `cible`, `execution`, `atteinte_de_la_cible`.
  - `performance-de-la-depense-rap-2025` (updated 2026-06-04) — 2,140 rows with
    `exec_2023`, `exec_2024`, `2025_cible`, `exec_2025`, `atteinte_de_la_cible_2025`,
    `2026_cible`. **Sample:** 684 target met, 338 improved, 623 no improvement,
    292 not reported, 139 not retained, 64 blank.
  - `plf-2025-performance` (PAP: 2022–2023 results, 2024–2027 targets).
- **Caveats:** dataset IDs and column names change every vintage (e.g.
  `exec_2025`) → discover via catalog search and normalise per vintage. Don't
  compare the RAP 2025 share (684/2140 = 32 %) with the 2007–2024 series until
  the denominator is computed the same way.
- Example row (Justice, P166): "Nombre d'affaires traitées par magistrat",
  target 1,040, result *non renseigné* — the gaps are themselves informative.
- **Re-verified 2026-11-08 — see Part 5.2.** Corrections to the list above:
  `performance-de-la-depense` (no year in its id) is the **RAP 2024**; the
  summary series still stops at 2024; the denominator question is solved
  (Part 5.3).

#### S8 — Eurostat EDP notification tables ⚠️
Twice a year (April, October) the government reports its deficit and debt to
Eurostat **including its own plan for the current year**.
- Current files are linked from
  `https://ec.europa.eu/eurostat/web/government-finance-statistics/excessive-deficit-procedure/edp-notification-tables`
  (per-country PDF, e.g. `FR-2026-10.pdf`, 12 pages; URL contains a file id →
  scrape the page for the link).
- **Sample, Table 1 (October 2026, € bn):** deficit 2022–2025 actual
  −125.9 / −151.9 / −169.1 / −151.6; **2026 planned −153.7**; interest (D41)
  65.7 in 2025 → **78.3 planned 2026**; debt 3,460.1 → 3,623.7 planned. Same
  table gives the sub-sector split and GFCF. Text extracts cleanly with
  `pdfplumber` (fixed template).
- **Caveat:** older notifications are on CircaBC, whose API returned
  **401 (auth required)**. Going forward the pipeline can capture each new
  notification automatically; backfilling history needs a one-time manual
  download via the CircaBC web UI, committed to the repo with source URLs
  (principle 4).
- **Why it matters:** "planned in April vs. final outturn" is a sourced,
  structured measure of forecast reliability — no hand-typed numbers.

#### S9 — OFGL local-authority finances ✅
- `https://data.ofgl.fr/api/explore/v2.1/catalog/datasets/{id}` (OpenDataSoft,
  Licence Ouverte v2.0, updated 2026-07-28).
- Datasets: `ofgl-base-communes` / `-consolidee` (2018–2025),
  `ofgl-base-departements` and `ofgl-base-regions` (2012–2025), `ofgl-base-gfp`
  (intercommunalités, 2018–2025), plus dotations, fiscalité (`rei`).
- Fields include `agregat` (≈50 aggregates: encours de dette, frais de
  personnel, dépenses d'équipement, épargne brute, impôts locaux…), `montant`,
  **`euros_par_habitant`**, `ptot`, and peer-grouping fields
  (`tranche_population`, `rural`, `montagne`, `touristique`, `qpv`) — like-for-like
  comparison is built in.
- **Volume test:** CSV export of 4 aggregates × every commune for 2024 =
  139,728 rows, 10.5 MB, 14 s (`/exports/csv` with `select` + `where`). The full
  base is ~2.6 M rows/year — always filter server-side.
- **Sample (Lyon, consolidated, 2025):** debt 730 €/hab, staff costs 808 €/hab,
  capital spending 308 €/hab, gross savings 166 €/hab.

#### S10 — DECP public procurement (consolidated) ⚠️
- data.gouv.fr dataset `608c055b35eb4e6ee20eb325` "DECP consolidées (format
  tabulaire)" — community consolidation (code: `ColinMaudry/decp-processing`),
  refreshed daily, Licence Ouverte v2.0. `decp.parquet` 250 MB (CSV 2.6 GB).
- **Verified:** 3.32 M rows (1.85 M distinct `uid` — rows include contract
  modifications; filter `donneesActuelles`), contracts 2018–2026, 67 columns
  incl. `offresRecues`, `procedure`, `acheteur_*`, `titulaire_*`, `codeCPV`,
  `montant`, anomaly flags.
- **Bid count fill rate:** < 1 % (2018–19), 14–20 % (2020–23), **79 % (2024),
  82 % (2025)**. Among filled: single-bid share **24.7 % (2024), 23.7 % (2025)**.
- **Hard caveat — amounts:** summing `montant_rationalise` gives ~685 bn € for
  2025, several times total French procurement: amounts are framework
  *ceilings*, not spend. 101 k rows flagged `suspect`, 33 k `aberrant`.
  ⇒ Use for **rates and counts** (single-bid, no-competition procedures, buyer
  categories), **never** for euro totals.
- Third-party consolidation of official data → label it on screen.

#### S11 — OpenFisca-France ✅
- Public API `https://api.fr.openfisca.org/latest/` (running openfisca-france
  175.0.45; PyPI has 176.1.6). 2,777 variables.
- **Sample:** single person, `salaire_de_base` 36,000 € (2025) →
  `impot_revenu_restant_a_payer` = −1,495 € (income tax due).
- **Caveats:** variable names change between versions (`irpp` no longer
  exists) and some are monthly-only (`salaire_net`) → pin a version. Don't call
  the public API from the browser; pre-compute archetype households in the
  pipeline with the pinned package. Check the package licence before bundling
  (not verified this session).

#### S12 — HATVP open data ⚠️
- `https://www.hatvp.fr/livraison/opendata/liste.csv` — 13,065 published
  declarations (interests/assets) of elected officials and senior officials.
- `https://www.hatvp.fr/agora/opendata/agora_repertoire_opendata.json` —
  139 MB lobbying register, 4,105 organisations, per-year spend bands and
  declared actions (`objet`, `decisionsConcernees`, `reponsablesPublics`).
- **Sample:** 8,468 declared lobbying actions mentioning a finance bill
  (PLF/PLFSS) since 2019, by 1,060 organisations, ~1,000–1,500 per year.
- **Caveats:** matching actions to specific tax measures is free-text; spend is
  in bands. Licence not confirmed this session. Declarations of individuals are
  out of scope for a fiscal dashboard (privacy and neutrality); use the lobbying
  register in aggregate only.

#### S13 — State subsidies to associations (jaune budgétaire) ⚠️
- `plf25-donnees-de-l-annexe-jaune-effort-financier-de-l-etat-en-faveur-des-associations`
  — per recipient: programme, SIREN, name, amount, purpose, commune.
- Older vintages exist (PLF 2020–2023). Dataset IDs differ per year; SIREN is
  sometimes `NR CHORUS`. Good for a searchable "who receives what" table.

#### S14 — AFA / SSMSI probity offences ⚠️
- `atteintes-a-la-probite-dans-les-decisions-de-justice-donnees-nationales-agregees-2021-2025`
  (355 rows) and `ssmsi-afa-atteintes-a-la-probite0` (by département: corruption,
  embezzlement of public funds, prise illégale d'intérêts, favouritism…).
- Small counts, many masked (`<5`). Context panel only, not a KPI.

#### S15 — Voted credits by destination ⚠️
- `plf25-depenses-2025-selon-destination` (2,404 rows: ministry, mission,
  programme, action, AE, CP), with earlier vintages back to 2020.
- **Caveat:** no PLF/LFI 2026 credits dataset on the portal as of 2026-10-26
  (only "budget vert"). Voted-vs-executed by mission is therefore not reliably
  automatable yet; the existing monthly execution covers totals only.

### 1.3 Rejected or deferred

| Source | Result of check | Decision |
|--------|-----------------|----------|
| Cour des comptes — recommendations follow-up | data.gouv dataset covers 2015 – May 2018 only; the annual follow-up report is PDF | ❌ Not automatable. Possible later as a small curated table. |
| DGAFP headcount series (data.gouv) | Last updated 2018–2019 | ❌ Use OECD S6 instead |
| AFT (aft.gouv.fr) — indexed debt share, avg. maturity, issuance rates | Site returns 403 to automated requests; not verified | ❌ Deferred. Eurostat S4 covers holders/maturity buckets. |
| PLRG (final execution by mission) | `plrg-2024`, `…-plrg-2025` still contain only a PDF notice | ❌ Confirms `known-gaps.md` |
| ONDAM voted vs realised | No tabular source found | ❌ Use S2 (`S1314`) + COFOG GF07 instead |
| Jaune "personnels des cabinets ministériels" | Only 2015–2018 vintages on the portal | ❌ Stale |
| Past PLF macro forecasts | Only in PDFs (Rapport économique, social et financier) | Replaced by S8 (EDP planned figures) |

---

## Part 2 — Phased plan

Effort: **S** ≤ 1 session, **M** 2–3 sessions, **L** 4+ sessions. Each item lists
acceptance criteria; per `CLAUDE.md`, methodology/source text changes need the
processor **and** a regenerated `backend/data/output/*.json` on the VPS.

### Phase 0 — Credibility fixes (S, do first)

| # | Item | Files | Done when |
|---|------|-------|-----------|
| 0.1 | Rename "Coût administratif" → "Part de la masse salariale publique"; rewrite explainer to say it includes teachers, health staff, police (Eurostat split above). Replaced by a real overhead KPI in 1.2. | `frontend/src/data/registry.ts`, `backend/processors/kpi_overhead.py` (kpi_name/methodology) | No on-screen text calls total D1 "administrative" ✅ 2026-11-04 |
| 0.2 | "Dépenses productives": state the value judgement in the explainer (education & health excluded by convention), or rename "Part des dépenses d'infrastructure et d'affaires économiques" | `registry.ts`, `processors/kpi_allocation.py` | Explainer names what is excluded and why ✅ 2026-11-04 — then renamed "Affaires économiques, environnement et logement" (the COFOG function names), polarity neutral |
| 0.3 | Fix overview intro: "depuis 1995 … comparés à la moyenne de l'OCDE" is true for 3/10 KPIs → "lorsque c'est possible" | `frontend/src/pages/Overview.tsx` | Intro claim matches data ✅ 2026-11-04 |
| 0.4 | Show the country peers already computed (DEU, ESP, GBR, ITA, NLD, SWE), not only OECD avg; France highlighted, peers muted, toggle per country | `frontend/src/data/adapters.ts` (`oecdSeries` keeps only `OECD_AVG`), `components/TimeSeriesChart.tsx` | Overhead, productive, deficit, debt charts can show each peer ✅ 2026-11-04 |
| 0.5 | Methodology page lists all sources behind displayed KPIs — today it names only INSEE, OECD, GTED; add Urssaf (`wage_ratio`) and data.economie.gouv.fr (`monthly_execution`). France Travail is fetched but unused (orphaned, see `known-gaps.md` A) — don't list it | `frontend/src/pages/Methodology.tsx` | Every source feeding a visible KPI is named ✅ 2026-11-04 |
| 0.6 | Chart tooltips/axes formatted with units (%, Md€, ×) in fr-FR | `TimeSeriesChart.tsx`, `data/format.ts` | No raw unformatted floats in tooltips ✅ 2026-11-04 |

### Phase 1 — Eurostat & OECD foundation (M)

| # | Item | Data | Done when |
|---|------|------|-----------|
| 1.1 | New `fetchers/eurostat.py` (JSON-stat decoder, cache raw per PRD §12.3) for S1–S4; peers DE/IT/ES/NL/SE + EU27 (`EU27_AVG`, label "Moyenne UE à 27"; see 4.2 on averages) | S1–S4 | Raw cached; `meta.json` shows step `ok` ✅ 2026-11-08 (raw verified locally; S3 not fetched — 1.5 uses S5, so it would be an orphaned input) |
| 1.2 | **True overhead KPI**: compensation in GF01 (general public services) ÷ total expenditure, France vs peers, 1995–2024; optionally "wage bill by function" stacked view | S1 | New `kpi_admin_overhead.json` with peers; keep `overhead_rate` (already "Part de la masse salariale publique" since 0.1) ✅ 2026-11-08 — "Masse salariale des services généraux"; optional stacked view not built |
| 1.3 | **Pensions isolated**: GF1002 (old age) as % of spending and % GDP vs peers; re-base "Protection sociale vs investissement" on P51G from Eurostat with peers | S1 | Closes known-gaps B "pension/investment peers ❌" ✅ 2026-11-08 — new `kpi_pensions.json`; `pension_investment` re-based on Eurostat GF10 / P51G for France and peers |
| 1.4 | **Who runs the deficit**: balance by sub-sector (State / local / social security), € bn and % GDP, 1995–2025 | S2 | New KPI under Soutenabilité ✅ 2026-11-08 — `kpi_deficit_subsector.json` |
| 1.5 | **Tax burden** (prélèvements obligatoires) vs peers + OECD avg (`OECD_REP` is a true OECD aggregate — the only series that may be labelled "Moyenne OCDE"; give it its own key, not `OECD_AVG`), 1965–2024 | S5 (or S3) | New KPI, one definition, named on chart ✅ 2026-11-08 — verified on the VPS; `kpi_tax_burden.json`, OECD definition named in explainer and methodology |
| 1.6 | **Who holds the debt**: non-residents / Banque de France / domestic, 2020–2025 | S4 | Detail panel on the debt KPI ✅ 2026-11-08 — `debt_holders` block in `kpi_sustainability.json`, France only |
| 1.7 | **Public employment** share vs peers, 2007–2023 | S6 | New KPI under Efficacité ✅ 2026-11-08 — verified on the VPS; `kpi_public_employment.json`; the dataflow publishes no OECD aggregate, so no average line |
| 1.8 | Peers for `debt_service` (interest payable, % GDP) | S2 `D41PAY` | Closes known-gaps B "debt_service ⚠️ unconfirmed" ✅ 2026-11-08 — KPI kept as interest / revenue: peers = D41PAY / TR |
| 1.9 | Decide fate of the INSEE+OECD COFOG stitch once Eurostat is wired (Eurostat runs 1995–2024 on one basis) | S1 | `runtime-discoveries.md` entry recording the decision ✅ 2026-11-08 — stitch retired: all COFOG KPIs on Eurostat for France and peers (Session H) |

### Phase 2 — Citizen framing (M)

| # | Item | Done when |
|---|------|-----------|
| 2.1 | **€ per inhabitant, constant euros** on every euro-denominated KPI: wire the orphaned `cpi` (monthly → annual average) and an INSEE population series (resolve via the idBank resolver) | Toggle "% du PIB / € par habitant (euros 2025)" on detail pages ✅ 2026-11-12 — 7 KPIs (deficit + debt, deficit by sub-sector, debt interest, pensions, health spending, tax burden, tax expenditure), France only, from 1996; `per_capita` block in each payload, `?vue=habitant`; live on the VPS the same day |
| 2.2 | **"Où vont 1 000 € de dépense publique"** — COFOG level-1/2 breakdown of 1,000 € (S1), with year selector and peer comparison | New page; numbers reconcile to S1 totals |
| 2.3 | **"Mes impôts"** — 6–10 archetype households (single minimum wage, median couple with 2 children, retiree, high earner…) computed with pinned OpenFisca in the pipeline; each household's direct taxes split by COFOG shares | Static JSON, no runtime call to the public API; archetypes and assumptions documented |
| 2.4 | **Data-driven context sentences** per KPI: historical rank ("plus haut depuis 1996"), peer rank ("1er sur 7"), 10-year change — generated by processors, not hand-written | Every KPI card shows one auto sentence ✅ 2026-11-14 — 14 of 16 cards (not performance, monthly_execution), also under the detail headline in the ratio view; facts in a `context` block of each payload, worded in `format.ts` (Part 6) |
| 2.5 | **Interest vs ministries**: debt interest (S2 `D41PAY`, S8 planned) next to the voted credits of the largest missions (S15). Interest per inhabitant already exists (2.1: `per_capita` in `kpi_debt_service.json`) | Chart with source per bar; 2026 marked "prévision du gouvernement" |

### Phase 3 — Accountability: promises vs results (M–L)

| # | Item | Data | Done when |
|---|------|------|-----------|
| 3.1 | **Tableau de bord de la performance de l'État** (brief in Part 5): share of targets met per year since 2007 (incl. "non renseigné"); drill-down by mission → programme → indicator with target vs result; filter "objectifs manqués", "non renseignés" | S7 | Fetcher discovers yearly vintages via catalog search; per-vintage column normalisation tested; consistent denominator documented ✅ 2026-11-09 — `kpi_performance.json` (official series only, 2007–2024) + `performance_detail_YYYY.json` 2022–2025, page `/performance` |
| 3.2 | **Prévisions vs réalité**: for each year, the deficit/interest/debt the government planned (April EDP notification) vs final outturn; forecast error in pp of GDP | S8 | Auto-capture new notifications; one-time archive backfill committed with URLs; parser tests on ≥ 3 vintages |
| 3.3 | **Factual timeline bands** on long series: crises (2008, 2020), governments and finance ministers with dates — same treatment for every government | Static, sourced list (Légifrance/gouvernement.fr dates) | Bands toggleable; no colour coding by party |
| 3.4 | Monthly execution: add same-month-last-year line and, when the LFI credits dataset exists for the year, the voted annual total | existing + S15 | Shows "à fin mars, X % des dépenses votées" when data allows |

### Phase 4 — Local finances: "Ma commune" (L)

| # | Item | Done when |
|---|------|-----------|
| 4.1 | Fetcher for OFGL (communes consolidated, GFP, départements, régions) — server-side filtered exports of ~10 aggregates, all years | Raw cached, < 100 MB total |
| 4.2 | Processor producing per-territory JSON sharded by département (debt, staff costs, capital spending, gross savings, local taxes — all €/hab) plus strata medians from `tranche_population` | Each commune compares to the median of its stratum |
| 4.3 | Search-by-commune page (name or postcode) with 2018–2025 series and stratum comparison; "durée de désendettement" (debt ÷ gross savings) as the headline solvency ratio | Works for any of ~35 k communes; mobile-friendly |
| 4.4 | Département and région views (2012–2025) | Same template |

### Phase 5 — Procurement & integrity (M)

| # | Item | Data | Done when |
|---|------|------|-----------|
| 5.1 | **Concurrence dans la commande publique**: single-bid share and "sans publicité ni mise en concurrence" share by year (2024+ only, where `offresRecues` ≥ ~80 % filled), by buyer category and by département | S10 (DuckDB over the parquet, weekly) | Counts only; fill rate displayed next to every rate; no euro totals |
| 5.2 | Buyer drill-down: top buyers by single-bid share (min. contract threshold to avoid noise) | S10 | Methodology explains thresholds and the third-party consolidation |
| 5.3 | **Lobbying on finance bills**: declared actions targeting PLF/PLFSS per year, by organisation category | S12 | Aggregate only; licence confirmed first |
| 5.4 | Searchable table of State subsidies to associations | S13 | Per-recipient, per-programme |
| 5.5 | Probity context panel (offences by département, 2021–2025) | S14 | Clearly labelled as context, not performance |

### Phase 6 — Reach & reuse (S–M, can run in parallel)

| # | Item | Done when |
|---|------|-----------|
| 6.1 | CSV download for every chart + stable permalinks per KPI/territory | Download button on each detail page |
| 6.2 | Per-KPI Open Graph image (latest value + sparkline) | Sharing a KPI link shows its own card |
| 6.3 | Prerender routes at build time (SPA is otherwise near-invisible to search engines) | `curl` of a KPI URL returns its title and figure in HTML |
| 6.4 | "Quoi de neuf" changelog generated from `meta.json` diffs + RSS feed | Feed updates when the cron publishes new data |
| 6.5 | Embeddable chart iframe for journalists | `/embed/kpi/<slug>` route |
| 6.6 | Accessible data table under each chart | Screen-reader users can read every value |

---

## Part 3 — Suggested order

1. ~~**Phase 0** in full (one session) — protects everything else.~~ ✅ 2026-11-04
2. ~~**1.1–1.4** — one Eurostat fetcher closes most of `known-gaps.md` and gives
   the honest overhead KPI.~~ ✅ 2026-11-08, with the rest of Phase 1.
3. ~~**3.1** (performance scorecard) — highest accountability value per
   effort; data is clean and official. Brief: Part 5.~~ ✅ 2026-11-09
4. ~~**2.1**~~ ✅ 2026-11-12. ~~**2.4**~~ ✅ 2026-11-14.
5. ▶ **NEXT — Phase 4** — largest new audience (local relevance).
6. **3.2, 5.1**, then the rest of Phases 2, 5 and 6.

Phases group work by theme; this list sets the order. Phase 2 cannot be done in
one block yet: 2.5 needs S8 (the source of 3.2) and S15 (latest vintage PLF
2025), and 2.3 needs OpenFisca (heavy). 2.2 and 2.4 are self-contained.

After each item: tick it in this file (append "✅ YYYY-MM-DD" to its "Done
when" cell), update `known-gaps.md` (remove closed gaps, add new ones), append
a session entry to `runtime-discoveries.md` (Session J, K, … — Session H was
Phase 1, Session I item 3.1, Session J item 2.1, Session K item 2.4), update the README's KPI table if a KPI was added, and move the
"▶ NEXT" marker above.

---

## Part 4 — Implementation guide

### 4.1 Re-verify before building
Each source was checked once, on 2026-10-26. Before implementing an item, re-run
its appendix query and confirm: HTTP 200, the same dimensions/columns, and a
recent last period. Known drift points:
- data.economie.gouv.fr publishes a **new dataset ID per budget vintage**
  (`plf-2025-performance`, `performance-de-la-depense-rap-2025`, …) with
  year-stamped column names (`exec_2025`, `2026_cible`). Discover the newest
  vintage via the catalog search
  (`…/api/explore/v2.1/catalog/datasets?where=search("performance")&limit=100&select=dataset_id`)
  and normalise columns per vintage.
- OECD dataflow IDs carry an edition suffix (`…_2025`); update when the next
  Government at a Glance edition ships (PRD §12 constraint 2).
- INSEE revises recent years at each release (2026-11-12: deficit 2024
  −5.79 → −5.76 % of GDP, 2025 added). Refreshing a fixture can therefore
  break a frontend test that hard-codes a value (`adapters.test.ts` does for
  the 2024 deficit): update the expected value and note the revision in the
  session entry; it is not a bug.
- If a source fails re-verification, record it in `known-gaps.md` §C and skip
  the item rather than working around it.

### 4.2 Backend conventions (follow existing code)
- **Fetchers** (`backend/fetchers/*.py`): `requests.get(..., headers=DEFAULT_HEADERS, timeout=...)`
  using `DEFAULT_HEADERS` from `fetchers/__init__.py`; call
  `save_raw("<source>", data)` **before** any processing (writes
  `data/raw/<source>_<YYYY-MM-DD>.json`, PRD §12 constraint 3). For
  OpenDataSoft portals (data.economie.gouv.fr, data.ofgl.fr) reuse
  `fetch_ods_records(base, dataset_id)` for small datasets; the records endpoint
  pages 100 rows at a time and does not suit large pulls (OFGL communes: millions of rows) — use
  `/exports/csv` (or `/exports/json`) with server-side `select`/`where`
  instead. For OECD reuse `_fetch_oecd_csv` in `fetchers/oecd.py` (20 req/min
  limit is already handled there).
- **Processors** (`backend/processors/*.py`): read only cached raw via
  `latest_raw("<source>")`, never re-fetch; deterministic. Write with
  `write_output("kpi_<id>.json", payload)`. Standard payload shape (see
  `frontend/src/data/types.ts` → `StdSeriesKpi`): `kpi_id`, `kpi_name`,
  `description`, `unit`, `source`, `methodology`, `last_updated` (`now_iso()`),
  `france: [{year, value, source?}]`, `peers: {ISO3: [...], OECD_AVG: [...]}`,
  `latest` (`build_latest(france)`). `source` and `methodology` strings are
  shown to users → write them in French.
- **Orchestration** (`backend/run_pipeline.py`): register each fetcher and
  processor with `_run_step("<name>", fn, sources)` in `run_annual` or
  `run_monthly`. `_run_step` is fail-soft; raise `NotImplementedError` to mark a
  step `skipped`.
- **Shared processor helpers** (`processors/__init__.py`): INSEE
  `load_insee_series`, `annual_values`, `year_end_value`; OECD
  `load_oecd_long`, `peer_series`; Eurostat `load_eurostat_long`, `pick`,
  `ratio`, `series_by_country`, `france_and_peers`, `EUROSTAT_PEER_NOTE`;
  € per inhabitant (2.1) `per_capita_block` (amounts in current euros →
  `{base_year, series}` in constant euros of the latest full CPI year),
  `cpi_annual`, `france_values`, `PER_CAPITA_SOURCE`, `per_capita_note`;
  context sentence (2.4) `build_context(france, peers)` → the payload's
  `context` block (call it for every new yearly KPI, beside `build_latest`);
  INSEE units: CNT flows (B9NF, D41, OTE…) and CNA GDP in **M€**, the
  Maastricht debt level (`public_debt_eur`) in **Md€**, population in
  persons, CPI monthly with 2025 = 100 (from 1996);
  output `build_latest`, `write_output`, `now_iso`. Fetchers:
  `fetchers/__init__.py` (`DEFAULT_HEADERS`, `save_raw`, `fetch_ods_records`),
  `fetchers/eurostat.py` (`decode_jsonstat`).
- **Peers naming (implemented, Phase 1):** peers are keyed by ISO3 (`DEU`,
  `GBR`…) plus **at most one average key** per series:
  `OECD_AVG` = unweighted mean of the 6 peers computed by `peer_series`, shown
  as "Moyenne des 6 pays" — **never** label it an OECD average; `EU27_AVG` =
  Eurostat's EU27 aggregate ("Moyenne UE à 27"); `OECD_REP` = OECD Revenue
  Statistics average ("Moyenne OCDE"). Eurostat-based KPIs have 5 peers (no UK)
  and must not store a 5-country mean under `OECD_AVG`. Frontend: key → label
  in `AVERAGES` (`frontend/src/data/adapters.ts`), key → card badge in
  `BADGES` (`components/KpiCard.tsx`) — add both for any new average.
  `KpiView.comparison` is still a single slot; the first KPI needing two
  averages must turn it into a list.
- **Tests:** backend — `cd backend && .venv/bin/python -m pytest -q` (files:
  `test_api.py`, `test_phase1.py`, `test_insee_resolver.py`,
  `test_performance.py`, `test_per_capita.py`; pytest/httpx come
  from `requirements-dev.txt`). For processor tests, copy the `raw_dir` fixture
  in `test_phase1.py` (monkeypatches `processors.RAW_DATA_DIR` /
  `OUTPUT_DATA_DIR` to a temp dir and writes small raw files); processors
  reading INSEE series use the `insee_raw` fixture in `tests/conftest.py`
  (built on the module's `raw_dir`). Frontend — in
  `frontend/`: `npm test` (vitest), `npx tsc -b`, `npm run build`,
  `npm run lint`. **Lint has 11 pre-existing errors** (`no-explicit-any` in
  tests and adapters, `set-state-in-effect` in `Overview.tsx`): don't add any.
- **Dependencies:** pin exact versions in `backend/requirements.txt`.
  New ones implied by this roadmap: `duckdb` (DECP, 5.1), `pdfplumber` (EDP,
  3.2), `openfisca-france` (2.3 — heavy; consider a separate script/venv).

### 4.3 Eurostat JSON-stat decoding (no extra dependency)
The API returns JSON-stat 2.0: `id` (ordered dimension names), `size`
(dimension lengths), `dimension[d].category.index` (code → position) and a
sparse `value` object keyed by the flat row-major index. Decode with:

```python
def decode_jsonstat(d: dict) -> dict[tuple, float]:
    dims, sizes = d["id"], d["size"]
    codes = [sorted(d["dimension"][k]["category"]["index"].items(), key=lambda x: x[1]) for k in dims]
    out = {}
    for flat, v in d["value"].items():
        i, pos = int(flat), []
        for s in reversed(sizes):
            pos.append(i % s); i //= s
        pos.reverse()
        out[tuple(codes[j][p][0] for j, p in enumerate(pos))] = v
    return out  # keys ordered as d["id"], e.g. ('A','MIO_EUR','S13','GF01','D1','FR','2024')
```
Filters are repeated query params (`geo=FR&geo=DE`); `sinceTimePeriod=1995`.

### 4.4 Large / special sources
- **DECP (5.1):** download `decp.parquet` (~250 MB; resolve the current URL from
  the dataset API, it changes daily) weekly at most; query with DuckDB; keep only
  rows with `donneesActuelles = true`; save the computed aggregates (not the
  parquet) as the raw JSON. Report the `offresRecues` fill rate alongside every
  rate; never sum `montant`.
- **EDP (3.2):** scrape the Eurostat EDP page for the `FR-YYYY-MM.pdf` link,
  extract Table 1 (page 2) with `pdfplumber`; numbers use `.` as thousands
  separator (`-153.715` = −153,715 M€). Commit backfilled archive PDFs' extracted
  values (not the PDFs) with their source URLs.
- **OpenFisca (2.3):** variables are versioned; some are monthly-only
  (`salaire_net` must be requested per month). Pin the package version and
  record it in the output's `methodology`.

### 4.5 Frontend wiring for a new KPI
1. Add an entry in `frontend/src/data/registry.ts` (`slug`, theme, unit,
   polarity, French title + explainer, adapter). Name the KPI after what it
   measures, not a judgement ("productive", "administrative" were both removed
   in Phase 0). Use polarity `neutral` unless a rise is uncontroversially better
   or worse (principle 2) — it colours the YoY arrow red/green.
2. Add its `kpi_<id>` to `ALL_APP_IDS` in `frontend/src/data/api.ts`.
3. Put a real pipeline output copy in `frontend/src/fixtures/kpi_<id>.json`
   (used in dev/tests when `VITE_API_BASE` is empty).
4. Non-standard payload → add an adapter in `adapters.ts` and types in
   `types.ts`. Patterns that exist: `KpiView.series` may hold several lines
   (the first, role `france`, drives the card value and sparkline);
   `secondary` is a second chart; `panels` are further charts; any
   `SecondaryBlock` may carry a `note` shown under its title. Give every line
   id of a multi-series chart a colour in `SERIES_COLORS`
   (`components/TimeSeriesChart.tsx`). Examples: `adaptPensions`,
   `adaptDeficitSubsector`, `adaptSustainability` (debt-holders panel).
   A KPI in euros or % of GDP should also get the "€ par habitant" view:
   a `per_capita` block from `per_capita_block` in the processor, then
   `perCapitaView` in its adapter (or `withPerCapita(adaptStandard, …)` in the
   registry); `KpiDetail` shows the toggle when `KpiView.perCapita` is set.
   Set `context: fmtContext(raw.context, unit)` in a custom adapter
   (`adaptStandard` already does); pass `{ value }` for a public balance
   so its extremes read as deficits.
5. Update the KPI counts in `src/data/registry.test.ts` and
   `src/pages/Overview.test.tsx` (16 today).
6. New page → route in `frontend/src/App.tsx` (routes today: `/`,
   `/kpi/:slug`, `/methodologie`, `/performance`) and a link to it (header nav
   in `components/AppShell.tsx`, or from a KPI page via `KpiView.drilldown`).
   The only table is the performance drill-down (`pages/PerformanceDetail.tsx`:
   semantic table, stacked cards under 620 px); reuse its pattern. Any new
   source must be named on `pages/Methodology.tsx` and in the footer line of
   `AppShell.tsx`. Fixtures are lazy-loaded (`import.meta.glob` without
   `eager`), so large fixtures don't weigh on the bundle.
7. Fixtures must be real pipeline output. If an input can only be fetched on
   the production server, copy its raw file from the server's
   `backend/data/raw/` into the local `backend/data/raw/` and run the
   processor locally. With `scp`, give each glob as its own source
   (`'host:…/raw/oecd_debt_*.json' 'host:…/raw/oecd_deficit_*.json' …`):
   recent `scp` goes through SFTP, which expands `*` but not `{a,b}`. As of
   2026-11-12 the Mac has every raw input except the monthly ones
   (budget execution, Urssaf, France Travail); INSEE can be refreshed
   locally (`python -m fetchers.insee_idbank_resolver` then
   `python -m fetchers.insee_bdm`).

### 4.6 Environments and shipping
- **Development** happens on the owner's Mac: backend venv `backend/.venv`,
  frontend `npm` in `frontend/`. Eurostat, INSEE and
  data.economie.gouv.fr are reachable from it; **`sdmx.oecd.org` is not**
  (Cloudflare challenge). Do not try to get around it (spoofed user agents
  etc. are refused as bot-check circumvention): fetch or verify OECD data on
  the VPS.
- **Production** is a VPS. How to reach it is deliberately not written in
  this public repo: ask the owner (Claude Code keeps it in its private local
  memory). The commands below run from the repo root on the server.
- **The owner runs `git pull` on the server themselves.** Ask them, then
  continue.
- **Backend runs in Docker Compose** (`docker-compose.yml`): service `api`
  (uvicorn on `127.0.0.1:8077` behind nginx → `https://fisc.159-69-91-118.sslip.io`)
  and the one-shot service `pipeline`. The code is baked into the image, so
  after every pull: `docker compose up -d --build api` (rebuilds the image both
  services share). Run the pipeline with
  `docker compose run --rm pipeline --mode annual|monthly|full`, or a single
  step with `docker compose run --rm --entrypoint python pipeline -m processors.<module>`.
  Data lives in `backend/data/` (mounted volume). The API reads the JSON fresh
  per request: no restart after a pipeline run. Check step statuses in
  `backend/data/output/meta.json`. After adding an INSEE resolver rule, run
  `--mode annual` (the resolver only runs there, before the INSEE fetch).
- **Claude Code and the VPS:** its permission classifier blocks SSH to the
  server unless the owner has asked for server steps in the conversation.
  When the owner says to go ahead, it can run the Docker and `curl` steps
  itself; otherwise it gives the owner the commands (prefixed with `!` so they
  run from the Claude Code prompt).
- **Cron** (on the server, not in the repo): monthly `0 3 5 * *`; annual
  `0 4 1 2,6,11 *` (1 Feb, 1 Jun, 1 Nov). Check a new source's release dates
  against this: EDP notifications late April / late October, RAP early June
  (performance summary series updated in July in 2025), OFGL mid-year.
- **Git flow when the owner asks to ship:** commit on `dev` → push `dev` →
  fast-forward `main` to `dev` → push `main` → `git checkout dev`. "Commit"
  alone means commit only. The GitHub repo is now `Arnobgr/fiscoscope`; the
  local `origin` points there since 2026-11-12 (the old URL still redirects).
- **Frontend:** Cloudflare Pages **auto-deploys `main`**
  (`https://fiscoscope.pages.dev`, built with `VITE_API_BASE` pointing at the
  VPS). A frontend that requests a new output file must therefore reach `main`
  only after the VPS has produced that file, or its card shows "Données
  momentanément indisponibles". Safe order for a new KPI: push `dev` → owner
  pulls on the VPS → rebuild, run the step, check with
  `curl https://fisc.159-69-91-118.sslip.io/api/kpi/<name>` → push `main`.

---

## Part 5 — Brief for the next item: 3.1 Tableau de bord de la performance de l'État

**Status:** ✅ done and live 2026-11-09 (Session I in `runtime-discoveries.md`, which
records the decisions taken on 5.5 and the answers to 5.6). Kept as the
reference for the performance datasets and as a model brief.

### 5.1 Goal
Every State budget programme publishes objectives and indicators, each with a
**target** set by the administration and a **result**. Show, per year since
2007, the share of indicators whose target was met, missed but improved, missed
without improvement, or not reported — and let a citizen drill down
mission → programme → indicator to see target vs result. Principle 2 applies:
the State's own targets next to the State's own results, no adjectives, no
ranking of ministries.

### 5.2 Data — data.economie.gouv.fr (OpenDataSoft, Licence Ouverte v2.0)
API base: `https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets`.
The attainment category values are identical in all detail datasets:
`cible atteinte`, `amélioration`, `absence amélioration`,
`donnée non renseignée`, `donnée non retenue`, and blank.

| Key | Dataset id | Content (checked 2026-11-08) |
|-----|------------|------------------------------|
| **A** — summary | `performance-atteinte-de-la-cible-generale-du-budget-de-l-etat-depuis-2007` | 18 rows, one per RAP year 2007–2024. Fields `rap` (year as float), `cible_atteinte`, `amelioration`, `absence_amelioration`, `donnees_non_renseignees` — fractions 0–1 summing to ~1. 2024: 0.38 / 0.15 / 0.27 / 0.20. Last modified 2025-07-02: **no 2025 row yet**. |
| **B** — detail 2022–2024 | `performance-execution-et-atteinte-de-la-cible-du-budget-de-l-etat-jusqu-au-niveau-sous-indicateur` | 6,338 rows: `annee` 2022 (2,012), 2023 (2,149), 2024 (2,177). Fields `annee`, `type_de_secteur` (Mission / Programme), `mission`, `code_programme`, `programme`, `code_externe_objectif`, `libelle_objectif`, `ordre_ind`, `code_externe_indicateur`, `libelle_indicateur`, `facteur_de_performance`, `code_interne_sous_indicateur`, `libelle_sous_indicateur`, `cotation`, `unite`, `cible`, `execution`, `atteinte_de_la_cible`, `commentaire`. |
| **C** — detail 2025 | `performance-de-la-depense-rap-2025` | 2,140 rows (Mission 320, Programme 1,820), modified 2026-06-04. Year-stamped columns: `exec_2023`, `exec_2024`, `2025_cible`, `exec_2025`, `atteinte_de_la_cible_2025`, `2026_cible`, plus `abs*` flag columns, `contexte`, `evolution`, and two unnamed `column_30`, `column_31` (inspect before use). Indicator/objective fields as in B, but `ordre_ssi` instead of `code_interne_sous_indicateur` and no `commentaire`. |
| D — RAP 2024 | `performance-de-la-depense` | Despite the generic id, this is the **RAP 2024** (2,177 rows; `exec_2022`, `exec_2023`, `2024_cible`, `exec_2024`, `atteinte_de_la_cible_2024`, `2025_cible`). Same 2024 rows as B: use one or the other, never both. |

Not needed: `performance-execution-cible-n-1-du-budget-de-l-etat-jusqu-au-niveau-sous-indicateur`
(results + next-year targets, publication 2025 only), `plf-2025-performance`
(PAP: targets, no attainment), and the 2015–2019 PLF/PLR performance datasets
(different formats).

**Vintage drift:** each RAP vintage is a new dataset with an unpredictable id
(`performance-de-la-depense` = 2024, `performance-de-la-depense-rap-2025`) and
year-stamped columns. Discover vintages with the catalog search (5.8, query 1)
and identify the year from the `atteinte_de_la_cible_YYYY` field name, not from
the id.

### 5.3 The denominator (solved — reuse this rule)
Count **rows at sub-indicator level, Mission and Programme rows together**,
exclude `donnée non retenue` and blank, and take the share of each of the four
remaining categories. This reproduces the published summary (A) within ~1 pt:

| Year | Computed (met / improved / no improvement / not reported, %) | Published in A (%) |
|------|-------------------------------------------------------------|--------------------|
| 2022 (B) | 38.6 / 12.2 / 27.4 / 21.8 | 39 / 12 / 26.5 / 22 |
| 2023 (B) | 39.3 / 13.5 / 27.0 / 20.3 | 39 / 13 / 27 / 21 |
| 2024 (B) | 37.8 / 14.6 / 27.7 / 19.9 | 38 / 15 / 27 / 20 |
| 2025 (C) | 35.3 / 17.4 / 32.2 / 15.1 (n = 1,937) | not published yet |

Programme rows alone give 38.8 / 15.4 / 27.7 / 18.1 for 2024, a worse match, so
keep Mission rows in. Recommended headline series: A for 2007–2024, plus the
2025 value computed from C under this rule, flagged as computed by Fiscoscope;
prefer A's figure for a year once A publishes it. Add a test asserting the
computed 2022–2024 shares stay within 1.5 pt of A (guards against drift).

### 5.4 Deliverables
**Backend**
- `fetchers/performance.py`: fetch A by fixed id (`fetch_ods_records`, 18
  rows); B and the discovered RAP vintages (C, and future ones) via
  `/exports/json` (one request each instead of 20–60 pages of 100). Save raw
  before processing, one source per dataset (e.g. `performance_summary`,
  `performance_detail_2022_2024`, `performance_rap_2025`). Fail loudly if
  discovery finds no RAP vintage.
- `processors/kpi_performance.py`: normalise each vintage to one schema
  (`year, sector, mission, programme_code, programme, objective, indicator_code,
  indicator, sub_indicator, unit, target, result, status, comment`). Outputs:
  - `kpi_performance.json` — standard payload (`france` = share of targets met
    per year 2007–2025, `source` per point: published vs computed) plus a
    `breakdown` block with the four shares and `n` per year;
  - a drill-down file (e.g. `performance_detail.json`). `api.py` serves any
    `[a-z0-9_]+` name at `/api/kpi/<name>`, so no API change is needed.
    Measure the size: ~2,000 rows × ~14 fields per year is around 1 MB
    uncompressed; latest year only, or one file per year, may be needed.
- Register fetch and processor steps in `run_annual` (`run_pipeline.py`). The
  RAP lands in early June and the summary updated in July last time, so the
  1 June run may be early; the 1 November run will catch it.
- Tests: per-vintage normalisation with small fixtures, the denominator rule,
  and the 1.5-pt guard above.

**Frontend**
- Registry entry (suggested theme "Dépenses & résultats") and an adapter:
  headline line = share of targets met; a `secondary` block with the four
  categories as lines.
- New drill-down page (route in `App.tsx`, link from the KPI page): mission →
  programme → indicator rows showing target, result, unit, status and comment,
  with filters "objectifs manqués" and "non renseignés". First table in the
  app: make it accessible (roadmap 6.6).
- Name the source on `Methodology.tsx`; data.economie.gouv.fr is already
  listed there and in the footer.
- Fixtures from real output (Part 4.5, step 7).

### 5.5 Decisions to settle with the owner before building
1. **Page shape:** KPI card plus dedicated drill-down page (recommended) or
   card only.
2. **Drill-down years:** latest year only, or 2022–2025 with a year selector
   (file size trade-off).
3. **Per-mission view:** showing each mission's four category counts is
   useful but invites ranking ministries. Recommended: counts per mission,
   sorted alphabetically, never ranked or coloured.
4. **Polarity of the headline:** recommended `neutral` — the administration
   sets and revises its own targets, so a higher share met is not
   self-evidently better performance.
5. **2025 value:** confirm showing the computed 2025 share next to the
   published 2007–2024 series, flagged "calculé par Fiscoscope".

### 5.6 Caveats for the explainer and methodology
- Targets are set by the administration itself and can be revised; the
  indicator set changes every year (~2,000 sub-indicators), so the share is
  not a like-for-like series.
- `donnée non renseignée` means no result was reported: show it, it is
  information.
- Check the official definition of `amélioration` (presumably target missed
  but result better than the previous year) on the dataset page before
  writing copy — not verified.
- Check whether Mission-level indicators repeat Programme-level ones before
  showing both in the drill-down (counting both is what reproduces A).

### 5.7 Done when
The roadmap row's criterion ("Fetcher discovers yearly vintages via catalog
search; per-vintage column normalisation tested; consistent denominator
documented"), plus: KPI card and drill-down page live, tests and lint clean
(no new lint errors), docs updated per "After each item" (Part 3).

### 5.8 Re-verification queries (run before coding)
URL-encode the parameters (`curl -G --data-urlencode` does it).
```text
# 1. Vintage discovery: list performance datasets with modified date and row count
GET {base}?where=search("performance")&limit=100
    → results[].dataset_id, results[].metas.default.modified, .records_count

# 2. Fields of a dataset (look for atteinte_de_la_cible_YYYY)
GET {base}/performance-de-la-depense-rap-2025

# 3. Summary series (does it have a 2025 row yet?)
GET {base}/performance-atteinte-de-la-cible-generale-du-budget-de-l-etat-depuis-2007/records?limit=30&order_by=rap

# 4. Category counts for the denominator check (repeat per year / dataset)
GET {base}/performance-execution-et-atteinte-de-la-cible-du-budget-de-l-etat-jusqu-au-niveau-sous-indicateur/records
    ?select=atteinte_de_la_cible as k, count(*) as n&group_by=atteinte_de_la_cible&where=annee=2024
GET {base}/performance-de-la-depense-rap-2025/records
    ?select=atteinte_de_la_cible_2025 as k, count(*) as n&group_by=atteinte_de_la_cible_2025
```

---

## Part 6 — 2.4 context sentences (done)

**Status:** ✅ built 2026-11-14 (Session K in `runtime-discoveries.md`).
6.1–6.3 are the starting point as written on 2026-11-12; 6.4 records the
owner's answers and 6.5 what was built.

### 6.1 Goal (from Part 2)
One automatic sentence per KPI card: historical position ("plus haut depuis
1996"), position among the compared countries ("1er sur 7"), change over
10 years. The sentence must be generated by the processors, not hand-written.
Principle 2 applies: state a fact, never a verdict.

### 6.2 What exists
- **No new data:** 2.4 reads the outputs already produced. The France
  series is `france` (for `sustainability`, the deficit; for `outcomes`,
  `health.spend_pct_gdp`; for `tax_expenditure`, rows with
  `total_cost_eur_bn` and `projection`). Peers are `peers`
  (`peers.deficit` / `peers.debt` for `sustainability`, `pct_gdp.peers` for
  pensions' second chart). The €/hab series are `per_capita`.
- **The card:** `frontend/src/components/KpiCard.tsx` shows the title, the
  latest value, the YoY arrow, a sparkline, "données jusqu'à {year}" and the
  average badge, all from the adapter's `KpiView`. The detail page's headline
  is `components/StatCallout.tsx`.
- **The backend hook:** every processor builds a payload and calls
  `write_output`; the standard ones also call `build_latest(france)`. A
  helper beside it in `processors/__init__.py` that takes `france` and
  `peers` would cover the standard payloads in one place; the non-standard
  ones (`sustainability`, `outcomes`, `tax_expenditure`, `performance`,
  `monthly_execution`) need their own call.
- **Series and peers per KPI** (fixtures, 2026-11-12):

| KPI | France | Peers (first–last year) |
|-----|--------|-------------------------|
| overhead_rate | 1995–2025 | 6 OECD (DEU ESP GBR ITA NLD SWE) + `OECD_AVG`, 2007–2024 |
| sustainability (deficit) | 1995–2025 | 6 OECD + `OECD_AVG`, 2007–2024 |
| admin_overhead, friction_ratio, productive_spend, pension_investment | 1995–2024 | 5 Eurostat (DEU ITA ESP NLD SWE) 1995–2024 + `EU27_AVG` 2010–2024 |
| pensions | 1995–2024 | 5 Eurostat (DEU from 2000, ITA and SWE from 2001) + `EU27_AVG` 2010–2024 |
| debt_service | 1995–2025 | 5 Eurostat + `EU27_AVG`, 1995–2025 |
| tax_burden | 1965–2024 | 6 OECD + `OECD_REP`, 1965–2024 |
| public_employment | 2007–2023 | 6 OECD, 2007–2023, no average |
| wage_ratio | 1997–2025 | none |
| deficit_subsector | 1995–2025 | none |
| outcomes (health spending) | 1995–2024 | none |
| tax_expenditure | 1999–2026, 2025–2026 are GTED projections | none |
| performance | 2007–2024 (official series) | none |
| monthly_execution | current year, cumulative by month | none |

### 6.3 Pitfalls already visible
- **Latest years differ:** France ends in 2025 but its peers in 2024 for
  overhead_rate and sustainability. A peer comparison must use the latest
  year every compared country has, and say which year.
- **Count countries, never averages:** the 5 Eurostat peers plus France
  make "sur 6"; the 6 OECD peers plus France make "sur 7". `EU27_AVG`,
  `OECD_AVG` and `OECD_REP` are aggregates, never ranks. Peer coverage starts
  late for some (OECD GIP 2007, EU27 2010, pensions DEU/ITA/SWE 2000–01).
- **Negative values:** the deficit series is negative, so "plus haut" is
  ambiguous there. The wording must follow the sign, e.g. "déficit le plus
  faible depuis…".
- **Projections:** tax_expenditure's last two years are forecasts. Either
  exclude them from "depuis" sentences or say "prévision".
- **Non-comparable sets:** the indicator set behind `performance` changes
  every year (Part 5.6), so "le plus haut depuis 2007" would compare unlike
  sets. `monthly_execution` has no yearly history: at most a sentence from
  its `yoy` block.
- **Neutral polarity:** most KPIs are `neutral`. An ordinal rank ("1er")
  reads as a ranking of countries; "la valeur la plus élevée des 7 pays"
  states the same fact without a podium.
- **Rounding:** outputs are rounded to 2 decimals, so equal values can tie
  a "plus haut depuis" test.
- **Revisions:** a sentence can change when INSEE or Eurostat revise a past
  year (see 4.1). Generating it at each run handles this.

### 6.4 Decisions (owner, 2026-11-14)
1. **Notable first.** History when it is a record (series ≥ 10 years) or
   reaches back ≥ 5 years; else France at an extreme of the compared
   countries; else the 10-year change. A literal "highest since" is mostly
   trivial (overhead_rate 2025 was "the highest since 2024"), hence the
   thresholds.
2. **Extremes only**: "la plus élevée / basse des N pays comparés en Y",
   never an ordinal rank; no peer sentence for middle positions.
3. and 4. **Card + detail headline**, ratio view only (the €/hab view keeps
   its headline without a sentence).
5. Defaults stated to the owner: no sentence for performance (indicator set
   changes yearly) or monthly_execution (no yearly history);
   tax_expenditure computed on outturn years only.
6. **Facts in the backend, words in the frontend**: wording fixes ship with
   Cloudflare Pages, no VPS regeneration.

### 6.5 What was built
- `build_context(france, peers)` in `processors/__init__.py` →
  `context: {history?: {direction, since, record}, peers?: {year, position,
  of}, change_10y?: {from_year, change}}`, each fact present only when it
  passes the rules above. Peer countries are the ISO3 keys of `OECD_PEERS`
  (Eurostat peers are a subset), so no average is ever counted; the
  comparison year is the latest one France and every peer have. Ties count
  as reached (values are rounded to 2 decimals). Called by the 14
  yearly processors; sustainability on the deficit and its deficit peers,
  outcomes on health spending, tax_expenditure without projections.
- `fmtContext(facts, unit, balance?)` in `frontend/src/data/format.ts`
  picks the first fact and words it: "Plus haut niveau depuis 2013.",
  "Plus bas niveau depuis le début de la série (1995).", "Valeur la plus
  élevée des 7 pays comparés en 2024.", "−1,0 point en dix ans
  (2015–2025)." (Md€ or × for those units). Public balances (sustainability,
  deficit_subsector) are worded as deficits when negative: "Déficit le plus
  faible depuis 2019.", "Déficit plus élevé de 1,2 point qu’en 2015."
- `KpiView.context` (string) on the card (`kpi-card__context`, under the
  figure) and in `StatCallout`; Methodology page section "Phrases de
  contexte".

---

## Appendix — Reproducible sample queries (2026-10-26)

URL-encode query strings (quotes, spaces, accents) when running these with a
script; they are shown decoded for readability.

```text
# S1 Eurostat COFOG × transaction, France
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10a_exp?format=JSON&geo=FR&sector=S13&unit=MIO_EUR&na_item=D1&na_item=TE&cofog99=GF01&cofog99=GF1002&cofog99=TOTAL

# S2 Eurostat sub-sector balances
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10a_main?format=JSON&geo=FR&unit=MIO_EUR&na_item=B9&sector=S1311&sector=S1313&sector=S1314&sector=S13

# S3 Eurostat tax burden
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10a_taxag?format=JSON&geo=FR&geo=DE&sector=S13_S212&unit=PC_GDP&na_item=D2_D5_D91_D61_M_D995

# S4 Eurostat debt by holder
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10dd_ggd?format=JSON&geo=FR&sector=S13&na_item=GD&maturity=TOTAL&unit=PC_GDP&sector2=S2&sector2=S121&sector2=S1_S2

# S5 OECD tax-to-GDP
https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_REV_COMP_OECD@DF_RSOECD,/FRA+DEU+GBR+SWE+ITA+ESP+NLD+OECD_REP.TAX_REV.S13._T._T.PT_B1GQ.A?format=csv

# S6 OECD public employment
https://sdmx.oecd.org/public/rest/data/OECD.GOV.GIP,DSD_GOV@DF_GOV_EMPPS_REP_2025,/A.FRA+DEU+ITA+ESP+NLD+SWE+GBR+OECD......?format=csvfilewithlabels

# S7 Performance (target attainment since 2007)
https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/performance-atteinte-de-la-cible-generale-du-budget-de-l-etat-depuis-2007/records?limit=30

# S9 OFGL filtered export (4 aggregates, all communes, 2024)
https://data.ofgl.fr/api/explore/v2.1/catalog/datasets/ofgl-base-communes-consolidee/exports/csv?select=exer,insee,com_name,ptot,agregat,montant,euros_par_habitant&where=exer=date'2024' and agregat in ("Encours de dette","Frais de personnel","Dépenses d'équipement","Epargne brute")

# S10 DECP consolidated (resource list)
https://www.data.gouv.fr/api/1/datasets/608c055b35eb4e6ee20eb325/

# S11 OpenFisca
POST https://api.fr.openfisca.org/latest/calculate
{"individus":{"p1":{"salaire_de_base":{"2025":36000},"date_naissance":{"ETERNITY":"1990-01-01"}}},
 "foyers_fiscaux":{"f1":{"declarants":["p1"],"impot_revenu_restant_a_payer":{"2025":null}}},
 "menages":{"m1":{"personne_de_reference":["p1"]}},"familles":{"fa1":{"parents":["p1"]}}}
```
