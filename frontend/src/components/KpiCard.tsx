import { Link } from "react-router-dom";
import type { KpiView } from "../data/types";
import { Sparkline } from "./Sparkline";
import { fmtPercent, fmtEurBn, fmtYears, fmtRatio, fmtYoy } from "../data/format";

function fmtValue(unit: KpiView["unit"], v: number): string {
  if (unit === "eur_bn") return fmtEurBn(v);
  if (unit === "years") return fmtYears(v);
  if (unit === "ratio") return fmtRatio(v);
  if (unit === "eur") return new Intl.NumberFormat("fr-FR", { notation: "compact", style: "currency", currency: "EUR" }).format(v);
  return fmtPercent(v);
}

export function KpiCard({ view }: { view: KpiView }) {
  const yoy = view.latest?.yoy != null ? fmtYoy(view.latest.yoy, view.latest.unit) : null;
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
      {view.latest && (
        <span className="kpi-card__asof">données jusqu’à {view.latest.year}</span>
      )}
      {hasOecd && <span className="kpi-card__badge">vs moyenne OCDE</span>}
    </Link>
  );
}
