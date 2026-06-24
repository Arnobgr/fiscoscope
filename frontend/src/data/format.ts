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
export function fmtNumber(v: number): string {
  return num(v, 0, 0);
}
export function fmtDateFr(iso: string): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(iso));
}
export type YoyDir = "up" | "down" | "flat";
// `unit` "ratio" → YoY is a delta of multiples (×), shown without a "%" suffix.
export function fmtYoy(v: number, unit?: string): { text: string; dir: YoyDir } {
  const dir: YoyDir = v > 0 ? "up" : v < 0 ? "down" : "flat";
  const sign = v > 0 ? "+" : ""; // negatives carry U+2212 via num()
  const suffix = unit === "ratio" ? "×" : " %";
  return { text: `${sign}${num(v, 1, 2)}${suffix}`, dir }; // 1–2 decimals (e.g. +1,2 / −0,41)
}

// Per-KPI direction of "better": for most ratios a rise is bad (overhead, debt
// service, niches…); for a few a rise is good (productive spend, public balance);
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
