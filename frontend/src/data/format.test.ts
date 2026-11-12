import { describe, it, expect } from "vitest";
import { fmtPercent, fmtEurBn, fmtEurHab, fmtYears, fmtRatio, fmtNumber, fmtDateFr, fmtYoy, yoySentiment, fmtValue, fmtAxis } from "./format";

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
