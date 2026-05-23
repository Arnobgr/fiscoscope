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
