# fiscoscope Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Task 14 additionally REQUIRES the `frontend-design` skill** for the visual layer.

**Goal:** A French-language, public-facing dashboard (Vite + React + TS + Recharts) that reads the backend's KPI JSON and presents an overview grid + per-KPI detail pages, with an Anthropic-editorial × French-tricolore aesthetic.

**Architecture:** A routed SPA. A pure **data core** (types → French formatters → per-KPI **adapters** that normalize each JSON variant into one common `KpiView` model → a **registry** of French presentation metadata → a fetch/cache layer) is fully TDD'd. UI components consume only `KpiView`, so they're agnostic to per-KPI JSON quirks. Visual styling is applied last via the `frontend-design` skill against stable DOM/behaviour contracts. Dev + tests run on **bundled fixtures** (copies of `backend/data/output/*.json`) so the whole build proceeds in parallel with VPS deployment; production fetches the live API.

**Tech stack:** Vite, React 19, TypeScript, React Router, Recharts, Vitest + React Testing Library, Playwright (1 smoke), self-hosted Fraunces + Inter. No dashboard component kit.

**Spec:** `docs/superpowers/specs/2026-05-22-frontend-design.md` (read it; this plan implements it).

**Conventions used throughout:**
- Work in `frontend/`. Run all commands from `frontend/` unless noted.
- Branch: `dev` (current). Commit after each task. End commit bodies with:
  `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`
- **KPI identity:** the API/file id keeps the `kpi_` prefix (e.g. `kpi_overhead_rate`); the route **slug** drops it (e.g. `overhead_rate`). The registry holds both.

---

## Pinned package versions

All npm packages are **hard-pinned to exact versions** — no `^` or `~` ranges anywhere.
Every version below was published at least 3 weeks before 2026-05-22 to guard against supply-chain attacks.
Use `--save-exact` for any package added later, or rely on `.npmrc` (`save-exact=true`) created in Task 1.

| Package | Pinned version | Published |
|---------|---------------|-----------|
| create-vite (scaffold only) | 9.0.6 | 2026-04-23 |
| vite | 8.0.10 | 2026-04-23 |
| react | 19.2.5 | 2026-04-08 |
| react-dom | 19.2.5 | 2026-04-08 |
| typescript | 6.0.2 | 2026-03-23 |
| @vitejs/plugin-react | 6.0.1 | 2026-03-13 |
| react-router-dom | 7.14.2 | 2026-04-21 |
| recharts | 3.8.0 | 2026-03-06 |
| vitest | 4.1.5 | 2026-04-21 |
| @testing-library/react | 16.3.2 | 2026-01-19 |
| @testing-library/jest-dom | 6.9.1 | 2025-10-01 |
| @testing-library/user-event | 14.6.1 | 2025-01-21 |
| jsdom | 29.1.0 | 2026-04-27 |
| @playwright/test | 1.59.1 | 2026-04-01 |

---

## File map (all under `frontend/`)

| File | Responsibility |
|------|----------------|
| `package.json`, `vite.config.ts`, `tsconfig*.json`, `vitest.setup.ts`, `playwright.config.ts`, `index.html` | Project config |
| `src/fixtures/*.json` | Copies of `backend/data/output/*.json` for dev + tests |
| `src/data/types.ts` | Raw JSON types (per variant) + normalized `KpiView` model |
| `src/data/format.ts` | French number/percent/€/date formatters |
| `src/data/adapters.ts` | Per-KPI `raw → KpiView` normalizers |
| `src/data/registry.ts` | slug ↔ apiId, theme, French label + explainer, unit, adapter |
| `src/data/api.ts` | `getMeta()` / `getKpi(apiId)` (fixtures in dev/test, fetch in prod) + in-memory cache |
| `src/data/useData.ts` | React hooks wrapping the api layer |
| `src/components/*` | `AppShell`, `Sparkline`, `KpiCard`, `TimeSeriesChart`, `StatCallout`, `MethodologyDisclosure` |
| `src/pages/*` | `Overview`, `KpiDetail`, `Methodology` |
| `src/styles/*` | Design tokens + global CSS (filled by Task 14) |
| `src/main.tsx`, `src/App.tsx` | Bootstrap + routes |
| `e2e/smoke.spec.ts` | Playwright smoke test |

---

## Task 1: Scaffold the project

**Files:** create `frontend/` project files; copy fixtures.

- [ ] **Step 1: Create the Vite React-TS app**

```bash
cd /home/arnobgr/french-efficiency-dashboard
npm create vite@9.0.6 frontend -- --template react-ts
cd frontend
# Enforce exact pins for all future installs in this project:
printf "save-exact=true\n" > .npmrc
# Install all packages at hard-pinned, supply-chain-safe versions (see "Pinned package versions" table above):
npm install --save-exact react@19.2.5 react-dom@19.2.5 react-router-dom@7.14.2 recharts@3.8.0
npm install -D --save-exact vite@8.0.10 @vitejs/plugin-react@6.0.1 typescript@6.0.2 vitest@4.1.5 @testing-library/react@16.3.2 @testing-library/jest-dom@6.9.1 @testing-library/user-event@14.6.1 jsdom@29.1.0 @playwright/test@1.59.1
```

- [ ] **Step 2: Copy the backend output as fixtures**

```bash
mkdir -p src/fixtures
cp ../backend/data/output/*.json src/fixtures/
ls src/fixtures/   # expect meta.json + 10 kpi_*.json
```

- [ ] **Step 3: Configure Vitest** — replace `vite.config.ts` with:

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
    css: false,
  },
});
```

Create `vitest.setup.ts`:

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 4: Add test/build scripts** — in `package.json` set `"scripts"` to include:

```json
{
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest",
  "e2e": "playwright test"
}
```

- [ ] **Step 5: Add a smoke unit test to prove the toolchain runs**

Create `src/smoke.test.ts`:

```ts
import { describe, it, expect } from "vitest";

describe("toolchain", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 6: Verify**

Run: `npm test`
Expected: 1 passed.
Run: `npm run build`
Expected: type-checks and builds to `dist/` with no errors.

- [ ] **Step 7: Commit**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git add frontend
git commit -m "feat(frontend): scaffold Vite + React + TS app with fixtures"
```

---

## Task 2: Data types

**Files:** create `src/data/types.ts`.

- [ ] **Step 1: Write the raw + view-model types** (no test — types only; verified by `tsc` in later tasks)

Create `src/data/types.ts`:

```ts
// ---- Raw JSON (as served by the backend) -------------------------------
export interface RawPoint { year: number; value: number; source?: string }
export interface StdSeriesKpi {            // overhead, friction, productive, debt_service, pension_investment, wage_ratio
  kpi_id: string; kpi_name: string; description: string; unit: string;
  source: string; methodology: string; last_updated: string;
  france: RawPoint[];
  peers?: Record<string, RawPoint[]>;      // may include OECD_AVG + 6 countries; we use OECD_AVG only
  latest?: { year: number; value: number; yoy_change?: number };
}
export interface SustainabilityKpi extends StdSeriesKpi {
  debt: { france: RawPoint[] };
  peers?: { deficit?: Record<string, RawPoint[]>; debt?: Record<string, RawPoint[]> } & Record<string, never>;
}
export interface OutcomesKpi {
  kpi_id: string; kpi_name: string; description: string; unit: string;
  source: string; methodology: string; last_updated: string;
  health: { spend_pct_gdp: RawPoint[]; life_expectancy_years: RawPoint[] };
  education: null; peers: Record<string, never>;
  latest?: Record<string, unknown>;
}
export interface TaxExpRow {
  year: number; total_cost_eur_bn: number; count: number;
  projection: boolean; ratio_to_revenue_pct?: number; yoy_change_pct?: number;
}
export interface TaxExpenditureKpi {
  kpi_id: string; kpi_name: string; description: string; unit: string;
  source: string; methodology: string; last_updated: string;
  france: TaxExpRow[]; peers: Record<string, never>;
  latest?: Record<string, unknown>;
}
export interface MonthlyBlock { months: string[]; [series: string]: number[] | string[] }
export interface MonthlyKpi {
  kpi_id: string; year: number; last_month: string; last_updated: string;
  revenues: MonthlyBlock; spending: MonthlyBlock; balance: MonthlyBlock;
  yoy: { revenue_change_pct: number; spending_change_pct: number };
}
export interface Meta {
  last_run: string; pipeline_version: string; mode: string;
  output_files: string[]; sources: Record<string, unknown>;
}

// ---- Normalized view model (what components consume) --------------------
export type Unit = "percent" | "eur_bn" | "years" | "eur" | "mixed";
export type XKind = "year" | "month";
export interface ViewPoint { x: number | string; y: number; projection?: boolean }
export interface ViewSeries { id: string; label: string; role: "france" | "oecd" | "secondary"; points: ViewPoint[] }
export interface SecondaryBlock { title: string; unit: Unit; series: ViewSeries[]; comparison?: ViewSeries }
export interface LatestStat { year: number | string; value: number; unit: Unit; yoy?: number }
export interface KpiView {
  slug: string;            // route slug, e.g. "overhead_rate"
  apiId: string;           // file/api id, e.g. "kpi_overhead_rate"
  title: string;           // French label (from registry)
  explainer: string;       // French explainer (from registry)
  unit: Unit;
  xKind: XKind;
  series: ViewSeries[];        // primary chart series (france first)
  comparison?: ViewSeries;     // OECD average (undefined when unavailable)
  secondary?: SecondaryBlock;  // e.g. debt (sustainability), life expectancy (outcomes)
  latest?: LatestStat;
  hasBreak2020: boolean;       // true if any france point switches source around 2020
  source: string;              // from JSON (empty for monthly)
  methodology: string;         // from JSON (empty for monthly)
}
```

- [ ] **Step 2: Verify types compile**

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/types.ts
git commit -m "feat(frontend): add raw + view-model types"
```

---

## Task 3: French formatters (TDD)

**Files:** `src/data/format.ts`, `src/data/format.test.ts`.

- [ ] **Step 1: Write failing tests** — create `src/data/format.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { fmtPercent, fmtEurBn, fmtYears, fmtNumber, fmtDateFr, fmtYoy } from "./format";

describe("french formatters", () => {
  it("formats percent with comma + space + sign-free", () => {
    expect(fmtPercent(5.79)).toBe("5,79 %");
    expect(fmtPercent(-8.93)).toBe("−8,93 %"); // minus sign U+2212
  });
  it("formats euro billions", () => {
    expect(fmtEurBn(81.7)).toBe("81,7 Md€");
  });
  it("formats years (life expectancy)", () => {
    expect(fmtYears(83)).toBe("83,0 ans");
  });
  it("formats plain numbers with fr grouping", () => {
    expect(fmtNumber(1456129)).toBe("1 456 129"); // narrow no-break space groups
  });
  it("formats an ISO date in French", () => {
    expect(fmtDateFr("2026-05-21T10:03:39Z")).toBe("21 mai 2026");
  });
  it("formats YoY with arrow + signed percent", () => {
    expect(fmtYoy(-0.41)).toEqual({ text: "−0,41 %", dir: "down" });
    expect(fmtYoy(1.2)).toEqual({ text: "+1,2 %", dir: "up" });
    expect(fmtYoy(0)).toEqual({ text: "0,0 %", dir: "flat" });
  });
});
```

- [ ] **Step 2: Run — expect fail** (`Cannot find module './format'`)

Run: `npm test -- format`
Expected: FAIL.

- [ ] **Step 3: Implement** — create `src/data/format.ts`:

```ts
const nf = (min: number, max: number) =>
  new Intl.NumberFormat("fr-FR", { minimumFractionDigits: min, maximumFractionDigits: max });

export function fmtPercent(v: number): string {
  return `${nf(2, 2).format(v)} %`;
}
export function fmtEurBn(v: number): string {
  return `${nf(1, 1).format(v)} Md€`;
}
export function fmtYears(v: number): string {
  return `${nf(1, 1).format(v)} ans`;
}
export function fmtNumber(v: number): string {
  return nf(0, 0).format(v);
}
export function fmtDateFr(iso: string): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(iso));
}
export type YoyDir = "up" | "down" | "flat";
export function fmtYoy(v: number): { text: string; dir: YoyDir } {
  const dir: YoyDir = v > 0 ? "up" : v < 0 ? "down" : "flat";
  const sign = v > 0 ? "+" : ""; // negatives already carry U+2212 via fr-FR
  return { text: `${sign}${nf(1, 1).format(v)} %`, dir };
}
```

- [ ] **Step 4: Run — expect pass**

Run: `npm test -- format`
Expected: 6 passed. (If a spacing assertion fails, copy the exact glyphs from the test — fr-FR uses U+202F narrow no-break space for grouping and U+2212 minus.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/format.ts frontend/src/data/format.test.ts
git commit -m "feat(frontend): French number/date formatters"
```

---

## Task 4: Adapters — standard, peers, sustainability (TDD)

**Files:** `src/data/adapters.ts`, `src/data/adapters.test.ts`.

- [ ] **Step 1: Write failing tests** — create `src/data/adapters.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { adaptStandard, adaptSustainability } from "./adapters";
import overhead from "../fixtures/kpi_overhead_rate.json";
import sustainability from "../fixtures/kpi_sustainability.json";

const base = { slug: "overhead_rate", title: "T", explainer: "E", unit: "percent" as const };

describe("adaptStandard", () => {
  const v = adaptStandard(overhead as any, base);
  it("maps france series first, role france", () => {
    expect(v.series[0].role).toBe("france");
    expect(v.series[0].points[0]).toEqual({ x: 1995, y: 24.11 });
  });
  it("exposes OECD_AVG as comparison and ignores the 6 countries", () => {
    expect(v.comparison?.role).toBe("oecd");
    expect(v.comparison?.points.length).toBeGreaterThan(0);
  });
  it("derives latest with yoy", () => {
    expect(v.latest?.unit).toBe("percent");
    expect(typeof v.latest?.yoy).toBe("number");
  });
  it("xKind is year", () => expect(v.xKind).toBe("year"));
});

describe("adaptSustainability", () => {
  const v = adaptSustainability(sustainability as any,
    { slug: "sustainability", title: "T", explainer: "E", unit: "percent" });
  it("primary = deficit, comparison = OECD_AVG deficit", () => {
    expect(v.series[0].points.find((p) => p.x === 2024)?.y).toBe(-5.79);
    expect(v.comparison?.role).toBe("oecd");
  });
  it("secondary = debt with its own OECD comparison", () => {
    expect(v.secondary?.title).toMatch(/dette/i);
    expect(v.secondary?.series[0].points.find((p) => p.x === 2024)?.y).toBe(112.6);
    expect(v.secondary?.comparison?.points.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- adapters`
Expected: FAIL (module not found). (Note: fixture JSON import needs `resolveJsonModule`, which Vite/TS templates enable by default; if `tsc` complains, ensure `"resolveJsonModule": true` in `tsconfig.app.json`.)

- [ ] **Step 3: Implement** — create `src/data/adapters.ts`:

```ts
import type {
  KpiView, ViewSeries, Unit, RawPoint, StdSeriesKpi, SustainabilityKpi,
} from "./types";

export interface AdaptBase { slug: string; title: string; explainer: string; unit: Unit }

const OECD = "OECD_AVG";

function yearPoints(rows: RawPoint[]): { x: number; y: number }[] {
  return rows.map((r) => ({ x: r.year, y: r.value }));
}
function detectBreak(rows: RawPoint[]): boolean {
  const sources = new Set(rows.filter((r) => r.source).map((r) => r.source));
  return sources.size > 1;
}
function franceSeries(rows: RawPoint[]): ViewSeries {
  return { id: "france", label: "France", role: "france", points: yearPoints(rows) };
}
function oecdSeries(peers?: Record<string, RawPoint[]>): ViewSeries | undefined {
  const rows = peers?.[OECD];
  if (!rows || rows.length === 0) return undefined;
  return { id: "oecd", label: "Moyenne OCDE", role: "oecd", points: yearPoints(rows) };
}
function latestFrom(rows: RawPoint[], unit: Unit, given?: StdSeriesKpi["latest"]) {
  if (given) return { year: given.year, value: given.value, unit, yoy: given.yoy_change };
  if (rows.length === 0) return undefined;
  const last = rows[rows.length - 1];
  const prev = rows[rows.length - 2];
  const yoy = prev ? last.value - prev.value : undefined;
  return { year: last.year, value: last.value, unit, yoy };
}

function meta(raw: { source: string; methodology: string }) {
  return { source: raw.source, methodology: raw.methodology };
}

export function adaptStandard(raw: StdSeriesKpi, b: AdaptBase): KpiView {
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer,
    unit: b.unit, xKind: "year",
    series: [franceSeries(raw.france)],
    comparison: oecdSeries(raw.peers),
    latest: latestFrom(raw.france, b.unit, raw.latest),
    hasBreak2020: detectBreak(raw.france),
    ...meta(raw),
  };
}

export function adaptSustainability(raw: SustainabilityKpi, b: AdaptBase): KpiView {
  const deficitPeers = (raw.peers as any)?.deficit as Record<string, RawPoint[]> | undefined;
  const debtPeers = (raw.peers as any)?.debt as Record<string, RawPoint[]> | undefined;
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer,
    unit: "percent", xKind: "year",
    series: [franceSeries(raw.france)],
    comparison: oecdSeries(deficitPeers),
    secondary: {
      title: "Dette publique (Maastricht, % du PIB)", unit: "percent",
      series: [franceSeries(raw.debt.france)],
      comparison: oecdSeries(debtPeers),
    },
    latest: latestFrom(raw.france, "percent", raw.latest),
    hasBreak2020: false,
    ...meta(raw),
  };
}
```

- [ ] **Step 4: Run — expect pass**

Run: `npm test -- adapters`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/adapters.ts frontend/src/data/adapters.test.ts
git commit -m "feat(frontend): standard + sustainability adapters"
```

---

## Task 5: Adapters — outcomes, tax expenditure, monthly (TDD)

**Files:** modify `src/data/adapters.ts`, `src/data/adapters.test.ts`.

- [ ] **Step 1: Add failing tests** — append to `src/data/adapters.test.ts`:

```ts
import { adaptOutcomes, adaptTaxExpenditure, adaptMonthly } from "./adapters";
import outcomes from "../fixtures/kpi_outcomes.json";
import taxexp from "../fixtures/kpi_tax_expenditure.json";
import monthly from "../fixtures/kpi_monthly_execution.json";

describe("adaptOutcomes", () => {
  const v = adaptOutcomes(outcomes as any,
    { slug: "outcomes", title: "T", explainer: "E", unit: "mixed" });
  it("primary = health spend %GDP, secondary = life expectancy", () => {
    expect(v.series[0].points[0]).toEqual({ x: 1995, y: 7.13 });
    expect(v.secondary?.unit).toBe("years");
    expect(v.secondary?.series[0].points.length).toBeGreaterThan(0);
  });
  it("no OECD comparison", () => expect(v.comparison).toBeUndefined());
  it("flags the 2020 source break", () => expect(v.hasBreak2020).toBe(true));
});

describe("adaptTaxExpenditure", () => {
  const v = adaptTaxExpenditure(taxexp as any,
    { slug: "tax_expenditure", title: "T", explainer: "E", unit: "eur_bn" });
  it("plots total_cost_eur_bn and marks projections", () => {
    expect(v.series[0].points[0]).toEqual({ x: 1999, y: 52.95, projection: false });
    expect(v.series[0].points.some((p) => p.projection === true)).toBe(true);
  });
});

describe("adaptMonthly", () => {
  const v = adaptMonthly(monthly as any,
    { slug: "monthly_execution", title: "T", explainer: "E", unit: "eur" });
  it("uses a month x-axis with revenue/spending series", () => {
    expect(v.xKind).toBe("month");
    const ids = v.series.map((s) => s.id);
    expect(ids).toContain("revenues");
    expect(ids).toContain("spending");
    expect(v.series[0].points[0].x).toBe("2026-01");
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- adapters`
Expected: FAIL (new exports missing).

- [ ] **Step 3: Implement** — append to `src/data/adapters.ts`:

```ts
import type { OutcomesKpi, TaxExpenditureKpi, MonthlyKpi } from "./types";

export function adaptOutcomes(raw: OutcomesKpi, b: AdaptBase): KpiView {
  const spend = raw.health.spend_pct_gdp;
  const life = raw.health.life_expectancy_years;
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer,
    unit: "percent", xKind: "year",
    series: [{ id: "health_spend", label: "Dépenses de santé (% du PIB)", role: "france", points: yearPoints(spend) }],
    secondary: {
      title: "Espérance de vie à la naissance", unit: "years",
      series: [{ id: "life_exp", label: "Espérance de vie", role: "secondary", points: yearPoints(life) }],
    },
    latest: latestFrom(spend, "percent"),
    hasBreak2020: detectBreak(spend),
    ...meta(raw),
  };
}

export function adaptTaxExpenditure(raw: TaxExpenditureKpi, b: AdaptBase): KpiView {
  const points = raw.france.map((r) => ({ x: r.year, y: r.total_cost_eur_bn, projection: r.projection }));
  const rows = raw.france;
  const last = rows[rows.length - 1];
  const prev = rows[rows.length - 2];
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer,
    unit: "eur_bn", xKind: "year",
    series: [{ id: "tax_cost", label: "Coût des dépenses fiscales", role: "france", points }],
    latest: last
      ? { year: last.year, value: last.total_cost_eur_bn, unit: "eur_bn",
          yoy: last.yoy_change_pct ?? (prev ? ((last.total_cost_eur_bn - prev.total_cost_eur_bn) / prev.total_cost_eur_bn) * 100 : undefined) }
      : undefined,
    hasBreak2020: false,
    ...meta(raw),
  };
}

export function adaptMonthly(raw: MonthlyKpi, b: AdaptBase): KpiView {
  const months = raw.revenues.months;
  const toPoints = (vals: number[]) => months.map((m, i) => ({ x: m, y: vals[i] }));
  const lastIdx = months.length - 1;
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer,
    unit: "eur", xKind: "month",
    series: [
      { id: "revenues", label: "Recettes (cumul, €)", role: "france", points: toPoints(raw.revenues.total as number[]) },
      { id: "spending", label: "Dépenses (cumul, €)", role: "secondary", points: toPoints(raw.spending.total as number[]) },
    ],
    latest: { year: raw.last_month, value: (raw.balance.cumulative as number[])[lastIdx], unit: "eur",
              yoy: raw.yoy.revenue_change_pct },
    hasBreak2020: false,
    source: "", methodology: "",
  };
}
```

- [ ] **Step 4: Run — expect pass**

Run: `npm test -- adapters`
Expected: all adapter tests pass (10 total).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/adapters.ts frontend/src/data/adapters.test.ts
git commit -m "feat(frontend): outcomes, tax-expenditure, monthly adapters"
```

---

## Task 6: KPI registry (TDD)

**Files:** `src/data/registry.ts`, `src/data/registry.test.ts`.

> The French `explainer` strings below are **drafts** the user will refine; they are real content (not placeholders) so the app is complete and runnable.

- [ ] **Step 1: Write failing tests** — create `src/data/registry.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { REGISTRY, THEMES, bySlug, buildView } from "./registry";
import overhead from "../fixtures/kpi_overhead_rate.json";

describe("registry", () => {
  it("has all 10 KPIs across 3 themes", () => {
    expect(REGISTRY.length).toBe(10);
    expect(THEMES.length).toBe(3);
  });
  it("every entry maps slug → apiId with kpi_ prefix and has French copy", () => {
    for (const e of REGISTRY) {
      expect(e.apiId).toBe(`kpi_${e.slug}`);
      expect(e.title.length).toBeGreaterThan(0);
      expect(e.explainer.length).toBeGreaterThan(10);
    }
  });
  it("bySlug finds an entry", () => {
    expect(bySlug("overhead_rate")?.apiId).toBe("kpi_overhead_rate");
  });
  it("buildView produces a KpiView via the entry's adapter", () => {
    const v = buildView("overhead_rate", overhead as any);
    expect(v.series[0].role).toBe("france");
    expect(v.title).toMatch(/administratif/i);
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- registry`
Expected: FAIL.

- [ ] **Step 3: Implement** — create `src/data/registry.ts`:

```ts
import type { KpiView, Unit } from "./types";
import {
  AdaptBase, adaptStandard, adaptSustainability, adaptOutcomes,
  adaptTaxExpenditure, adaptMonthly,
} from "./adapters";

export type ThemeId = "efficacite" | "soutenabilite" | "depenses";
export const THEMES: { id: ThemeId; label: string }[] = [
  { id: "efficacite", label: "Efficacité administrative" },
  { id: "soutenabilite", label: "Soutenabilité des finances publiques" },
  { id: "depenses", label: "Dépenses & résultats" },
];

type Adapter = (raw: any, b: AdaptBase) => KpiView;
export interface Entry {
  slug: string; apiId: string; theme: ThemeId; unit: Unit;
  title: string; explainer: string; adapter: Adapter;
}

const e = (slug: string, theme: ThemeId, unit: Unit, title: string, explainer: string, adapter: Adapter): Entry =>
  ({ slug, apiId: `kpi_${slug}`, theme, unit, title, explainer, adapter });

export const REGISTRY: Entry[] = [
  e("overhead_rate", "efficacite", "percent", "Coût administratif",
    "Part de la masse salariale publique dans la dépense publique totale : combien de chaque euro dépensé sert à faire fonctionner l’administration plutôt qu’à délivrer des services.", adaptStandard),
  e("friction_ratio", "efficacite", "percent", "Ratio de friction",
    "Poids des fonctions administratives générales (administration, défense, ordre public) rapporté aux recettes : ce que coûte « l’appareil » avant toute action publique.", adaptStandard),
  e("productive_spend", "efficacite", "percent", "Part des dépenses productives",
    "Part des dépenses publiques consacrée aux fonctions productives (affaires économiques, environnement, logement) dans le total des dépenses par fonction.", adaptStandard),
  e("wage_ratio", "efficacite", "percent", "Masse salariale public / privé",
    "Masse salariale publique rapportée à la masse salariale privée : mesure le poids relatif de l’emploi public dans la rémunération du pays.", adaptStandard),
  e("sustainability", "soutenabilite", "percent", "Déficit public & dette",
    "Solde public (déficit ou excédent) en % du PIB, accompagné de la dette publique au sens de Maastricht. Indique si les finances publiques sont soutenables dans la durée.", adaptSustainability),
  e("debt_service", "soutenabilite", "percent", "Charge de la dette",
    "Intérêts de la dette publique rapportés aux recettes : la part des recettes absorbée par le seul service de la dette, avant toute dépense.", adaptStandard),
  e("pension_investment", "soutenabilite", "percent", "Retraites vs investissement",
    "Comparaison de la part des dépenses consacrée aux retraites et de celle consacrée à l’investissement public : un arbitrage entre transferts et préparation de l’avenir.", adaptStandard),
  e("outcomes", "depenses", "mixed", "Dépenses de santé vs espérance de vie",
    "Dépenses publiques de santé (% du PIB) mises en regard de l’espérance de vie à la naissance : un écart croissant entre dépense en hausse et résultats stables signale une efficacité déclinante.", adaptOutcomes),
  e("tax_expenditure", "depenses", "eur_bn", "Dépenses fiscales (niches)",
    "Coût total des dépenses fiscales (« niches ») : les recettes auxquelles l’État renonce via exonérations, taux réduits et crédits d’impôt. Les deux dernières années sont des prévisions.", adaptTaxExpenditure),
  e("monthly_execution", "depenses", "eur", "Exécution budgétaire mensuelle",
    "Recettes et dépenses du budget général de l’État, cumulées mois par mois sur l’année en cours : le suivi le plus récent de l’exécution budgétaire.", adaptMonthly),
];

export function bySlug(slug: string): Entry | undefined {
  return REGISTRY.find((x) => x.slug === slug);
}
export function buildView(slug: string, raw: unknown): KpiView {
  const entry = bySlug(slug);
  if (!entry) throw new Error(`unknown KPI slug: ${slug}`);
  const { slug: s, title, explainer, unit } = entry;
  return entry.adapter(raw, { slug: s, title, explainer, unit });
}
```

- [ ] **Step 4: Run — expect pass**

Run: `npm test -- registry`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/registry.ts frontend/src/data/registry.test.ts
git commit -m "feat(frontend): KPI registry with French copy + theme grouping"
```

---

## Task 7: Data/API layer (TDD)

**Files:** `src/data/api.ts`, `src/data/api.test.ts`.

- [ ] **Step 1: Write failing tests** — create `src/data/api.test.ts`:

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { getMeta, getKpi, _resetCache } from "./api";

beforeEach(() => _resetCache());

describe("api (fixtures mode)", () => {
  it("getMeta returns the meta fixture", async () => {
    const m = await getMeta();
    expect(typeof m.last_run).toBe("string");
  });
  it("getKpi returns a raw KPI by apiId", async () => {
    const raw = await getKpi("kpi_overhead_rate");
    expect((raw as any).kpi_id).toBe("overhead_rate");
  });
  it("caches: second call returns same reference", async () => {
    const a = await getKpi("kpi_overhead_rate");
    const b = await getKpi("kpi_overhead_rate");
    expect(a).toBe(b);
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- api`
Expected: FAIL.

- [ ] **Step 3: Implement** — create `src/data/api.ts`. In test/dev (no `VITE_API_BASE`) it loads bundled fixtures; in prod it fetches the live API.

```ts
import type { Meta } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";
const ALL_APP_IDS = [
  "kpi_overhead_rate", "kpi_friction_ratio", "kpi_productive_spend", "kpi_wage_ratio",
  "kpi_sustainability", "kpi_debt_service", "kpi_pension_investment",
  "kpi_outcomes", "kpi_tax_expenditure", "kpi_monthly_execution",
];

// Eagerly import fixtures so they bundle for dev/test (used when BASE is empty).
const fixtures = import.meta.glob("../fixtures/*.json", { eager: true }) as Record<string, { default: unknown }>;
function fixture(name: string): unknown {
  const hit = fixtures[`../fixtures/${name}.json`];
  if (!hit) throw new Error(`fixture not found: ${name}`);
  return hit.default;
}

let cache = new Map<string, unknown>();
export function _resetCache() { cache = new Map(); }

async function load(name: string, apiPath: string): Promise<unknown> {
  if (cache.has(name)) return cache.get(name);
  const value = BASE
    ? await fetch(`${BASE}${apiPath}`).then((r) => {
        if (!r.ok) throw new Error(`${apiPath} -> ${r.status}`);
        return r.json();
      })
    : fixture(name);
  cache.set(name, value);
  return value;
}

export async function getMeta(): Promise<Meta> {
  return load("meta", "/api/meta") as Promise<Meta>;
}
export async function getKpi(apiId: string): Promise<unknown> {
  return load(apiId, `/api/kpi/${apiId}`);
}
export const ALL_KPI_IDS = ALL_APP_IDS;
```

- [ ] **Step 4: Run — expect pass**

Run: `npm test -- api`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/api.ts frontend/src/data/api.test.ts
git commit -m "feat(frontend): fixtures/live data layer with cache"
```

---

## Task 8: Data hooks + routing shell

**Files:** `src/data/useData.ts`, `src/App.tsx`, `src/main.tsx`, `src/components/AppShell.tsx`, `src/components/AppShell.test.tsx`.

- [ ] **Step 1: Write a failing AppShell test** — create `src/components/AppShell.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("renders the title and a last-updated badge", () => {
    render(
      <MemoryRouter>
        <AppShell lastUpdated="2026-05-21T10:03:39Z">
          <p>contenu</p>
        </AppShell>
      </MemoryRouter>,
    );
    expect(screen.getByRole("banner")).toHaveTextContent(/fiscoscope/i);
    expect(screen.getByText(/Dernière mise à jour/i)).toHaveTextContent(/21 mai 2026/);
    expect(screen.getByText("contenu")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- AppShell`
Expected: FAIL.

- [ ] **Step 3: Implement AppShell** — create `src/components/AppShell.tsx`:

```tsx
import { ReactNode } from "react";
import { Link } from "react-router-dom";
import { fmtDateFr } from "../data/format";

export function AppShell({ lastUpdated, children }: { lastUpdated?: string; children: ReactNode }) {
  return (
    <div className="app-shell">
      <header role="banner" className="app-header">
        <Link to="/" className="brand">fiscoscope</Link>
        <p className="tagline">L’efficacité de l’administration publique française, en chiffres</p>
        {lastUpdated && (
          <p className="last-updated">Dernière mise à jour : {fmtDateFr(lastUpdated)}</p>
        )}
      </header>
      <main>{children}</main>
      <footer className="app-footer">
        <p>
          Sources : INSEE, OCDE (Government at a Glance), GTED (CC-BY-4.0). Données publiques.{" "}
          <Link to="/methodologie">Méthodologie</Link>
        </p>
      </footer>
    </div>
  );
}
```

- [ ] **Step 4: Implement hooks + routes** — create `src/data/useData.ts`:

```tsx
import { useEffect, useState } from "react";
import { getKpi, getMeta } from "./api";
import { buildView } from "./registry";
import type { KpiView, Meta } from "./types";

export function useMeta() {
  const [meta, setMeta] = useState<Meta | null>(null);
  useEffect(() => { getMeta().then(setMeta).catch(() => setMeta(null)); }, []);
  return meta;
}
export function useKpiView(slug: string) {
  const [view, setView] = useState<KpiView | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let live = true;
    getKpi(`kpi_${slug}`)
      .then((raw) => live && setView(buildView(slug, raw)))
      .catch(() => live && setError(true));
    return () => { live = false; };
  }, [slug]);
  return { view, error };
}
```

Create `src/App.tsx`:

```tsx
import { Routes, Route } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { useMeta } from "./data/useData";
import { Overview } from "./pages/Overview";
import { KpiDetail } from "./pages/KpiDetail";
import { Methodology } from "./pages/Methodology";

export default function App() {
  const meta = useMeta();
  return (
    <AppShell lastUpdated={meta?.last_run}>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/kpi/:slug" element={<KpiDetail />} />
        <Route path="/methodologie" element={<Methodology />} />
      </Routes>
    </AppShell>
  );
}
```

Replace `src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

Create empty `src/styles/global.css` (filled in Task 14) and **stub pages** so the app compiles (each is fully implemented in Tasks 10–13):

```tsx
// src/pages/Overview.tsx
export function Overview() { return <p>overview</p>; }
```
```tsx
// src/pages/KpiDetail.tsx
export function KpiDetail() { return <p>detail</p>; }
```
```tsx
// src/pages/Methodology.tsx
export function Methodology() { return <p>methodologie</p>; }
```

- [ ] **Step 5: Run — expect pass + typecheck**

Run: `npm test -- AppShell` → 1 passed.
Run: `npx tsc --noEmit` → no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): routing shell, AppShell, data hooks, page stubs"
```

---

## Task 9: Sparkline + KpiCard (TDD)

**Files:** `src/components/Sparkline.tsx`, `src/components/KpiCard.tsx`, `src/components/KpiCard.test.tsx`.

- [ ] **Step 1: Write failing test** — create `src/components/KpiCard.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { KpiCard } from "./KpiCard";
import overhead from "../fixtures/kpi_overhead_rate.json";
import { buildView } from "../data/registry";

function renderCard(raw: unknown, slug: string) {
  render(<MemoryRouter><KpiCard view={buildView(slug, raw)} /></MemoryRouter>);
}

describe("KpiCard", () => {
  it("shows the French title, formatted latest value, and links to detail", () => {
    renderCard(overhead, "overhead_rate");
    expect(screen.getByRole("link")).toHaveAttribute("href", "/kpi/overhead_rate");
    expect(screen.getByText(/Coût administratif/)).toBeInTheDocument();
    // latest overhead value 2025 formatted as fr percent
    expect(screen.getByTestId("kpi-latest").textContent).toMatch(/%/);
  });
  it("renders a YoY direction indicator", () => {
    renderCard(overhead, "overhead_rate");
    expect(screen.getByTestId("kpi-yoy")).toHaveAttribute("data-dir");
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- KpiCard`
Expected: FAIL.

- [ ] **Step 3: Implement Sparkline + KpiCard** (functional; visuals refined in Task 14)

Create `src/components/Sparkline.tsx`:

```tsx
import { LineChart, Line, YAxis } from "recharts";
import type { ViewSeries } from "../data/types";

export function Sparkline({ series }: { series: ViewSeries }) {
  const data = series.points.map((p) => ({ x: p.x, y: p.y }));
  return (
    <LineChart width={120} height={36} data={data} aria-hidden="true">
      <YAxis hide domain={["dataMin", "dataMax"]} />
      <Line type="monotone" dataKey="y" dot={false} strokeWidth={2} stroke="#0055A4" isAnimationActive={false} />
    </LineChart>
  );
}
```

Create `src/components/KpiCard.tsx`:

```tsx
import { Link } from "react-router-dom";
import type { KpiView } from "../data/types";
import { Sparkline } from "./Sparkline";
import { fmtPercent, fmtEurBn, fmtYears, fmtYoy } from "../data/format";

function fmtValue(unit: KpiView["unit"], v: number): string {
  if (unit === "eur_bn") return fmtEurBn(v);
  if (unit === "years") return fmtYears(v);
  if (unit === "eur") return new Intl.NumberFormat("fr-FR", { notation: "compact", style: "currency", currency: "EUR" }).format(v);
  return fmtPercent(v);
}

export function KpiCard({ view }: { view: KpiView }) {
  const yoy = view.latest?.yoy != null ? fmtYoy(view.latest.yoy) : null;
  const hasOecd = !!view.comparison;
  return (
    <Link to={`/kpi/${view.slug}`} className="kpi-card">
      <h3 className="kpi-card__title">{view.title}</h3>
      <div className="kpi-card__figure">
        {view.latest && (
          <span data-testid="kpi-latest" className="kpi-card__value">
            {fmtValue(view.latest.unit, view.latest.value)}
          </span>
        )}
        {yoy && (
          <span data-testid="kpi-yoy" data-dir={yoy.dir} className={`kpi-card__yoy yoy--${yoy.dir}`}>
            {yoy.dir === "up" ? "▲" : yoy.dir === "down" ? "▼" : "▬"} {yoy.text}
          </span>
        )}
      </div>
      <Sparkline series={view.series[0]} />
      {hasOecd && <span className="kpi-card__badge">vs moyenne OCDE</span>}
    </Link>
  );
}
```

- [ ] **Step 4: Run — expect pass**

Run: `npm test -- KpiCard`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Sparkline.tsx frontend/src/components/KpiCard.tsx frontend/src/components/KpiCard.test.tsx
git commit -m "feat(frontend): Sparkline + KpiCard"
```

---

## Task 10: Overview page (TDD)

**Files:** `src/pages/Overview.tsx` (replace stub), `src/pages/Overview.test.tsx`.

- [ ] **Step 1: Write failing test** — create `src/pages/Overview.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Overview } from "./Overview";

describe("Overview", () => {
  it("renders the 3 theme headings and 10 KPI cards", async () => {
    render(<MemoryRouter><Overview /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("Efficacité administrative")).toBeInTheDocument();
    });
    expect(screen.getByText("Soutenabilité des finances publiques")).toBeInTheDocument();
    expect(screen.getByText("Dépenses & résultats")).toBeInTheDocument();
    const cards = await screen.findAllByRole("link");
    // 10 KPI cards (theme headings are not links)
    expect(cards.filter((c) => c.getAttribute("href")?.startsWith("/kpi/")).length).toBe(10);
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- Overview`
Expected: FAIL (stub renders only "overview").

- [ ] **Step 3: Implement** — replace `src/pages/Overview.tsx`:

```tsx
import { useEffect, useState } from "react";
import { REGISTRY, THEMES, buildView } from "../data/registry";
import { getKpi } from "../data/api";
import type { KpiView } from "../data/types";
import { KpiCard } from "../components/KpiCard";

export function Overview() {
  const [views, setViews] = useState<KpiView[]>([]);
  useEffect(() => {
    Promise.all(
      REGISTRY.map((e) => getKpi(e.apiId).then((raw) => buildView(e.slug, raw))),
    ).then(setViews);
  }, []);

  return (
    <div className="overview">
      <p className="overview__intro">
        Des indicateurs longitudinaux (depuis 1995) mesurant l’efficacité de l’administration
        publique française, à partir de données publiques, comparés à la moyenne de l’OCDE.
      </p>
      {THEMES.map((theme) => {
        const themeViews = views.filter(
          (v) => REGISTRY.find((e) => e.slug === v.slug)?.theme === theme.id,
        );
        return (
          <section key={theme.id} className="theme-section">
            <h2 className="theme-section__title">{theme.label}</h2>
            <div className="kpi-grid">
              {themeViews.map((v) => <KpiCard key={v.slug} view={v} />)}
            </div>
          </section>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run — expect pass**

Run: `npm test -- Overview`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Overview.tsx frontend/src/pages/Overview.test.tsx
git commit -m "feat(frontend): overview page with themed KPI grid"
```

---

## Task 11: TimeSeriesChart (TDD)

**Files:** `src/components/TimeSeriesChart.tsx`, `src/components/TimeSeriesChart.test.tsx`.

> Recharts renders to SVG in jsdom but needs a sized container; tests assert on the legend/toggle DOM and series wiring, not pixel output.

- [ ] **Step 1: Write failing test** — create `src/components/TimeSeriesChart.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TimeSeriesChart } from "./TimeSeriesChart";
import type { KpiView } from "../data/types";

const view: KpiView = {
  slug: "x", apiId: "kpi_x", title: "T", explainer: "E", unit: "percent", xKind: "year",
  series: [{ id: "france", label: "France", role: "france",
    points: [{ x: 2018, y: 1 }, { x: 2019, y: 2 }] }],
  comparison: { id: "oecd", label: "Moyenne OCDE", role: "oecd",
    points: [{ x: 2018, y: 1.5 }, { x: 2019, y: 1.6 }] },
  hasBreak2020: false, source: "s", methodology: "m",
};

describe("TimeSeriesChart", () => {
  it("hides the OECD comparison until toggled on", async () => {
    render(<TimeSeriesChart view={view} />);
    const toggle = screen.getByRole("checkbox", { name: /moyenne ocde/i });
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    expect(toggle).toBeChecked();
  });
  it("renders no toggle when there is no comparison", () => {
    render(<TimeSeriesChart view={{ ...view, comparison: undefined }} />);
    expect(screen.queryByRole("checkbox")).toBeNull();
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- TimeSeriesChart`
Expected: FAIL.

- [ ] **Step 3: Implement** — create `src/components/TimeSeriesChart.tsx`:

```tsx
import { useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import type { KpiView, ViewSeries } from "../data/types";

const COLORS: Record<ViewSeries["role"], string> = {
  france: "#0055A4", oecd: "#8A8576", secondary: "#CC785C",
};

function merge(seriesList: ViewSeries[]): Record<string, number | string>[] {
  const byX = new Map<number | string, Record<string, number | string>>();
  for (const s of seriesList) {
    for (const p of s.points) {
      const row = byX.get(p.x) ?? { x: p.x };
      row[s.id] = p.y;
      byX.set(p.x, row);
    }
  }
  return [...byX.values()].sort((a, b) => String(a.x).localeCompare(String(b.x)));
}

export function TimeSeriesChart({ view }: { view: KpiView }) {
  const [showOecd, setShowOecd] = useState(false);
  const active = [...view.series, ...(showOecd && view.comparison ? [view.comparison] : [])];
  const data = merge(active);
  return (
    <div className="chart">
      {view.comparison && (
        <label className="chart__toggle">
          <input type="checkbox" checked={showOecd} onChange={(e) => setShowOecd(e.target.checked)} />
          Comparer à la moyenne OCDE
        </label>
      )}
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E7E2D6" />
          <XAxis dataKey="x" />
          <YAxis />
          <Tooltip />
          <Legend />
          {active.map((s) => (
            <Line key={s.id} type="monotone" dataKey={s.id} name={s.label}
              stroke={COLORS[s.role]} strokeWidth={s.role === "france" ? 2.5 : 1.75}
              strokeDasharray={s.role === "oecd" ? "6 4" : undefined}
              dot={false} isAnimationActive={false} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
      {view.hasBreak2020 && (
        <p className="chart__note">Changement de base méthodologique en 2020 (INSEE → OCDE).</p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run — expect pass**

Run: `npm test -- TimeSeriesChart`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/TimeSeriesChart.tsx frontend/src/components/TimeSeriesChart.test.tsx
git commit -m "feat(frontend): TimeSeriesChart with OECD toggle + break note"
```

---

## Task 12: StatCallout, MethodologyDisclosure, KpiDetail page (TDD)

**Files:** `src/components/StatCallout.tsx`, `src/components/MethodologyDisclosure.tsx`, `src/pages/KpiDetail.tsx` (replace stub), `src/pages/KpiDetail.test.tsx`.

- [ ] **Step 1: Write failing test** — create `src/pages/KpiDetail.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { KpiDetail } from "./KpiDetail";

function renderAt(slug: string) {
  render(
    <MemoryRouter initialEntries={[`/kpi/${slug}`]}>
      <Routes><Route path="/kpi/:slug" element={<KpiDetail />} /></Routes>
    </MemoryRouter>,
  );
}

describe("KpiDetail", () => {
  it("renders title, explainer, and methodology disclosure for a standard KPI", async () => {
    renderAt("overhead_rate");
    await waitFor(() => expect(screen.getByRole("heading", { name: /Coût administratif/ })).toBeInTheDocument());
    expect(screen.getByText(/chaque euro dépensé/)).toBeInTheDocument();
    expect(screen.getByText(/Méthodologie & sources/i)).toBeInTheDocument();
  });
  it("renders the secondary block title for sustainability (debt)", async () => {
    renderAt("sustainability");
    await waitFor(() => expect(screen.getByText(/Dette publique/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run — expect fail**

Run: `npm test -- KpiDetail`
Expected: FAIL.

- [ ] **Step 3: Implement components**

Create `src/components/StatCallout.tsx`:

```tsx
import type { KpiView } from "../data/types";
import { fmtPercent, fmtEurBn, fmtYears, fmtYoy } from "../data/format";

export function StatCallout({ view }: { view: KpiView }) {
  if (!view.latest) return null;
  const { unit, value, year, yoy } = view.latest;
  const v = unit === "eur_bn" ? fmtEurBn(value) : unit === "years" ? fmtYears(value)
    : unit === "eur" ? new Intl.NumberFormat("fr-FR", { notation: "compact", style: "currency", currency: "EUR" }).format(value)
    : fmtPercent(value);
  const y = yoy != null ? fmtYoy(yoy) : null;
  return (
    <div className="stat-callout">
      <span className="stat-callout__value">{v}</span>
      <span className="stat-callout__year">en {year}</span>
      {y && <span className={`stat-callout__yoy yoy--${y.dir}`} data-dir={y.dir}>
        {y.dir === "up" ? "▲" : y.dir === "down" ? "▼" : "▬"} {y.text} sur un an</span>}
    </div>
  );
}
```

Create `src/components/MethodologyDisclosure.tsx`:

```tsx
export function MethodologyDisclosure({ source, methodology }: { source: string; methodology: string }) {
  if (!source && !methodology) return null;
  return (
    <details className="methodology">
      <summary>Méthodologie &amp; sources</summary>
      {methodology && <p className="methodology__body">{methodology}</p>}
      {source && <p className="methodology__source"><strong>Source :</strong> {source}</p>}
    </details>
  );
}
```

- [ ] **Step 4: Implement KpiDetail** — replace `src/pages/KpiDetail.tsx`:

```tsx
import { useParams, Link } from "react-router-dom";
import { useKpiView } from "../data/useData";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { StatCallout } from "../components/StatCallout";
import { MethodologyDisclosure } from "../components/MethodologyDisclosure";

export function KpiDetail() {
  const { slug = "" } = useParams();
  const { view, error } = useKpiView(slug);
  if (error) return <p className="state">Indicateur introuvable. <Link to="/">Retour</Link></p>;
  if (!view) return <p className="state">Chargement…</p>;
  return (
    <article className="kpi-detail">
      <nav className="breadcrumb"><Link to="/">← Tous les indicateurs</Link></nav>
      <h1>{view.title}</h1>
      <p className="kpi-detail__explainer">{view.explainer}</p>
      <StatCallout view={view} />
      <TimeSeriesChart view={view} />
      {view.secondary && (
        <section className="kpi-detail__secondary">
          <h2>{view.secondary.title}</h2>
          <TimeSeriesChart view={{ ...view, series: view.secondary.series,
            comparison: view.secondary.comparison, secondary: undefined, hasBreak2020: false }} />
        </section>
      )}
      <MethodologyDisclosure source={view.source} methodology={view.methodology} />
    </article>
  );
}
```

- [ ] **Step 5: Run — expect pass**

Run: `npm test -- KpiDetail`
Expected: 2 passed. Then `npm test` (full suite) → all green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/StatCallout.tsx frontend/src/components/MethodologyDisclosure.tsx frontend/src/pages/KpiDetail.tsx frontend/src/pages/KpiDetail.test.tsx
git commit -m "feat(frontend): KPI detail page with chart, stat callout, methodology"
```

---

## Task 13: Methodology / About page

**Files:** `src/pages/Methodology.tsx` (replace stub).

- [ ] **Step 1: Implement** — replace `src/pages/Methodology.tsx`:

```tsx
import { Link } from "react-router-dom";

export function Methodology() {
  return (
    <article className="methodology-page">
      <nav className="breadcrumb"><Link to="/">← Tous les indicateurs</Link></nav>
      <h1>Méthodologie</h1>
      <p>
        fiscoscope mesure la productivité et l’efficacité de l’administration publique française
        à partir de données publiques, sous forme de ratios (par euro dépensé), sur longue période
        (depuis 1995) et, lorsque c’est possible, en comparaison de la moyenne de l’OCDE.
      </p>
      <h2>Sources</h2>
      <ul>
        <li><strong>INSEE</strong> — comptes nationaux (séries BDM), pour les agrégats des administrations publiques et le PIB.</li>
        <li><strong>OCDE</strong> — Government at a Glance 2025 et statistiques de santé, pour la moyenne OCDE et l’espérance de vie.</li>
        <li><strong>GTED</strong> — Global Tax Expenditures Database (CC-BY-4.0), pour les dépenses fiscales.</li>
      </ul>
      <h2>Limites</h2>
      <p>
        Les comparaisons OCDE débutent en 2007. Un changement de base méthodologique INSEE intervient
        en 2020 sur certains indicateurs fonctionnels (signalé sur les graphiques concernés). Les
        dernières années de certaines séries sont des prévisions.
      </p>
    </article>
  );
}
```

- [ ] **Step 2: Verify** — `npx tsc --noEmit` (no errors) and `npm test` (full suite still green).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Methodology.tsx
git commit -m "feat(frontend): methodology/about page"
```

---

## Task 14: Visual design pass (REQUIRES the `frontend-design` skill)

**Files:** `src/styles/tokens.css`, `src/styles/global.css`, component CSS/classNames as needed, `index.html` (fonts).

> **Invoke the `frontend-design` skill for this task.** Goal: realise the spec's aesthetic — Anthropic editorial × French tricolore — against the existing components **without changing their DOM contracts or `data-testid`s** (tests must stay green). Constraints from the spec §3:
> - Canvas warm ivory `#F4F1EA`; ink dark slate `#28261F`; coral accent `#CC785C`; France data bleu `#0055A4`; rouge `#EF4135` only for meaningful negatives; OECD line neutral taupe `#8A8576` dashed.
> - Display serif **Fraunces**, body sans **Inter** (self-host or Google Fonts in `index.html`).
> - Generous whitespace, editorial rhythm; **no** gradients/glassmorphism/neon.
> - Responsive (cards reflow to 1 column on mobile); WCAG AA contrast; `prefers-reduced-motion` respected; color never the sole signal (keep the ▲/▼ arrows + dashed OECD line + labels).

- [ ] **Step 1: Add fonts** to `index.html` `<head>` (Google Fonts example; self-hosting is acceptable):

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
```

- [ ] **Step 2: Create design tokens** — `src/styles/tokens.css` with the palette/type/spacing variables above (CSS custom properties).

- [ ] **Step 3: Style globally + per component** — author `src/styles/global.css` (import tokens) and the component class styles (`.kpi-card`, `.kpi-grid`, `.theme-section`, `.app-header`, `.stat-callout`, `.chart`, etc.). Update the Recharts stroke colors only via the existing `COLORS` map (already aligned to tokens — keep in sync).

- [ ] **Step 4: Verify tests still pass** (DOM contracts unchanged)

Run: `npm test`
Expected: full suite green (no test edits should be needed; if a selector broke, restore the DOM contract rather than weakening the test).

- [ ] **Step 5: Visual check** — `npm run dev`, open the local URL, eyeball overview + a detail page (desktop + a narrow viewport).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/styles frontend/index.html frontend/src
git commit -m "style(frontend): Anthropic-editorial × tricolore visual design"
```

---

## Task 15: Playwright smoke test

**Files:** `playwright.config.ts`, `e2e/smoke.spec.ts`.

- [ ] **Step 1: Configure Playwright** — create `playwright.config.ts`:

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  webServer: { command: "npm run dev", url: "http://localhost:5173", reuseExistingServer: true },
  use: { baseURL: "http://localhost:5173" },
});
```

- [ ] **Step 2: Write the smoke test** — create `e2e/smoke.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test("overview loads and a card opens its detail", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Efficacité administrative")).toBeVisible();
  await page.getByRole("link", { name: /Coût administratif/ }).click();
  await expect(page).toHaveURL(/\/kpi\/overhead_rate/);
  await expect(page.getByRole("heading", { name: /Coût administratif/ })).toBeVisible();
});
```

- [ ] **Step 3: Install browser + run**

```bash
npx playwright install chromium
npm run e2e
```
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e
git commit -m "test(frontend): Playwright smoke (overview → detail)"
```

---

## Task 16: Build config + Cloudflare Pages wiring

**Files:** `frontend/.env.production`, `frontend/.env.example`, `frontend/README.md`.

- [ ] **Step 1: Document env** — create `frontend/.env.example`:

```
# Empty / unset = use bundled fixtures (dev + tests).
# Production: the backend HTTPS origin (no trailing slash), e.g. https://203-0-113-45.sslip.io
VITE_API_BASE=
```

Create `frontend/.env.production` (committed; the value is non-secret and matches the deployment plan's API host — fill in your real sslip.io host):

```
VITE_API_BASE=https://203-0-113-45.sslip.io
```

- [ ] **Step 2: README** — create `frontend/README.md` with: dev (`npm run dev`, fixtures), test (`npm test`, `npm run e2e`), build (`npm run build` → `dist/`), and the Cloudflare Pages settings:
  - Framework preset: **Vite**; build command `npm run build`; output dir `dist`; root dir `frontend`.
  - Set `VITE_API_BASE` in Pages → Settings → Environment variables to the backend origin.
  - The Pages production URL must equal the backend's `ALLOWED_ORIGINS` (deployment plan `.env`) for CORS.

- [ ] **Step 3: Production build sanity check** (fixtures off → expects the live API at runtime, but the *build* must succeed)

```bash
cd frontend && npm run build
```
Expected: clean type-check + build to `dist/`.

- [ ] **Step 4: Commit**

```bash
git add frontend/.env.example frontend/.env.production frontend/README.md
git commit -m "build(frontend): env config + Cloudflare Pages instructions"
```

- [ ] **Step 5 (manual, when ready):** In Cloudflare Pages, create/connect the project (root `frontend`, preset Vite, output `dist`), set `VITE_API_BASE`, deploy. Confirm the deployed URL matches the backend `ALLOWED_ORIGINS`. (This is the same Pages project reserved in the deployment plan's Phase 5.)

---

## Self-Review (plan vs. spec)

- **Audience/French/editorial (spec §2):** all copy French; explainers in registry; About page (Tasks 6, 13) ✓
- **Aesthetic Anthropic × tricolore, frontend-design skill (spec §3):** Task 14 (explicitly requires the skill), palette wired in `COLORS` + tokens ✓
- **IA: overview grid → detail, methodology page (spec §4):** Tasks 8 (routes), 10, 12, 13 ✓
- **Stack: Vite/React/TS/Recharts/Router, no kit (spec §5):** Task 1 ✓
- **Registry + grouping, French labels (spec §6):** Task 6 ✓
- **Components (spec §7):** AppShell (8), Sparkline+KpiCard (9), TimeSeriesChart (11), StatCallout+MethodologyDisclosure+KpiDetail (12) ✓
- **Data layer + per-KPI adapters for all shape variants (spec §8):** Tasks 2,4,5,7 — standard/peers/sustainability/outcomes/tax/monthly all covered; OECD_AVG-only; projections flagged; 2020 break detected ✓
- **Formatting/i18n/responsive/a11y (spec §9):** Task 3 (fr formatters), Task 14 (responsive/AA/arrows/dashed) ✓
- **Testing: Vitest/RTL + 1 Playwright (spec §10):** Tasks 3–12 unit/component, Task 15 e2e ✓
- **Deploy: Pages + VITE_API_BASE ↔ ALLOWED_ORIGINS (spec §11):** Task 16 ✓
- **Parallel via fixtures (spec §12):** Task 1 copies fixtures; Task 7 fixtures-by-default; entire build runs offline ✓
- **Scope/YAGNI (spec §13):** OECD-average only (no 6 countries), no dark mode, no export, French only — none added ✓

**Placeholder scan:** French explainer/About copy is real draft content (flagged as user-refinable in spec §14, not placeholders); every code step has complete code; the `203-0-113-45.sslip.io` host is an explicit fill-in matching the deployment plan. No "TBD"/"handle X" left.

**Type consistency:** `KpiView`/`ViewSeries`/`AdaptBase` defined in Tasks 2/4 and used identically in 5–12; adapter names (`adaptStandard`/`adaptSustainability`/`adaptOutcomes`/`adaptTaxExpenditure`/`adaptMonthly`) consistent between `adapters.ts`, `registry.ts`, and tests; `getKpi(apiId)`/`getMeta()`/`buildView(slug, raw)` signatures consistent across api/registry/hooks/pages; slug↔apiId (`kpi_` prefix) handled uniformly.
