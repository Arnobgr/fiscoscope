import { describe, it, expect } from "vitest";
import { adaptStandard, adaptSustainability } from "./adapters";
import overhead from "../fixtures/kpi_overhead_rate.json";
import sustainability from "../fixtures/kpi_sustainability.json";

const base = { slug: "overhead_rate", title: "T", explainer: "E", unit: "percent" as const };

describe("adaptStandard", () => {
  const v = adaptStandard(overhead as any, base);
  it("maps france series first, role france", () => {
    expect(v.series[0].role).toBe("france");
    expect(v.series[0].points[0]).toEqual({ x: 1995, y: 24.11 });
  });
  it("exposes OECD_AVG as comparison and ignores the 6 countries", () => {
    expect(v.comparison?.role).toBe("oecd");
    expect(v.comparison?.points.length).toBeGreaterThan(0);
  });
  it("derives latest with yoy", () => {
    expect(v.latest?.unit).toBe("percent");
    expect(typeof v.latest?.yoy).toBe("number");
  });
  it("xKind is year", () => expect(v.xKind).toBe("year"));
});

describe("adaptSustainability", () => {
  const v = adaptSustainability(sustainability as any,
    { slug: "sustainability", title: "T", explainer: "E", unit: "percent" });
  it("primary = deficit, comparison = OECD_AVG deficit", () => {
    expect(v.series[0].points.find((p) => p.x === 2024)?.y).toBe(-5.79);
    expect(v.comparison?.role).toBe("oecd");
  });
  it("secondary = debt with its own OECD comparison", () => {
    expect(v.secondary?.title).toMatch(/dette/i);
    expect(v.secondary?.series[0].points.find((p) => p.x === 2024)?.y).toBe(112.6);
    expect(v.secondary?.comparison?.points.length).toBeGreaterThan(0);
  });
});
