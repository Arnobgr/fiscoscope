import type { ContextFacts } from "./types";
const MINUS = "−"; // fr typographic minus sign (Intl emits ASCII "-" on some ICU builds)

const nf = (min: number, max: number) =>
  new Intl.NumberFormat("fr-FR", { minimumFractionDigits: min, maximumFractionDigits: max });

// Format a number in fr-FR, normalizing the leading sign to U+2212.
const num = (v: number, min: number, max: number) => nf(min, max).format(v).replace("-", MINUS);

export function fmtPercent(v: number): string {
  return `${num(v, 2, 2)} %`;
}
export function fmtEurBn(v: number): string {
  return `${num(v, 1, 1)} Md€`;
}
export function fmtYears(v: number): string {
  return `${num(v, 1, 1)} ans`;
}
export function fmtRatio(v: number): string {
  return `${num(v, 1, 1)}×`;
}
export function fmtEurHab(v: number): string {
  return `${num(v, 0, 0)} €`;
}
export function fmtNumber(v: number): string {
  return num(v, 0, 0);
}
// Chart tooltip value for a KPI unit. "eur" series are raw euros → shown in Md€.
export function fmtValue(v: number, unit: string): string {
  switch (unit) {
    case "percent": return fmtPercent(v);
    case "eur_bn": return fmtEurBn(v);
    case "eur": return fmtEurBn(v / 1e9);
    case "eur_hab": return fmtEurHab(v);
    case "years": return fmtYears(v);
    case "ratio": return fmtRatio(v);
    default: return num(v, 0, 2);
  }
}
// Shorter variant for chart axis ticks.
export function fmtAxis(v: number, unit: string): string {
  switch (unit) {
    case "percent": return `${num(v, 0, 1)} %`;
    case "eur_bn": return `${num(v, 0, 0)} Md€`;
    case "eur": return `${num(v / 1e9, 0, 0)} Md€`;
    case "eur_hab": return Math.abs(v) >= 10000 ? `${num(v / 1000, 0, 1)} k€` : `${num(v, 0, 0)} €`;
    case "years": return `${num(v, 0, 0)} ans`;
    case "ratio": return `${num(v, 0, 1)}×`;
    default: return num(v, 0, 1);
  }
}
// Context sentence (roadmap 2.4): the first fact present among history, peers,
// change over 10 years. `balance` (public balances, negative = deficit) words
// the extremes as deficits so "highest" never reads as "largest deficit".
export function fmtContext(facts: ContextFacts | undefined, unit: string, balance?: { value: number }): string | undefined {
  if (!facts) return undefined;
  const deficit = balance && balance.value < 0;
  const extreme = (high: boolean) => !balance
    ? (high ? "la plus élevée" : "la plus basse")
    : deficit ? (high ? "le plus faible" : "le plus élevé") : (high ? "le plus élevé" : "le plus bas");
  const noun = !balance ? null : deficit ? "Déficit" : "Solde";
  const { history: h, peers: p, change_10y: c } = facts;
  if (h) {
    const since = h.record ? `depuis le début de la série (${h.since})` : `depuis ${h.since}`;
    if (!noun) return `Plus ${h.direction === "high" ? "haut" : "bas"} niveau ${since}.`;
    return `${noun} ${extreme(h.direction === "high")} ${since}.`;
  }
  if (p) return `${noun ?? "Valeur"} ${extreme(p.position === "highest")} des ${p.of} pays comparés en ${p.year}.`;
  if (c) {
    const span = `en dix ans (${c.from_year}–${c.from_year + 10})`;
    if (Math.abs(c.change) < 0.05) return `Quasiment inchangé ${span}.`;
    const sign = c.change > 0 ? "+" : "";
    if (deficit && balance.value - c.change < 0) { // a deficit both years: say which way it moved
      const pts = `${num(Math.abs(c.change), 1, 1)} ${Math.round(Math.abs(c.change) * 10) >= 20 ? "points" : "point"}`;
      return `Déficit ${c.change < 0 ? "plus élevé" : "plus faible"} de ${pts} qu’en ${c.from_year}.`;
    }
    const amount = unit === "eur_bn" ? fmtEurBn(c.change)
      : unit === "ratio" ? `${num(c.change, 1, 1)}×`
      : `${num(c.change, 1, 1)} ${Math.round(Math.abs(c.change) * 10) >= 20 ? "points" : "point"}`; // fr: plural from 2
    return `${sign}${amount} ${span}.`;
  }
  return undefined;
}

export function fmtDateFr(iso: string): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(iso));
}
export type YoyDir = "up" | "down" | "flat";
// `unit` "ratio" → YoY is a delta of multiples (×), shown without a "%" suffix;
// "eur_hab" → a delta in euros per inhabitant.
export function fmtYoy(v: number, unit?: string): { text: string; dir: YoyDir } {
  const dir: YoyDir = v > 0 ? "up" : v < 0 ? "down" : "flat";
  const sign = v > 0 ? "+" : ""; // negatives carry U+2212 via num()
  if (unit === "eur_hab") return { text: `${sign}${fmtEurHab(v)}`, dir };
  const suffix = unit === "ratio" ? "×" : " %";
  return { text: `${sign}${num(v, 1, 2)}${suffix}`, dir }; // 1–2 decimals (e.g. +1,2 / −0,41)
}

// Per-KPI direction of "better": for most ratios a rise is bad (overhead, debt
// service, niches…); for a few a rise is good (public balance);
// some are informational with no good/bad reading (outcomes, monthly tracking).
export type Polarity = "higher_good" | "higher_bad" | "neutral";
export type Sentiment = "good" | "bad" | "neutral";
// Map a raw YoY direction to a good/bad sentiment for coloring. The arrow still
// shows the real direction (▲/▼); only the color uses this sentiment.
export function yoySentiment(dir: YoyDir, polarity: Polarity): Sentiment {
  if (dir === "flat" || polarity === "neutral") return "neutral";
  const increaseIsGood = polarity === "higher_good";
  return (dir === "up") === increaseIsGood ? "good" : "bad";
}
