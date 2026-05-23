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
