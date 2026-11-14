import { describe, it, expect } from "vitest";
import { fmtPercent, fmtEurBn, fmtEurHab, fmtYears, fmtRatio, fmtNumber, fmtDateFr, fmtYoy, yoySentiment, fmtValue, fmtAxis, fmtContext } from "./format";

const NB = " "; // narrow no-break space — fr-FR thousands grouping
const MIN = "−"; // U+2212 minus sign (not ASCII hyphen)

describe("french formatters", () => {
  it("formats percent with comma + space + sign-free", () => {
    expect(fmtPercent(5.79)).toBe("5,79 %");
    expect(fmtPercent(-8.93)).toBe(`${MIN}8,93 %`);
  });
  it("formats euro billions", () => {
    expect(fmtEurBn(81.7)).toBe("81,7 Md€");
  });
  it("formats years (life expectancy)", () => {
    expect(fmtYears(83)).toBe("83,0 ans");
  });
  it("formats a ratio as a multiple (×, not %)", () => {
    expect(fmtRatio(5.39)).toBe("5,4×");
    expect(fmtRatio(5.39)).not.toContain("%");
  });
  it("formats chart tooltip values by unit", () => {
    expect(fmtValue(21.537, "percent")).toBe("21,54 %");
    expect(fmtValue(5.391, "ratio")).toBe("5,4×");
    expect(fmtValue(81.73, "eur_bn")).toBe("81,7 Md€");
    expect(fmtValue(152_345_000_000, "eur")).toBe("152,3 Md€");
    expect(fmtValue(82.94, "years")).toBe("82,9 ans");
  });
  it("formats chart axis ticks by unit", () => {
    expect(fmtAxis(20, "percent")).toBe("20 %");
    expect(fmtAxis(-2.5, "percent")).toBe(`${MIN}2,5 %`);
    expect(fmtAxis(150_000_000_000, "eur")).toBe("150 Md€");
    expect(fmtAxis(4, "ratio")).toBe("4×");
  });
  it("formats plain numbers with fr grouping", () => {
    expect(fmtNumber(1456129)).toBe(`1${NB}456${NB}129`);
  });
  it("formats an ISO date in French", () => {
    expect(fmtDateFr("2026-05-21T10:03:39Z")).toBe("21 mai 2026");
  });
  it("formats YoY with arrow + signed percent", () => {
    expect(fmtYoy(-0.41)).toEqual({ text: `${MIN}0,41 %`, dir: "down" });
    expect(fmtYoy(1.2)).toEqual({ text: "+1,2 %", dir: "up" });
    expect(fmtYoy(0)).toEqual({ text: "0,0 %", dir: "flat" });
  });
  it("formats a ratio YoY with × instead of %", () => {
    expect(fmtYoy(0.12, "ratio")).toEqual({ text: "+0,12×", dir: "up" });
  });
  it("colors YoY by per-KPI polarity, not raw direction", () => {
    // higher_bad (overhead, debt service, niches…): a rise is bad, a fall is good
    expect(yoySentiment("up", "higher_bad")).toBe("bad");
    expect(yoySentiment("down", "higher_bad")).toBe("good");
    // higher_good (public balance): a rise is good
    expect(yoySentiment("up", "higher_good")).toBe("good");
    expect(yoySentiment("down", "higher_good")).toBe("bad");
    // neutral (outcomes, monthly) and flat are always neutral
    expect(yoySentiment("up", "neutral")).toBe("neutral");
    expect(yoySentiment("flat", "higher_bad")).toBe("neutral");
  });
});

describe("euros per inhabitant (roadmap 2.1)", () => {
  it("formats whole euros, with a k€ axis for large values", () => {
    expect(fmtEurHab(50170.4)).toBe(`50${NB}170 €`);
    expect(fmtValue(-2198, "eur_hab")).toBe(`${MIN}2${NB}198 €`);
    expect(fmtAxis(52000, "eur_hab")).toBe("52 k€");
    expect(fmtAxis(950, "eur_hab")).toBe("950 €");
  });
  it("shows a year-on-year change in euros, not in %", () => {
    expect(fmtYoy(68, "eur_hab")).toEqual({ text: "+68 €", dir: "up" });
    expect(fmtYoy(-120, "eur_hab").text).toBe(`${MIN}120 €`);
  });
});

describe("fmtContext (roadmap 2.4)", () => {
  const change = { change_10y: { from_year: 2015, change: -1.03 } };
  it("prefers history, then peers, then the 10-year change", () => {
    const all = { history: { direction: "high" as const, since: 2013, record: false },
      peers: { year: 2024, position: "highest" as const, of: 7 }, ...change };
    expect(fmtContext(all, "percent")).toBe("Plus haut niveau depuis 2013.");
    expect(fmtContext({ peers: all.peers, ...change }, "percent")).toBe("Valeur la plus élevée des 7 pays comparés en 2024.");
    expect(fmtContext(change, "percent")).toBe(`${MIN}1,0 point en dix ans (2015–2025).`);
    expect(fmtContext({}, "percent")).toBeUndefined();
    expect(fmtContext(undefined, "percent")).toBeUndefined();
  });
  it("names a record with the first year of the series", () => {
    expect(fmtContext({ history: { direction: "low", since: 1995, record: true } }, "percent"))
      .toBe("Plus bas niveau depuis le début de la série (1995).");
  });
  it("words the extremes of a negative balance as deficits", () => {
    const value = -4.4;
    expect(fmtContext({ history: { direction: "high", since: 2019, record: false } }, "percent", { value }))
      .toBe("Déficit le plus faible depuis 2019.");
    expect(fmtContext({ peers: { year: 2024, position: "lowest", of: 7 } }, "percent", { value }))
      .toBe("Déficit le plus élevé des 7 pays comparés en 2024.");
    expect(fmtContext({ history: { direction: "high", since: 2000, record: false } }, "percent", { value: 0.5 }))
      .toBe("Solde le plus élevé depuis 2000.");
    expect(fmtContext({ change_10y: { from_year: 2015, change: -1.18 } }, "percent", { value: -5.07 }))
      .toBe("Déficit plus élevé de 1,2 point qu’en 2015.");
    expect(fmtContext({ change_10y: { from_year: 2015, change: 2.5 } }, "percent", { value: -1 }))
      .toBe("Déficit plus faible de 2,5 points qu’en 2015.");
    // a surplus 10 years ago: no deficit wording
    expect(fmtContext({ change_10y: { from_year: 2015, change: -1.5 } }, "percent", { value: -1 }))
      .toBe(`${MIN}1,5 point en dix ans (2015–2025).`);
  });
  it("formats the 10-year change in the KPI's unit", () => {
    expect(fmtContext({ change_10y: { from_year: 2014, change: 12.27 } }, "eur_bn")).toBe("+12,3 Md€ en dix ans (2014–2024).");
    expect(fmtContext({ change_10y: { from_year: 2014, change: 18.7 } }, "percent")).toBe("+18,7 points en dix ans (2014–2024).");
    expect(fmtContext({ change_10y: { from_year: 2014, change: -0.29 } }, "ratio")).toBe(`${MIN}0,3× en dix ans (2014–2024).`);
    expect(fmtContext({ change_10y: { from_year: 2014, change: 0.04 } }, "percent")).toBe("Quasiment inchangé en dix ans (2014–2024).");
  });
});
