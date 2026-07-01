import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { KpiView } from "../data/types";
import { Sparkline } from "./Sparkline";
import { fmtPercent, fmtEurBn, fmtYears, fmtRatio, fmtYoy, yoySentiment } from "../data/format";

function fmtValue(unit: KpiView["unit"], v: number): string {
  if (unit === "eur_bn") return fmtEurBn(v);
  if (unit === "years") return fmtYears(v);
  if (unit === "ratio") return fmtRatio(v);
  if (unit === "eur") return new Intl.NumberFormat("fr-FR", { notation: "compact", style: "currency", currency: "EUR" }).format(v);
  return fmtPercent(v);
}

export function KpiCard({ view, index = 0 }: { view: KpiView; index?: number }) {
  const yoy = view.latest?.yoy != null ? fmtYoy(view.latest.yoy, view.latest.unit) : null;
  const sentiment = yoy ? yoySentiment(yoy.dir, view.polarity) : "neutral";
  const hasOecd = !!view.comparison;
  const spark = view.series[0];
  return (
    <Link to={`/kpi/${view.slug}`} className="kpi-card" style={{ "--i": index } as CSSProperties}>
      <h3 className="kpi-card__title">{view.title}</h3>
      <div className="kpi-card__figure">
        {view.latest && (
          <span data-testid="kpi-latest" className="kpi-card__value">
            {fmtValue(view.latest.unit, view.latest.value)}
          </span>
        )}
        {yoy && (
          <span data-testid="kpi-yoy" data-dir={yoy.dir} data-sentiment={sentiment} className={`kpi-card__yoy yoy--${sentiment}`}>
            <span className="kpi-card__yoy-glyph" aria-hidden="true">
              {yoy.dir === "up" ? "▲" : yoy.dir === "down" ? "▼" : "▬"}
            </span>
            {yoy.text}
            {sentiment !== "neutral" && (
              <span className="sr-only">
                {sentiment === "good" ? " (évolution favorable)" : " (évolution défavorable)"}
              </span>
            )}
          </span>
        )}
      </div>
      {spark?.points.length ? <Sparkline series={spark} /> : null}
      {view.latest && (
        <span className="kpi-card__asof">données jusqu’à {view.latest.year}</span>
      )}
      {hasOecd && <span className="kpi-card__badge">vs moyenne OCDE</span>}
    </Link>
  );
}

export function KpiCardSkeleton() {
  return (
    <div className="kpi-card kpi-card--skeleton" aria-hidden="true">
      <div className="skeleton-line skeleton-line--title" />
      <div className="skeleton-line skeleton-line--value" />
      <div className="skeleton-line skeleton-line--spark" />
      <div className="skeleton-line skeleton-line--meta" />
    </div>
  );
}

export function KpiCardError({ title, onRetry, index = 0 }: { title: string; onRetry: () => void; index?: number }) {
  return (
    <div className="kpi-card kpi-card--error" style={{ "--i": index } as CSSProperties}>
      <h3 className="kpi-card__title">{title}</h3>
      <p className="kpi-card__error-text">Données momentanément indisponibles.</p>
      <button type="button" className="link-button" onClick={onRetry}>Réessayer</button>
    </div>
  );
}
