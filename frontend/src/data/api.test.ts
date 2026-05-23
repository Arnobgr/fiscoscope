import { describe, it, expect, beforeEach } from "vitest";
import { getMeta, getKpi, _resetCache } from "./api";

beforeEach(() => _resetCache());

describe("api (fixtures mode)", () => {
  it("getMeta returns the meta fixture", async () => {
    const m = await getMeta();
    expect(typeof m.last_run).toBe("string");
  });
  it("getKpi returns a raw KPI by apiId", async () => {
    const raw = await getKpi("kpi_overhead_rate");
    expect((raw as any).kpi_id).toBe("overhead_rate");
  });
  it("caches: second call returns same reference", async () => {
    const a = await getKpi("kpi_overhead_rate");
    const b = await getKpi("kpi_overhead_rate");
    expect(a).toBe(b);
  });
});
