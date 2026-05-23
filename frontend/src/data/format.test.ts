import { describe, it, expect } from "vitest";
import { fmtPercent, fmtEurBn, fmtYears, fmtNumber, fmtDateFr, fmtYoy } from "./format";

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
});
