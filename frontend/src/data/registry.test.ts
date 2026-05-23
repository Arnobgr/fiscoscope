import { describe, it, expect } from "vitest";
import { REGISTRY, THEMES, bySlug, buildView } from "./registry";
import overhead from "../fixtures/kpi_overhead_rate.json";

describe("registry", () => {
  it("has all 10 KPIs across 3 themes", () => {
    expect(REGISTRY.length).toBe(10);
    expect(THEMES.length).toBe(3);
  });
  it("every entry maps slug → apiId with kpi_ prefix and has French copy", () => {
    for (const e of REGISTRY) {
      expect(e.apiId).toBe(`kpi_${e.slug}`);
      expect(e.title.length).toBeGreaterThan(0);
      expect(e.explainer.length).toBeGreaterThan(10);
    }
  });
  it("bySlug finds an entry", () => {
    expect(bySlug("overhead_rate")?.apiId).toBe("kpi_overhead_rate");
  });
  it("buildView produces a KpiView via the entry's adapter", () => {
    const v = buildView("overhead_rate", overhead as any);
    expect(v.series[0].role).toBe("france");
    expect(v.title).toMatch(/administratif/i);
  });
});
