import type { KpiView } from "../data/types";
import { fmtPercent, fmtEurBn, fmtYears, fmtRatio, fmtYoy, yoySentiment } from "../data/format";

export function StatCallout({ view }: { view: KpiView }) {
  if (!view.latest) return null;
  const { unit, value, year, yoy } = view.latest;
  const v = unit === "eur_bn" ? fmtEurBn(value) : unit === "years" ? fmtYears(value)
    : unit === "ratio" ? fmtRatio(value)
    : unit === "eur" ? new Intl.NumberFormat("fr-FR", { notation: "compact", style: "currency", currency: "EUR" }).format(value)
    : fmtPercent(value);
  const y = yoy != null ? fmtYoy(yoy, unit) : null;
  const sentiment = y ? yoySentiment(y.dir, view.polarity) : "neutral";
  return (
    <div className="stat-callout">
      <span className="stat-callout__value">{v}</span>
      <span className="stat-callout__year">en {year}</span>
      {y && <span className={`stat-callout__yoy yoy--${sentiment}`} data-dir={y.dir} data-sentiment={sentiment}>
        {y.dir === "up" ? "▲" : y.dir === "down" ? "▼" : "▬"} {y.text} sur un an</span>}
    </div>
  );
}
