# Roadmap — Fiscoscope for citizens: transparency & accountability

Written 2026-10-26. This is the forward plan; `known-gaps.md` stays the reference
for what is blocked and `runtime-discoveries.md` for why existing KPIs are built
the way they are.

**Start here (new session).** Read this file top to bottom, then
`known-gaps.md`. Pick the next unchecked item from Part 3; before writing code,
re-run that source's query from the appendix to confirm it still answers
(dataset IDs and columns drift — see Part 4). Part 4 has everything needed about
repo conventions; no other context is required. Figures quoted below are as of
2026-10-26 and will have moved.

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
| 1.5 | **Tax burden** (prélèvements obligatoires) vs peers + OECD avg (`OECD_REP` is a true OECD aggregate — the only series that may be labelled "Moyenne OCDE"; give it its own key, not `OECD_AVG`), 1965–2024 | S5 (or S3) | New KPI, one definition, named on chart ⏳ code written 2026-11-08 (fetcher, processor, parser tests); not yet in the registry — awaiting re-verification on the VPS: `sdmx.oecd.org` served a Cloudflare challenge to the dev machine |
| 1.6 | **Who holds the debt**: non-residents / Banque de France / domestic, 2020–2025 | S4 | Detail panel on the debt KPI ✅ 2026-11-08 — `debt_holders` block in `kpi_sustainability.json`, France only |
| 1.7 | **Public employment** share vs peers, 2007–2023 | S6 | New KPI under Efficacité ⏳ code written 2026-11-08 (fetcher, processor, parser tests); not yet in the registry — awaiting re-verification on the VPS: `sdmx.oecd.org` served a Cloudflare challenge to the dev machine |
| 1.8 | Peers for `debt_service` (interest payable, % GDP) | S2 `D41PAY` | Closes known-gaps B "debt_service ⚠️ unconfirmed" ✅ 2026-11-08 — KPI kept as interest / revenue: peers = D41PAY / TR |
| 1.9 | Decide fate of the INSEE+OECD COFOG stitch once Eurostat is wired (Eurostat runs 1995–2024 on one basis) | S1 | `runtime-discoveries.md` entry recording the decision ✅ 2026-11-08 — stitch retired: all COFOG KPIs on Eurostat for France and peers (Session H) |

### Phase 2 — Citizen framing (M)

| # | Item | Done when |
|---|------|-----------|
| 2.1 | **€ per inhabitant, constant euros** on every euro-denominated KPI: wire the orphaned `cpi` (monthly → annual average) and an INSEE population series (resolve via the idBank resolver) | Toggle "% du PIB / € par habitant (euros 2025)" on detail pages |
| 2.2 | **"Où vont 1 000 € de dépense publique"** — COFOG level-1/2 breakdown of 1,000 € (S1), with year selector and peer comparison | New page; numbers reconcile to S1 totals |
| 2.3 | **"Mes impôts"** — 6–10 archetype households (single minimum wage, median couple with 2 children, retiree, high earner…) computed with pinned OpenFisca in the pipeline; each household's direct taxes split by COFOG shares | Static JSON, no runtime call to the public API; archetypes and assumptions documented |
| 2.4 | **Data-driven context sentences** per KPI: historical rank ("plus haut depuis 1996"), peer rank ("1er sur 7"), 10-year change — generated by processors, not hand-written | Every KPI card shows one auto sentence |
| 2.5 | **Interest vs ministries**: debt interest (S2 `D41PAY`, S8 planned) next to the voted credits of the largest missions (S15) | Chart with source per bar; 2026 marked "prévision du gouvernement" |

### Phase 3 — Accountability: promises vs results (M–L)

| # | Item | Data | Done when |
|---|------|------|-----------|
| 3.1 | **Tableau de bord de la performance de l'État**: share of targets met per year since 2007 (incl. "non renseigné"); drill-down by mission → programme → indicator with target vs result; filter "objectifs manqués", "non renseignés" | S7 | Fetcher discovers yearly vintages via catalog search; per-vintage column normalisation tested; consistent denominator documented |
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
   the honest overhead KPI.~~ ✅ 2026-11-08 with the rest of Phase 1, except 1.5
   and 1.7 (OECD), which await re-verification on the VPS.
3. **3.1** (performance scorecard) — highest accountability value per effort;
   data is clean and official.
4. **2.1, 2.4** — per-capita/constant euros and auto context sentences raise
   readability of every existing KPI.
5. **Phase 4** — largest new audience (local relevance).
6. **3.2, 5.1**, then the rest of Phases 2, 5 and 6.

After each item: tick it in this file (append "✅ YYYY-MM-DD" to its "Done
when" cell), update `known-gaps.md` (remove closed gaps, add new ones) and
append a session entry to `runtime-discoveries.md`.

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
- **Peers naming:** existing payloads key peers by ISO3 (`DEU`, `GBR`…) plus
  `OECD_AVG`. **`OECD_AVG` is a misnomer:** it is the unweighted mean of the 6
  peers (`peer_series` in `processors/__init__.py`), shown on screen as
  "Moyenne des 6 pays" — never label it as an OECD average. Eurostat uses ISO2
  (`FR`, `DE`, `EL` for Greece) and `EU27_2020`: map to ISO3 and introduce
  `EU27_AVG` (a true aggregate). Eurostat has **no UK**, so a peer mean computed
  from Eurostat covers 5 countries — don't store it under `OECD_AVG` or reuse
  the "6 pays" label. Frontend today: `adapters.ts` reads `OECD_AVG` into the
  single `KpiView.comparison` slot and the 6 countries via its `PEERS` list
  (order + French labels); `TimeSeriesChart.tsx` colours them via
  `PEER_COLORS`. The first KPI with a second average (EU27, `OECD_REP`) must
  turn `comparison` into a list of averages, each with its own label.
- **Tests:** backend `pytest` in `backend/tests/` (only `test_api.py` today —
  add tests for new decoders/parsers with small fixture files); frontend
  `npm test` (vitest) in `frontend/`.
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
   `types.ts`. New page → route in `frontend/src/App.tsx`.

### 4.6 Shipping
Production runs on the VPS: a cron/systemd timer runs `run_pipeline.py`, and
`backend/api.py` serves `backend/data/output/*.json` read fresh per request
(`https://fisc.159-69-91-118.sslip.io`). A new KPI is live once the backend code
is deployed on the VPS and the pipeline (or that step) has run, **and** the
frontend is redeployed to Cloudflare Pages (`https://fiscoscope.pages.dev`).
New sources may need their own timer: EDP notifications land in April and
October, the RAP around spring, OFGL local accounts mid-year — check actual
release dates per source before scheduling.

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
