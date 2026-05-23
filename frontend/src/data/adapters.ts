import type {
  KpiView, ViewSeries, Unit, RawPoint, StdSeriesKpi, SustainabilityKpi,
  OutcomesKpi, TaxExpenditureKpi, MonthlyKpi,
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
