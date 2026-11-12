import { describe, it, expect } from "vitest";
import { adaptStandard, adaptSustainability, perCapitaView, withPerCapita } from "./adapters";
import overhead from "../fixtures/kpi_overhead_rate.json";
import sustainability from "../fixtures/kpi_sustainability.json";
import debtService from "../fixtures/kpi_debt_service.json";

const base = { slug: "overhead_rate", title: "T", explainer: "E", unit: "percent" as const, polarity: "higher_bad" as const };

describe("adaptStandard", () => {
  const v = adaptStandard(overhead as any, base);
  it("maps france series first, role france", () => {
    expect(v.series[0].role).toBe("france");
    expect(v.series[0].points[0]).toEqual({ x: 1995, y: 24.11 });
  });
  it("exposes OECD_AVG as comparison, labelled as the 6-country mean", () => {
    expect(v.comparison).toMatchObject({ id: "OECD_AVG", label: "Moyenne des 6 pays", role: "oecd" });
    expect(v.comparison?.points.length).toBeGreaterThan(0);
  });
  it("exposes the 6 peer countries in a fixed order with French labels", () => {
    expect(v.peers?.map((p) => p.id)).toEqual(["DEU", "ESP", "ITA", "NLD", "GBR", "SWE"]);
    expect(v.peers?.[0]).toMatchObject({ label: "Allemagne", role: "peer" });
    expect(v.peers?.every((p) => p.points.length > 0)).toBe(true);
  });
  it("derives latest with yoy", () => {
    expect(v.latest?.unit).toBe("percent");
    expect(typeof v.latest?.yoy).toBe("number");
  });
  it("xKind is year", () => expect(v.xKind).toBe("year"));
});

describe("adaptSustainability", () => {
  const v = adaptSustainability(sustainability as any,
    { slug: "sustainability", title: "T", explainer: "E", unit: "percent", polarity: "higher_good" });
  it("primary = deficit, comparison = OECD_AVG deficit", () => {
    expect(v.series[0].points.find((p) => p.x === 2024)?.y).toBe(-5.76);
    expect(v.comparison?.role).toBe("oecd");
  });
  it("secondary = debt with its own OECD comparison", () => {
    expect(v.secondary?.title).toMatch(/dette/i);
    expect(v.secondary?.series[0].points.find((p) => p.x === 2024)?.y).toBe(112.6);
    expect(v.secondary?.comparison?.points.length).toBeGreaterThan(0);
  });
  it("exposes peers for both deficit and debt", () => {
    expect(v.peers).toHaveLength(6);
    expect(v.secondary?.peers).toHaveLength(6);
  });
});

import { adaptOutcomes, adaptTaxExpenditure, adaptMonthly } from "./adapters";
import outcomes from "../fixtures/kpi_outcomes.json";
import taxexp from "../fixtures/kpi_tax_expenditure.json";
import monthly from "../fixtures/kpi_monthly_execution.json";

describe("adaptOutcomes", () => {
  const v = adaptOutcomes(outcomes as any,
    { slug: "outcomes", title: "T", explainer: "E", unit: "mixed", polarity: "neutral" });
  it("primary = health spend %GDP, secondary = life expectancy", () => {
    expect(v.series[0].points[0]).toEqual({ x: 1995, y: 6.9 });
    expect(v.secondary?.unit).toBe("years");
    expect(v.secondary?.series[0].points.length).toBeGreaterThan(0);
  });
  it("no OECD comparison", () => expect(v.comparison).toBeUndefined());
  it("no peers", () => expect(v.peers).toBeUndefined());
});

describe("adaptTaxExpenditure", () => {
  const v = adaptTaxExpenditure(taxexp as any,
    { slug: "tax_expenditure", title: "T", explainer: "E", unit: "eur_bn", polarity: "higher_bad" });
  it("plots total_cost_eur_bn and marks projections", () => {
    expect(v.series[0].points[0]).toEqual({ x: 1999, y: 52.95, projection: false });
    expect(v.series[0].points.some((p) => p.projection === true)).toBe(true);
  });
});

describe("adaptMonthly", () => {
  const v = adaptMonthly(monthly as any,
    { slug: "monthly_execution", title: "T", explainer: "E", unit: "eur", polarity: "neutral" });
  it("uses a month x-axis with revenue/spending series", () => {
    expect(v.xKind).toBe("month");
    const ids = v.series.map((s) => s.id);
    expect(ids).toContain("revenues");
    expect(ids).toContain("spending");
    expect(v.series[0].points[0].x).toBe("2026-01");
  });
});

import { adaptPensions, adaptDeficitSubsector } from "./adapters";
import adminOverhead from "../fixtures/kpi_admin_overhead.json";
import pensions from "../fixtures/kpi_pensions.json";
import deficitSubsector from "../fixtures/kpi_deficit_subsector.json";
import type { StdSeriesKpi, PensionsKpi, DeficitSubsectorKpi, SustainabilityKpi } from "./types";

const deficitRaw = deficitSubsector as unknown as DeficitSubsectorKpi;

describe("Eurostat-based KPIs", () => {
  it("label the EU27 aggregate, and have 5 peers (no UK)", () => {
    const v = adaptStandard(adminOverhead as unknown as StdSeriesKpi, { ...base, slug: "admin_overhead" });
    expect(v.comparison).toMatchObject({ id: "EU27_AVG", label: "Moyenne UE à 27", role: "oecd" });
    expect(v.peers?.map((p) => p.id)).toEqual(["DEU", "ESP", "ITA", "NLD", "SWE"]);
  });
  it("pensions: share of spending first, % of GDP as secondary with its own peers", () => {
    const v = adaptPensions(pensions as unknown as PensionsKpi,
      { slug: "pensions", title: "T", explainer: "E", unit: "percent", polarity: "neutral" });
    expect(v.series[0].role).toBe("france");
    expect(v.secondary?.title).toMatch(/PIB/);
    expect(v.secondary?.comparison?.id).toBe("EU27_AVG");
    expect(v.secondary?.peers).toHaveLength(5);
  });
  it("deficit by sub-sector: State first, then local, social security and total, in % and Md€", () => {
    const v = adaptDeficitSubsector(deficitRaw,
      { slug: "deficit_subsector", title: "T", explainer: "E", unit: "percent", polarity: "higher_good" });
    expect(v.series.map((s) => s.id)).toEqual(["central", "local", "social_security", "total"]);
    expect(v.series[0].role).toBe("france");
    expect(v.latest?.value).toBe(deficitRaw.latest?.value);
    expect(v.secondary?.unit).toBe("eur_bn");
    expect(v.secondary?.series).toHaveLength(4);
    expect(v.comparison).toBeUndefined();
  });
  it("sustainability: debt-holders panel with three series", () => {
    const v = adaptSustainability(sustainability as unknown as SustainabilityKpi,
      { slug: "sustainability", title: "T", explainer: "E", unit: "percent", polarity: "higher_good" });
    expect(v.panels?.[0].series.map((s) => s.id)).toEqual(["non_residents", "central_bank", "other_residents"]);
    expect(v.panels?.[0].note).toMatch(/2020/);
  });
});

import taxBurden from "../fixtures/kpi_tax_burden.json";
import publicEmployment from "../fixtures/kpi_public_employment.json";

describe("OECD-based KPIs (roadmap 1.5, 1.7)", () => {
  it("tax burden: OECD_REP labelled as the OECD average, 6 peers incl. UK", () => {
    const v = adaptStandard(taxBurden as unknown as StdSeriesKpi, { ...base, slug: "tax_burden" });
    expect(v.comparison).toMatchObject({ id: "OECD_REP", label: "Moyenne OCDE" });
    expect(v.peers).toHaveLength(6);
  });
  it("public employment: 6 peers, no average", () => {
    const v = adaptStandard(publicEmployment as unknown as StdSeriesKpi, { ...base, slug: "public_employment" });
    expect(v.comparison).toBeUndefined();
    expect(v.peers?.map((p) => p.id)).toContain("GBR");
  });
});

describe("€ par habitant view (roadmap 2.1)", () => {
  it("builds a France-only block in constant euros with its own headline figure", () => {
    const pc = adaptPensions(pensions as unknown as PensionsKpi, { ...base, slug: "pensions" }).perCapita!;
    expect(pc.label).toBe("€ par habitant (euros 2025)");
    expect(pc.ratioLabel).toBe("% de la dépense et du PIB");
    expect(pc.blocks).toHaveLength(1);
    expect(pc.blocks[0]).toMatchObject({ title: "Dépenses de vieillesse par habitant, en euros 2025", unit: "eur_hab" });
    expect(pc.blocks[0].comparison).toBeUndefined();
    expect(pc.blocks[0].peers).toBeUndefined();
    expect(pc.blocks[0].note).toMatch(/^France seule/);
    expect(pc.blocks[0].series[0].points[0].x).toBe(1996);
    expect(pc.latest?.unit).toBe("eur_hab");
    expect(pc.latest?.value).toBe(pensions.per_capita.series.france.at(-1)!.value);
  });
  it("keeps every sub-sector line", () => {
    const pc = adaptDeficitSubsector(deficitSubsector as unknown as DeficitSubsectorKpi, { ...base, slug: "deficit_subsector" }).perCapita!;
    expect(pc.blocks[0].series.map((s) => s.id)).toEqual(["central", "local", "social_security", "total"]);
  });
  it("is added to standard KPIs by withPerCapita, and absent without per_capita data", () => {
    const adapt = withPerCapita(adaptStandard, "% des recettes", [{ title: "Intérêts", lines: [["france", "France"]] }]);
    expect(adapt(debtService, { ...base, slug: "debt_service" }).perCapita?.ratioLabel).toBe("% des recettes");
    expect(adapt(overhead, base).perCapita).toBeUndefined();
    expect(perCapitaView(undefined, "% du PIB", [])).toBeUndefined();
  });
});
