// ---- Raw JSON (as served by the backend) -------------------------------
export interface RawPoint { year: number; value: number; source?: string }
export interface StdSeriesKpi {            // overhead, admin_overhead, friction, productive, debt_service, pension_investment, wage_ratio
  kpi_id: string; kpi_name: string; description: string; unit: string;
  source: string; methodology: string; last_updated: string;
  france: RawPoint[];
  peers?: Record<string, RawPoint[]>;      // ISO3 country keys + at most one average (OECD_AVG, EU27_AVG or OECD_REP)
  latest?: { year: number; value: number; yoy_change?: number };
}
export interface SustainabilityKpi extends StdSeriesKpi {
  debt: { france: RawPoint[] };
  debt_holders?: { france: { non_residents: RawPoint[]; central_bank: RawPoint[]; other_residents: RawPoint[] } };
  peers?: { deficit?: Record<string, RawPoint[]>; debt?: Record<string, RawPoint[]> } & Record<string, never>;
}
export interface PensionsKpi extends StdSeriesKpi {
  pct_gdp: { france: RawPoint[]; peers?: Record<string, RawPoint[]> };
}
export interface SubsectorSeries { pct_gdp: RawPoint[]; eur_bn: RawPoint[] }
export interface DeficitSubsectorKpi extends StdSeriesKpi {
  subsectors: { central: SubsectorSeries; local: SubsectorSeries; social_security: SubsectorSeries; total: SubsectorSeries };
}
export type PerfStatus = "met" | "improved" | "not_improved" | "not_reported" | "not_retained";
export type PerfCounts = Record<PerfStatus | "unassessed", number>;
export interface PerformanceKpi extends StdSeriesKpi {
  categories: Record<"met" | "improved" | "not_improved" | "not_reported", RawPoint[]>;
  detail_years: number[];
}
// performance_detail_YYYY.json — every sub-indicator of one RAP year, values as published.
export interface PerfRow {
  sub_indicator: string | null; unit: string | null;
  target: string | number | null; result: string | number | null;
  status: PerfStatus | null; comment: string | null;
}
export interface PerfIndicator { code: string | null; indicator: string; rows: PerfRow[] }
export interface PerfObjective { objective: string | null; indicators: PerfIndicator[] }
export interface PerfGroup { programme_code: number | null; programme: string | null; objectives: PerfObjective[] } // code null = mission-level indicators
export interface PerfMission { mission: string; counts: PerfCounts; groups: PerfGroup[] }
export interface PerformanceDetail { year: number; source: string; last_updated: string; counts: PerfCounts; missions: PerfMission[] }
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
import type { Polarity } from "./format";
export type Unit = "percent" | "eur_bn" | "years" | "eur" | "ratio" | "mixed";
export type XKind = "year" | "month";
export interface ViewPoint { x: number | string; y: number; projection?: boolean }
export interface ViewSeries { id: string; label: string; role: "france" | "oecd" | "peer" | "secondary"; points: ViewPoint[] }
export interface SecondaryBlock { title: string; unit: Unit; series: ViewSeries[]; comparison?: ViewSeries; peers?: ViewSeries[]; note?: string }
export interface LatestStat { year: number | string; value: number; unit: Unit; yoy?: number }
export interface KpiView {
  slug: string;            // route slug, e.g. "overhead_rate"
  apiId: string;           // file/api id, e.g. "kpi_overhead_rate"
  title: string;           // French label (from registry)
  explainer: string;       // French explainer (from registry)
  unit: Unit;
  polarity: Polarity;      // whether a rise is good/bad/neutral (drives YoY color)
  xKind: XKind;
  series: ViewSeries[];        // primary chart series (france first)
  comparison?: ViewSeries;     // an average (6-country mean, EU27 or OECD — label says which); undefined when unavailable
  peers?: ViewSeries[];        // individual peer countries (role "peer"), fixed order
  secondary?: SecondaryBlock;  // e.g. debt (sustainability), life expectancy (outcomes)
  panels?: SecondaryBlock[];   // further detail charts below the secondary one (e.g. debt holders)
  drilldown?: { to: string; label: string }; // link to a dedicated detail page (e.g. performance indicators)
  latest?: LatestStat;
  source: string;              // from JSON (empty for monthly)
  methodology: string;         // from JSON (empty for monthly)
}
