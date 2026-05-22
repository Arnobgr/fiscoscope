# fisc-o-scope Frontend — Design Spec

**Date:** 2026-05-22
**Status:** Approved (brainstorm) — pending spec review before plan
**Phase:** Project Phase 2 (frontend). Backend + API are built; deployment is covered by `docs/superpowers/plans/2026-05-22-vps-deployment.md`.

---

## 1. Goal

A public, French-language web dashboard that lets a general French audience see how the productivity and efficiency of French public administration has evolved (1995–present), KPI by KPI, with optional comparison to the OECD average. It reads the pre-computed JSON served by the FastAPI backend (`/api/...`). Editorial, trustworthy, and visually distinctive — Anthropic's design language blended with the French tricolore, deliberately avoiding generic "AI dashboard" aesthetics.

## 2. Audience, language, tone

- **Audience:** French general public (taxpayers / citizens), not specialists.
- **Language:** French throughout (UI chrome + KPI labels + explainers + number/date formatting).
- **Tone:** editorial "explainer" — each KPI gets a short plain-French description of what it measures and why it matters. Assumes no fiscal expertise.

## 3. Aesthetic / design language

> Implementation MUST use the **`frontend-design`** skill to drive the visual craft. The tokens below are the design constraints; the skill produces the finished components.

- **Canvas / chrome (Anthropic):** warm ivory/cream background (≈ `#F4F1EA`), dark slate ink (≈ `#28261F`), generous whitespace, calm editorial rhythm. No gradients, glassmorphism, neon, or purple-on-dark.
- **Typography:** serif **display** headings (e.g. **Fraunces**) + clean sans **body** (e.g. **Inter**), both free (Google Fonts, self-hosted for performance/privacy).
- **Tricolore — used for *data*, not chrome:**
  - **France series → bleu `#0055A4`** (the protagonist line everywhere).
  - **rouge `#EF4135` → reserved for *meaningful* negatives** (deficits, and "bad-direction" movement like rising overhead/debt). Not decorative.
  - **white** = cards/surfaces over the cream canvas.
- **Brand/interaction accent (Anthropic):** coral/clay `#CC785C` for links, active nav, hover/focus states, sparkline highlights — the connective tissue that signals the Anthropic lineage without competing with the bleu data.
- **Accessibility of color:** color is never the sole signal — YoY uses an arrow (▲/▼) *and* color; the OECD-average line differs by **dash style + label**, not just hue. Target WCAG AA contrast on the cream canvas. Respect `prefers-reduced-motion`.

## 4. Information architecture (routed SPA)

Three routes:

### `/` — Overview
- **Header:** site title, French tagline, and a **"Dernière mise à jour : {date}"** badge sourced from `meta.json` (`last_run`).
- **Intro:** one short paragraph framing the project.
- **KPI cards in 3 themed groups** (see §6 for the mapping):
  1. **Efficacité administrative**
  2. **Soutenabilité des finances publiques**
  3. **Dépenses & résultats**
- Each card → `KpiCard` (see §7).

### `/kpi/:id` — Detail
- Breadcrumb back to overview.
- KPI title + **plain-French explainer** paragraph.
- **`StatCallout`**: latest value (French-formatted) + YoY change (arrow + color).
- **`TimeSeriesChart`**: France line by default; a small **toggle** adds the OECD-average line *where that KPI has OECD data* (otherwise no toggle).
- **`MethodologyDisclosure`** (collapsible): the KPI's `source` + `methodology`, plus data caveats (see §8).

### `/methodologie` — About / Methodology
Small page: what the project is, where the data comes from (INSEE, OECD GIP, GTED for tax expenditure with its CC-BY attribution), update cadence, and limitations. Supports public trust/credibility.

## 5. Tech stack

- **Vite + React + TypeScript**, **Recharts** for charts, **React Router** for the 3 routes.
- **Hand-crafted CSS with design tokens** (CSS custom properties; optional light utility layer). **No dashboard component kit** (Tremor/shadcn-charts) — those impose a recognizable templated look that conflicts with the no-slop requirement.
- Native `fetch` + a small in-memory cache/hook for data (no heavy data-fetching dependency; the dataset is ~11 small JSON files).
- Self-hosted fonts (Fraunces, Inter).

## 6. KPI registry & theme grouping

A central **registry** (`kpiRegistry.ts`) is the single source of per-KPI presentation metadata: theme, French label, French explainer, value formatting (unit + decimals), and which JSON adapter to use. The backend JSON carries English `description`/`methodology`; **French label + explainer are authored in the registry** (the user will refine wording).

| `kpi_id` | French label (draft) | Theme | OECD-avg available? |
|----------|----------------------|-------|---------------------|
| `kpi_overhead_rate` | Coût administratif (frais de personnel) | Efficacité administrative | Yes |
| `kpi_friction_ratio` | Ratio de friction | Efficacité administrative | Yes (trend-only) |
| `kpi_productive_spend` | Part des dépenses productives | Efficacité administrative | Yes |
| `kpi_wage_ratio` | Masse salariale public / privé | Efficacité administrative | No (France-only) |
| `kpi_sustainability` | Déficit public & dette | Soutenabilité des finances publiques | Yes (deficit + debt) |
| `kpi_debt_service` | Charge de la dette | Soutenabilité des finances publiques | No |
| `kpi_pension_investment` | Retraites vs investissement | Soutenabilité des finances publiques | No |
| `kpi_outcomes` | Dépenses de santé vs espérance de vie | Dépenses & résultats | No (dual series) |
| `kpi_tax_expenditure` | Dépenses fiscales (niches) | Dépenses & résultats | No |
| `kpi_monthly_execution` | Exécution budgétaire mensuelle | Dépenses & résultats | No (monthly x-axis) |

(Draft labels are starting points; final French wording is the user's to refine.)

## 7. Components

- **`AppShell`** — header (title, tagline, last-updated badge), `<main>`, footer (data attributions: INSEE, OECD, GTED CC-BY).
- **`ThemeSection`** — a titled group of `KpiCard`s on the overview.
- **`KpiCard`** — KPI label, latest value (formatted), YoY (▲/▼ + color), a **`Sparkline`** (France series), and an optional **"vs moyenne OCDE"** badge where applicable. Links to `/kpi/:id`.
- **`Sparkline`** — tiny France-only line (Recharts or inline SVG).
- **`KpiDetail`** (route view) — composes the explainer, `StatCallout`, `TimeSeriesChart`, `MethodologyDisclosure`.
- **`TimeSeriesChart`** — Recharts line chart from a normalized series model; France (bleu) always; OECD-average (dashed, neutral) behind a toggle when present; projection-aware (dashed segment); methodology-break marker.
- **`StatCallout`** — large latest value + YoY.
- **`MethodologyDisclosure`** — collapsible source/methodology + caveats.

## 8. Data layer, shape normalization & honesty handling

### 8.1 Endpoints (from the FastAPI backend)
- `GET /api/meta` → `last_run` (→ last-updated badge), pipeline metadata.
- `GET /api/kpis` → list of available KPI ids.
- `GET /api/kpi/{id}` → that KPI's JSON.

**Fetch strategy:** on overview load, fetch `meta` + all KPI files **in parallel**, cache in memory; detail pages reuse the cache. (~11 small files.)

### 8.2 Per-KPI JSON shapes (the registry maps each to a common view model)
The backend JSON is **not uniform** — a per-KPI **adapter** normalizes each into a common `{ series: {year,value}[], unit, latest, comparison?: {year,value}[], secondary?: {...}, notes }` model:
- **Standard ratio KPIs** (`overhead`, `friction`, `productive`, `debt_service`, `pension_investment`, `wage_ratio`): top-level `france: [{year,value}]`, `latest: {year,value,yoy_change}`, optional `peers` (use **`OECD_AVG`** only; ignore the 6 individual countries).
- **`sustainability`**: `france` = deficit (% GDP), **plus** `debt: {france: [...]}` (debt % GDP), and `peers: {deficit:{OECD_AVG}, debt:{OECD_AVG}}`. Detail view shows deficit as primary with debt as a secondary view/series; OECD-avg toggle applies to whichever is shown.
- **`outcomes`**: `health: {spend_pct_gdp: [...], life_expectancy_years: [...]}`, `education: null`, no peers. **Dual-axis** chart: health spend (% GDP) and life expectancy (years) over time. (`education` is a documented gap — show nothing for it.)
- **`tax_expenditure`**: `france: [{year, total_cost_eur_bn, count, projection, ratio_to_revenue_pct, yoy_change_pct}]`, no peers. Plot `total_cost_eur_bn` (or `ratio_to_revenue_pct`); rows with `projection: true` (2024–25) render **dashed + "prévision"**.
- **`monthly_execution`**: **monthly** cadence (x-axis = months, not years); `last_month` at payload root. Render on a month axis, distinct from the annual KPIs.

### 8.3 Honesty / credibility details (important for a public audience)
- **Projections** (`tax_expenditure` 2024–25): dashed segment, labelled *"prévision"* in legend/tooltip.
- **2020 COFOG methodology break:** KPIs whose datapoints carry a `source` tag that switches `INSEE → OECD` around 2020 (overhead/friction/productive/pension/outcomes-health) get a subtle marker + a one-line note ("changement de base méthodologique 2020").
- **OECD-average start year:** where the comparison begins in 2007, note "comparaison OCDE à partir de 2007".
- **France-only KPIs:** simply omit the comparison toggle (no empty UI).

## 9. Formatting, i18n, responsiveness

- **French locale** via `Intl.NumberFormat('fr-FR')`: percentages `5,79 %`, large numbers with narrow no-break-space thousands separators, € where relevant. Dates via `Intl.DateTimeFormat('fr-FR')` → `21 mai 2026`.
- Copy centralized (a `strings.ts` / the registry) even though single-language, for maintainability.
- **Mobile-first responsive**: cards reflow to 1 column on small screens; charts resize; touch-friendly tooltips.

## 10. Testing

- **Vitest + React Testing Library** (component/unit):
  - `KpiCard` renders the latest value with French formatting and the correct YoY sign + color/arrow.
  - registry adapters normalize each JSON variant correctly (standard, sustainability+debt, outcomes dual-series, tax-expenditure projection, monthly).
  - `TimeSeriesChart` maps series → points; OECD toggle shows/hides the comparison; projection rows render as the dashed variant.
  - last-updated badge reads `meta.last_run`.
- **Playwright smoke (1):** overview loads → click a card → detail renders its chart.
- Tests run against **local fixtures** (copies of `backend/data/output/*.json`), so no live API needed (see §12). TDD via the implementation plan.

## 11. Deployment (ties to the deployment plan)

- **Cloudflare Pages**, build `vite build` → output `frontend/dist`.
- **`VITE_API_BASE`** env (Pages build setting) = the backend's HTTPS origin (e.g. `https://<ip>.sslip.io`). The frontend calls `${VITE_API_BASE}/api/...`.
- The Pages production URL must match the backend's **`ALLOWED_ORIGINS`** (set in the deployment plan's `.env`) so CORS permits the calls.

## 12. Parallel execution with deployment

The frontend depends only on the JSON *shape*, not a live server: dev and tests use **local fixtures** (committed copies of the current `data/output/*.json` under `frontend/fixtures/` or a dev proxy). A `VITE_API_BASE` pointing at fixtures (or a Vite dev proxy) lets the entire frontend be built and tested **in parallel** with the user executing the VPS deployment. Final wiring to the live `sslip.io` API is a config flip at the end.

## 13. Scope (v1) and YAGNI

- **In:** all 10 KPIs; overview + detail + methodology pages; France line + OECD-average toggle; sparklines; YoY; French formatting; projection/break honesty markers; responsive; a11y AA; component + smoke tests.
- **Out (deferred):** the 6 individual peer countries (OECD-average only, per decision); per-country spaghetti; bilingual/i18n framework (French only); dark mode; data-download/export; URL-shareable chart state beyond the route; PISA/education half of outcomes (backend gap); user accounts/interactivity beyond hover + the OECD toggle.

## 14. Open items the user will refine

- Final **French copy**: KPI labels (draft in §6) and the one-paragraph explainers per KPI; the overview intro; the methodology page text.
- Exact font choices (Fraunces/Inter are defaults; swappable).
- Theme group names (draft in §4/§6).
