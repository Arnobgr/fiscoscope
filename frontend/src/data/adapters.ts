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
