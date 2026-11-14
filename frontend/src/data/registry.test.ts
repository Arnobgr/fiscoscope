import { describe, it, expect } from "vitest";
import { REGISTRY, THEMES, bySlug, buildView } from "./registry";
import overhead from "../fixtures/kpi_overhead_rate.json";

describe("registry", () => {
  it("has all 16 KPIs across 3 themes", () => {
    expect(REGISTRY.length).toBe(16);
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
    expect(v.title).toMatch(/masse salariale publique/i);
    expect(v.title).not.toMatch(/administratif/i);
  });
  it("names the COFOG functions instead of calling them productive", () => {
    const title = bySlug("productive_spend")!.title;
    expect(title).toBe("Affaires économiques, environnement et logement");
    expect(title).not.toMatch(/productiv/i);
  });
  it("every KPI with a yearly history gets a context sentence (roadmap 2.4)", async () => {
    // performance: the indicator set changes every year; monthly_execution: no yearly history.
    const without = new Set(["performance", "monthly_execution"]);
    for (const e of REGISTRY) {
      const raw = (await import(`../fixtures/${e.apiId}.json`)).default;
      const view = buildView(e.slug, raw);
      if (without.has(e.slug)) expect(view.context).toBeUndefined();
      else expect(view.context, e.slug).toMatch(/\.$/);
    }
  });
});

