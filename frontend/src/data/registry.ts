import type { KpiView, Unit } from "./types";
import {
  type AdaptBase, adaptStandard, adaptSustainability, adaptOutcomes,
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
    "Poids des fonctions support et régaliennes de base (services publics généraux, défense, ordre et sécurité publics) rapporté aux recettes : la part des recettes absorbée par le socle de fonctionnement de l’État.", adaptStandard),
  e("productive_spend", "efficacite", "percent", "Part des dépenses productives",
    "Part des dépenses publiques consacrée aux fonctions productives (affaires économiques, environnement, logement) dans le total des dépenses par fonction.", adaptStandard),
  e("wage_ratio", "efficacite", "percent", "Masse salariale public / privé",
    "Masse salariale publique rapportée à la masse salariale privée : mesure le poids relatif de l’emploi public dans la rémunération du pays.", adaptStandard),
  e("sustainability", "soutenabilite", "percent", "Déficit public & dette",
    "Solde public (déficit ou excédent) en % du PIB, accompagné de la dette publique au sens de Maastricht. Indique si les finances publiques sont soutenables dans la durée.", adaptSustainability),
  e("debt_service", "soutenabilite", "percent", "Charge de la dette",
    "Intérêts de la dette publique rapportés aux recettes : la part des recettes absorbée par le seul service de la dette, avant toute dépense.", adaptStandard),
  e("pension_investment", "soutenabilite", "ratio", "Protection sociale vs investissement",
    "Dépenses de protection sociale (retraites, chômage, famille, maladie, etc.) rapportées à l’investissement public : combien de fois l’État dépense en transferts sociaux ce qu’il investit pour l’avenir.", adaptStandard),
  e("outcomes", "depenses", "mixed", "Dépenses de santé vs espérance de vie",
    "Dépenses publiques de santé (% du PIB) et espérance de vie à la naissance, présentées comme deux séries parallèles. L’espérance de vie dépend de l’ensemble du système de santé et de facteurs hors santé : à chacun d’apprécier comment les résultats accompagnent la dépense.", adaptOutcomes),
  e("tax_expenditure", "depenses", "eur_bn", "Dépenses fiscales (niches)",
    "Coût des dépenses fiscales (« niches ») — recettes auxquelles l’État renonce via exonérations, taux réduits et crédits d’impôt — d’après l’estimation GTED. Le chiffrage officiel (PLF, Voies et Moyens tome II) retient un périmètre plus large et un total plus élevé (de l’ordre de 80–90 Md€ ces dernières années). Les deux dernières années sont des prévisions.", adaptTaxExpenditure),
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
