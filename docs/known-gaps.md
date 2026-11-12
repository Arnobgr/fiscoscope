# Known gaps & blocked attempts — Fiscoscope

Moved out of `CLAUDE.md` (2026-05-22); consolidated 2026-05-21 from the
session-by-session notes now in `runtime-discoveries.md`. This is the single
"we wanted to do this but couldn't (yet)" reference — consulted when picking up
related work, not needed at every session start. **Before re-attempting any item
here, confirm its blocker has changed** — otherwise it will fail the same way.

All 8 PRD KPIs (§5.2–5.9) plus 2 extra (wage ratio, debt service) are built and
`ok`; the items below are the asterisks on "complete". Backend code is
feature-complete; deployment (first live run of the FastAPI app) and the frontend
(Phase 2) are the remaining *build* work — not "blocked", just not started.

---

### A. Orphaned inputs (fetched/resolved, no processor consumes them)

| Input | Blocker | Unblock path |
|-------|---------|--------------|
| `social_benefits` (D62_S13) | **None** — just unwired. Resolved for PRD §5.3's original friction formula; the shipped friction diverged to admin-COFOG / revenue. | Design choice: wire into a redesigned friction or a new transfers KPI. No new data needed. |
| France Travail (`france_travail_allocataires`) | **Real data gap** — gives an indemnisés *count* (a level), not benefit *spend*, so no efficiency ratio is possible. | Acquire a paired spend series: COFOG GF10.5 unemployment sub-function (EUR) or a France-Travail expenditure/montant file → € per recipient (Session D candidate #3). |
| `budget_plrg` raw | PLRG mission/program tabular export **discontinued, PDF-only**. | By-design `skipped`; no KPI consumes it. Revisit only if a PLRG-based KPI is wanted (would need PDF parsing). |

### B. Peer-benchmarking feasibility per KPI (PRD §5.1 wants peers on all)

Mostly **not feasible** beyond the four already done — the OECD raw lacks the
needed series for several, and three KPIs are France-only by construction.

| KPI | Peer status | Reason |
|-----|-------------|--------|
| overhead_rate, sustainability (deficit+debt) | ✅ DONE (Sessions A/B; each country shown on charts since roadmap 0.4) | OECD GIP raw has the series (peer floor 2007). The `OECD_AVG` key is the unweighted mean of the **6 peers**, not an OECD aggregate — shown as "Moyenne des 6 pays" since 2026-11-04 |
| admin_overhead, productive, friction, pension/investment, pensions | ✅ DONE (Session H, roadmap 1.2/1.3/1.9) | Eurostat `gov_10a_exp` (+ `gov_10a_main` TR for friction) for France and peers alike, from 1995 (DE/IT/SE old-age from 2000–01), with the true EU27 aggregate (`EU27_AVG`, COFOG from 2010). **No UK** on these charts — Eurostat dropped it after Brexit. Friction peers are back: the old blocker (revenue vs expenditure denominators) is gone, Eurostat TR is the same aggregate for every country |
| outcomes — education | ❌ BLOCKED | PISA not in OECD SDMX (see C) |
| outcomes — health | ⚠️ FEASIBLE, not built | OECD life-expectancy peers exist; peers deferred (shipped France-only dual series) |
| tax_expenditure | ⚠️ FEASIBLE, not built | GTED RevenueForgone carries all countries; PRD names no peer source, so deferred |
| debt_service | ✅ DONE (Session H, roadmap 1.8) | Peers = Eurostat `gov_10a_main` D41PAY / TR (+ EU27, no UK). France stays on INSEE quarterly accounts; its Eurostat equivalent differs by ≤ 0.06 pt over 1995–2025 |
| deficit_subsector | N/A | France's own sub-sector split (Eurostat S1311/S1313/S1314); peers not shown — sub-sector structures (federal states, social-security perimeter) are not comparable |
| wage_ratio | ❌ no aligned source | Urssaf is a France-only private wage bill; no cross-country equivalent on the same basis. France-only |
| monthly_execution | N/A | French budget-execution data; France-only by nature |
| performance | N/A | The State's own targets and results; France-only by nature |

### C. Tried but technically blocked upstream

| Goal | Blocker | Status / workaround | Revisit when |
|------|---------|---------------------|--------------|
| `wage_bill_central` (S1311 central-state wage bill, PRD §3.1) | CNT-2020-CSI has no central-state breakdown past 2020 | **Deleted** (Session 8); no KPI used it | A base-2020 INSEE family with an S1311 breakdown appears |
| Education / PISA half of §5.9 outcomes | **PISA not in OECD's SDMX API** | Outcomes shipped **health-only** (Session 10) | Source PISA from the OECD PISA explorer bulk download or a data.gouv mirror (non-SDMX), interpolate triennially |
| Official tax-expenditure tabular (Voies et Moyens *Tome II*) | **PDF-only**; no costed, multi-year, full-list tabular source | Used **GTED** via Zenodo (third-party academic compilation, CC-BY; Sessions C/C2) — *not* a primary statistical feed | Bercy publishes a tabular Tome II, or if GTED definitions prove insufficient (then PDF-parse, Session 9 option 2) |
| §5.9 "indexed to OECD average = 100" | peers deferred | shipped as dual France-only time series | Outcomes peers are built (see B) |
| Performance headline for the latest RAP year (roadmap 3.1) | The official summary series stopped at 2024 when checked (2026-11-09) although the RAP 2025 detail is out | Headline shows the **official series only** (owner's decision: no Fiscoscope-computed point); the 2025 detail is on the drill-down page. A recount under the same rule gives 35.3 % met for 2025 | The ministry adds the year to `performance-atteinte-de-la-cible-generale-…-depuis-2007` (picked up automatically by the annual run) |
| Official definition of "amélioration" (performance indicators) | Not given on the dataset pages | Copy uses the ministry's wording only ("cible non atteinte, en amélioration"). Data check: 141 of 174 numerically comparable RAP 2025 rows are "missed, better than the previous year" | The ministry documents the categories |
| Deduplicating mission vs programme performance indicators | About half of the Mission rows repeat a Programme indicator, but the link field (`(Indicateur du Pxxx)`) and the labels don't match reliably (22 tagged rows have no label match) | Drill-down shows both levels and counts both, as the official series does; the page says so | A stable indicator id linking the two levels |
| Full historical peer depth (1995) | OECD GIP peers start **2007** | **Resolved for COFOG KPIs** (Session H): Eurostat runs 1995–2024 on one basis, the INSEE+OECD stitch is retired. Still 2007+ for the OECD-sourced peers of overhead_rate and sustainability | Move those to Eurostat too (loses the UK), or OECD extends GIP history |
