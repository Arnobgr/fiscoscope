import type { Meta } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";
const ALL_APP_IDS = [
  "kpi_overhead_rate", "kpi_admin_overhead", "kpi_friction_ratio", "kpi_productive_spend", "kpi_public_employment", "kpi_wage_ratio",
  "kpi_tax_burden", "kpi_sustainability", "kpi_deficit_subsector", "kpi_debt_service", "kpi_pension_investment",
  "kpi_pensions", "kpi_outcomes", "kpi_performance", "kpi_tax_expenditure", "kpi_monthly_execution",
];

// Fixtures for dev/test (used when BASE is empty). Lazy: each is its own chunk,
// loaded on first use, so the ~0.5 MB performance drill-down files never weigh
// on the main bundle.
const fixtures = import.meta.glob("../fixtures/*.json", { import: "default" }) as Record<string, () => Promise<unknown>>;
async function fixture(name: string): Promise<unknown> {
  const hit = fixtures[`../fixtures/${name}.json`];
  if (!hit) throw new Error(`fixture not found: ${name}`);
  return hit();
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
    : await fixture(name);
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
