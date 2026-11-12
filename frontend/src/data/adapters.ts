import type {
  KpiView, ViewSeries, Unit, RawPoint, StdSeriesKpi, SustainabilityKpi,
  OutcomesKpi, TaxExpenditureKpi, MonthlyKpi, PensionsKpi, DeficitSubsectorKpi,
  PerformanceKpi, PerfStatus, PerCapitaRaw, PerCapitaView, SecondaryBlock,
} from "./types";
import type { Polarity } from "./format";

export interface AdaptBase { slug: string; title: string; explainer: string; unit: Unit; polarity: Polarity }

// Averages a payload may carry, with their on-screen labels. OECD_AVG is the
// unweighted mean of the 6 peers (never an OECD average); EU27_AVG and OECD_REP
// (Revenue Statistics "OECD average") are published by Eurostat / the OECD.
export const AVERAGES: [string, string][] = [
  ["OECD_AVG", "Moyenne des 6 pays"], ["EU27_AVG", "Moyenne UE à 27"], ["OECD_REP", "Moyenne OCDE"],
];
const PEERS: [string, string][] = [
  ["DEU", "Allemagne"], ["ESP", "Espagne"], ["ITA", "Italie"],
  ["NLD", "Pays-Bas"], ["GBR", "Royaume-Uni"], ["SWE", "Suède"],
];

function yearPoints(rows: RawPoint[]): { x: number; y: number }[] {
  return rows.map((r) => ({ x: r.year, y: r.value }));
}
function franceSeries(rows: RawPoint[]): ViewSeries {
  return { id: "france", label: "France", role: "france", points: yearPoints(rows) };
}
function averageSeries(peers?: Record<string, RawPoint[]>): ViewSeries | undefined {
  const hit = AVERAGES.find(([key]) => peers?.[key]?.length);
  if (!hit) return undefined;
  const [key, label] = hit;
  return { id: key, label, role: "oecd", points: yearPoints(peers![key]) };
}
function peerSeries(peers?: Record<string, RawPoint[]>): ViewSeries[] {
  return PEERS.filter(([iso]) => peers?.[iso]?.length)
    .map(([iso, label]) => ({ id: iso, label, role: "peer" as const, points: yearPoints(peers![iso]) }));
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

// "€ par habitant" view (roadmap 2.1): France only, constant euros of base_year.
// Each block lists [per_capita series key, line label]; the first line of the
// first block drives the headline figure.
type PerCapitaBlocks = { title: string; lines: [string, string][] }[];
export function perCapitaView(pc: PerCapitaRaw | undefined, ratioLabel: string, blocks: PerCapitaBlocks): PerCapitaView | undefined {
  if (!pc) return undefined;
  const out: SecondaryBlock[] = blocks.map((block, bi) => ({
    title: `${block.title}, en euros ${pc.base_year}`, unit: "eur_hab" as const,
    note: bi === 0
      ? `France seule : des euros par habitant ne se comparent pas d’un pays à l’autre sans corriger les écarts de prix ; la comparaison internationale se fait sur la vue « ${ratioLabel} ». Montants divisés par la population moyenne de l’année et convertis en euros ${pc.base_year} avec l’indice des prix à la consommation de l’INSEE, depuis 1996.`
      : undefined,
    series: block.lines.filter(([key]) => pc.series[key]?.length).map(([key, label], i) => ({
      id: key, label, role: i === 0 ? "france" as const : "secondary" as const, points: yearPoints(pc.series[key]),
    })),
  })).filter((block) => block.series.length > 0);
  const head = pc.series[blocks[0]?.lines[0]?.[0]] ?? [];
  if (out.length === 0 || head.length === 0) return undefined;
  return { label: `€ par habitant (euros ${pc.base_year})`, ratioLabel, blocks: out, latest: latestFrom(head, "eur_hab") };
}
export const withPerCapita = <R extends { per_capita?: PerCapitaRaw }>(
  adapt: (raw: R, b: AdaptBase) => KpiView, ratioLabel: string, blocks: PerCapitaBlocks,
) => (raw: R, b: AdaptBase): KpiView => ({ ...adapt(raw, b), perCapita: perCapitaView(raw.per_capita, ratioLabel, blocks) });

export function adaptStandard(raw: StdSeriesKpi, b: AdaptBase): KpiView {
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer, polarity: b.polarity,
    unit: b.unit, xKind: "year",
    series: [franceSeries(raw.france)],
    comparison: averageSeries(raw.peers),
    peers: peerSeries(raw.peers),
    latest: latestFrom(raw.france, b.unit, raw.latest),
    ...meta(raw),
  };
}

export function adaptSustainability(raw: SustainabilityKpi, b: AdaptBase): KpiView {
  const deficitPeers = (raw.peers as any)?.deficit as Record<string, RawPoint[]> | undefined;
  const debtPeers = (raw.peers as any)?.debt as Record<string, RawPoint[]> | undefined;
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer, polarity: b.polarity,
    unit: "percent", xKind: "year",
    series: [franceSeries(raw.france)],
    comparison: averageSeries(deficitPeers),
    peers: peerSeries(deficitPeers),
    secondary: {
      title: "Dette publique (Maastricht, % du PIB)", unit: "percent",
      series: [franceSeries(raw.debt.france)],
      comparison: averageSeries(debtPeers),
      peers: peerSeries(debtPeers),
    },
    panels: raw.debt_holders ? [{
      title: "Qui détient la dette ? (% du PIB)", unit: "percent",
      note: "Ventilation publiée par Eurostat depuis 2020. « Autres résidents » : banques, assurances, fonds, ménages…",
      series: [
        { id: "non_residents", label: "Non-résidents", role: "france", points: yearPoints(raw.debt_holders.france.non_residents) },
        { id: "central_bank", label: "Banque de France", role: "secondary", points: yearPoints(raw.debt_holders.france.central_bank) },
        { id: "other_residents", label: "Autres résidents", role: "secondary", points: yearPoints(raw.debt_holders.france.other_residents) },
      ],
    }] : undefined,
    perCapita: perCapitaView(raw.per_capita, "% du PIB", [
      { title: "Solde public par habitant", lines: [["deficit", "France"]] },
      { title: "Dette publique par habitant", lines: [["debt", "France"]] },
    ]),
    latest: latestFrom(raw.france, "percent", raw.latest),
    ...meta(raw),
  };
}

export function adaptPensions(raw: PensionsKpi, b: AdaptBase): KpiView {
  return {
    ...adaptStandard(raw, b),
    secondary: {
      title: "Dépenses de vieillesse (% du PIB)", unit: "percent",
      series: [franceSeries(raw.pct_gdp.france)],
      comparison: averageSeries(raw.pct_gdp.peers),
      peers: peerSeries(raw.pct_gdp.peers),
    },
    perCapita: perCapitaView(raw.per_capita, "% de la dépense et du PIB", [
      { title: "Dépenses de vieillesse par habitant", lines: [["france", "France"]] },
    ]),
  };
}

const SUBSECTORS: [keyof DeficitSubsectorKpi["subsectors"], string][] = [
  ["central", "État et organismes centraux"], ["local", "Collectivités locales"],
  ["social_security", "Sécurité sociale"], ["total", "Ensemble des administrations"],
];
export function adaptDeficitSubsector(raw: DeficitSubsectorKpi, b: AdaptBase): KpiView {
  const lines = (field: "pct_gdp" | "eur_bn"): ViewSeries[] => SUBSECTORS.map(([key, label], i) => ({
    id: key, label, role: i === 0 ? "france" : "secondary", points: yearPoints(raw.subsectors[key][field]),
  }));
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer, polarity: b.polarity,
    unit: "percent", xKind: "year",
    series: lines("pct_gdp"),
    secondary: { title: "En milliards d’euros courants", unit: "eur_bn", series: lines("eur_bn") },
    perCapita: perCapitaView(raw.per_capita, "% du PIB", [{ title: "Solde par habitant", lines: SUBSECTORS }]),
    latest: latestFrom(raw.france, "percent", raw.latest),
    ...meta(raw),
  };
}

// Attainment categories of the State's performance indicators, in the ministry's
// own terms. Shared by the KPI chart and the drill-down page.
export const PERFORMANCE_STATUS: Record<PerfStatus | "unassessed", string> = {
  met: "Cible atteinte",
  improved: "Cible non atteinte, en amélioration",
  not_improved: "Cible non atteinte, sans amélioration",
  not_reported: "Résultat non renseigné",
  not_retained: "Indicateur non retenu",
  unassessed: "Non évalué",
};
const PERFORMANCE_LINES = ["met", "improved", "not_improved", "not_reported"] as const;
export function adaptPerformance(raw: PerformanceKpi, b: AdaptBase): KpiView {
  const years = raw.detail_years;
  return {
    ...adaptStandard(raw, b),
    series: [{ id: "france", label: PERFORMANCE_STATUS.met, role: "france", points: yearPoints(raw.france) }],
    secondary: {
      title: "Répartition des indicateurs (% du total)", unit: "percent",
      note: "Les indicateurs « non retenus » par le ministère sont exclus du total.",
      series: PERFORMANCE_LINES.map((key, i) => ({
        id: key, label: PERFORMANCE_STATUS[key], role: i === 0 ? "france" as const : "secondary" as const,
        points: yearPoints(raw.categories[key]),
      })),
    },
    drilldown: years.length
      ? { to: "/performance", label: `Voir chaque indicateur : cible, résultat, mission par mission (${years[0]}–${years[years.length - 1]})` }
      : undefined,
  };
}

export function adaptOutcomes(raw: OutcomesKpi, b: AdaptBase): KpiView {
  const spend = raw.health.spend_pct_gdp;
  const life = raw.health.life_expectancy_years;
  const lifeBlock: SecondaryBlock = {
    title: "Espérance de vie à la naissance", unit: "years",
    series: [{ id: "life_exp", label: "Espérance de vie", role: "secondary", points: yearPoints(life) }],
  };
  const perCapita = perCapitaView(raw.per_capita, "% du PIB", [
    { title: "Dépenses publiques de santé par habitant", lines: [["france", "France"]] },
  ]);
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer, polarity: b.polarity,
    unit: "percent", xKind: "year",
    series: [{ id: "health_spend", label: "Dépenses de santé (% du PIB)", role: "france", points: yearPoints(spend) }],
    secondary: lifeBlock,
    // Life expectancy stays next to the spending in either view.
    perCapita: perCapita && { ...perCapita, blocks: [...perCapita.blocks, lifeBlock] },
    latest: latestFrom(spend, "percent"),
    ...meta(raw),
  };
}

export function adaptTaxExpenditure(raw: TaxExpenditureKpi, b: AdaptBase): KpiView {
  const points = raw.france.map((r) => ({ x: r.year, y: r.total_cost_eur_bn, projection: r.projection }));
  const rows = raw.france;
  const last = rows[rows.length - 1];
  const prev = rows[rows.length - 2];
  const perCapita = perCapitaView(raw.per_capita, "Md€ courants", [
    { title: "Coût des dépenses fiscales par habitant", lines: [["france", "France"]] },
  ]);
  const projected = new Set(rows.filter((r) => r.projection).map((r) => r.year));
  if (perCapita) {
    perCapita.blocks[0].series[0].points = perCapita.blocks[0].series[0].points
      .map((p) => ({ ...p, projection: projected.has(p.x as number) }));
  }
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer, polarity: b.polarity,
    unit: "eur_bn", xKind: "year",
    series: [{ id: "tax_cost", label: "Coût des dépenses fiscales", role: "france", points }],
    perCapita,
    latest: last
      ? { year: last.year, value: last.total_cost_eur_bn, unit: "eur_bn",
          yoy: last.yoy_change_pct ?? (prev ? ((last.total_cost_eur_bn - prev.total_cost_eur_bn) / prev.total_cost_eur_bn) * 100 : undefined) }
      : undefined,
    ...meta(raw),
  };
}

export function adaptMonthly(raw: MonthlyKpi, b: AdaptBase): KpiView {
  const months = raw.revenues.months;
  const toPoints = (vals: number[]) => months.map((m, i) => ({ x: m, y: vals[i] }));
  const lastIdx = months.length - 1;
  return {
    slug: b.slug, apiId: `kpi_${b.slug}`, title: b.title, explainer: b.explainer, polarity: b.polarity,
    unit: "eur", xKind: "month",
    series: [
      { id: "revenues", label: "Recettes (cumul, €)", role: "france", points: toPoints(raw.revenues.total as number[]) },
      { id: "spending", label: "Dépenses (cumul, €)", role: "secondary", points: toPoints(raw.spending.total as number[]) },
    ],
    latest: { year: raw.last_month, value: (raw.balance.cumulative as number[])[lastIdx], unit: "eur",
              yoy: raw.yoy.revenue_change_pct },
    source: "", methodology: "",
  };
}
