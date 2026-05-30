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
| `cpi` | **None technical** — it's a utility, not a KPI; nothing has asked for constant-euro framing. `cpi` is monthly and `annual_values()` rejects monthly, so a monthly→annual step is also needed. | Build when a KPI wants real-terms values (Session D candidate #4). |
| France Travail (`france_travail_allocataires`) | **Real data gap** — gives an indemnisés *count* (a level), not benefit *spend*, so no efficiency ratio is possible. | Acquire a paired spend series: COFOG GF10.5 unemployment sub-function (EUR) or a France-Travail expenditure/montant file → € per recipient (Session D candidate #3). |
| `budget_plrg` raw | PLRG mission/program tabular export **discontinued, PDF-only**. | By-design `skipped`; no KPI consumes it. Revisit only if a PLRG-based KPI is wanted (would need PDF parsing). |

### B. Peer-benchmarking feasibility per KPI (PRD §5.1 wants peers on all)

Mostly **not feasible** beyond the four already done — the OECD raw lacks the
needed series for several, and three KPIs are France-only by construction.

| KPI | Peer status | Reason |
|-----|-------------|--------|
| overhead, productive, sustainability (deficit+debt) | ✅ DONE (Sessions A/B) | OECD GIP raw has the series (peer floor 2007) |
| friction | ✅ DONE but **trend-only** | France denominator is revenue; peer denominator is total expenditure — not level-comparable |
| pension/investment | ❌ BLOCKED | OECD fiscal raw has **no P51 / gross fixed capital formation**; PRD §5.5 names no peer source |
| outcomes — education | ❌ BLOCKED | PISA not in OECD SDMX (see C) |
| outcomes — health | ⚠️ FEASIBLE, not built | OECD life-expectancy peers exist; peers deferred (shipped France-only dual series) |
| tax_expenditure | ⚠️ FEASIBLE, not built | GTED RevenueForgone carries all countries; PRD names no peer source, so deferred |
| debt_service | ⚠️ UNCONFIRMED | OECD GE transactions expose D4 (property income), not isolated D41 interest — peer source not verified |
| wage_ratio | ❌ no aligned source | Urssaf is a France-only private wage bill; no cross-country equivalent on the same basis. France-only |
| monthly_execution | N/A | French budget-execution data; France-only by nature |

### C. Tried but technically blocked upstream

| Goal | Blocker | Status / workaround | Revisit when |
|------|---------|---------------------|--------------|
| `wage_bill_central` (S1311 central-state wage bill, PRD §3.1) | CNT-2020-CSI has no central-state breakdown past 2020 | **Deleted** (Session 8); no KPI used it | A base-2020 INSEE family with an S1311 breakdown appears |
| Education / PISA half of §5.9 outcomes | **PISA not in OECD's SDMX API** | Outcomes shipped **health-only** (Session 10) | Source PISA from the OECD PISA explorer bulk download or a data.gouv mirror (non-SDMX), interpolate triennially |
| Official tax-expenditure tabular (Voies et Moyens *Tome II*) | **PDF-only**; no costed, multi-year, full-list tabular source | Used **GTED** via Zenodo (third-party academic compilation, CC-BY; Sessions C/C2) — *not* a primary statistical feed | Bercy publishes a tabular Tome II, or if GTED definitions prove insufficient (then PDF-parse, Session 9 option 2) |
| Pension/investment peers | no OECD GFCF (P51) in the fiscal raw | deferred (see B) | An OECD/Eurostat GFCF-by-country series is wired in |
| §5.9 "indexed to OECD average = 100" | peers deferred | shipped as dual France-only time series | Outcomes peers are built (see B) |
| Full historical peer depth (1995) | OECD GIP peers start **2007**; OECD COFOG caps at **2023**; INSEE functional COFOG frozen at base-2020 (no FONCTION dim post-2020) | documented upstream limits; INSEE+OECD COFOG **stitched** at 2020 seam (Session 8) | OECD extends GIP history/recency, or INSEE ships a base-2020 functional series |
