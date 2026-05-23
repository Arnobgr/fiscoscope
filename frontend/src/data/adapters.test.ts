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

import { adaptOutcomes, adaptTaxExpenditure, adaptMonthly } from "./adapters";
import outcomes from "../fixtures/kpi_outcomes.json";
import taxexp from "../fixtures/kpi_tax_expenditure.json";
import monthly from "../fixtures/kpi_monthly_execution.json";

describe("adaptOutcomes", () => {
  const v = adaptOutcomes(outcomes as any,
    { slug: "outcomes", title: "T", explainer: "E", unit: "mixed" });
  it("primary = health spend %GDP, secondary = life expectancy", () => {
    expect(v.series[0].points[0]).toEqual({ x: 1995, y: 7.13 });
    expect(v.secondary?.unit).toBe("years");
    expect(v.secondary?.series[0].points.length).toBeGreaterThan(0);
  });
  it("no OECD comparison", () => expect(v.comparison).toBeUndefined());
  it("flags the 2020 source break", () => expect(v.hasBreak2020).toBe(true));
});

describe("adaptTaxExpenditure", () => {
  const v = adaptTaxExpenditure(taxexp as any,
    { slug: "tax_expenditure", title: "T", explainer: "E", unit: "eur_bn" });
  it("plots total_cost_eur_bn and marks projections", () => {
    expect(v.series[0].points[0]).toEqual({ x: 1999, y: 52.95, projection: false });
    expect(v.series[0].points.some((p) => p.projection === true)).toBe(true);
  });
});

describe("adaptMonthly", () => {
  const v = adaptMonthly(monthly as any,
    { slug: "monthly_execution", title: "T", explainer: "E", unit: "eur" });
  it("uses a month x-axis with revenue/spending series", () => {
    expect(v.xKind).toBe("month");
    const ids = v.series.map((s) => s.id);
    expect(ids).toContain("revenues");
    expect(ids).toContain("spending");
    expect(v.series[0].points[0].x).toBe("2026-01");
  });
});
