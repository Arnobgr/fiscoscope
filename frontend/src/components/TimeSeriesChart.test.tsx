import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TimeSeriesChart } from "./TimeSeriesChart";
import type { KpiView } from "../data/types";

const view: KpiView = {
  slug: "x", apiId: "kpi_x", title: "T", explainer: "E", unit: "percent", xKind: "year",
  series: [{ id: "france", label: "France", role: "france",
    points: [{ x: 2018, y: 1 }, { x: 2019, y: 2 }] }],
  comparison: { id: "oecd", label: "Moyenne des 6 pays", role: "oecd",
    points: [{ x: 2018, y: 1.5 }, { x: 2019, y: 1.6 }] },
  source: "s", methodology: "m",
};

describe("TimeSeriesChart", () => {
  it("hides the peer-average comparison until toggled on", async () => {
    render(<TimeSeriesChart view={view} />);
    const toggle = screen.getByRole("checkbox", { name: /moyenne des 6 pays/i });
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    expect(toggle).toBeChecked();
  });
  it("offers one toggle per peer country alongside the peer average", async () => {
    render(<TimeSeriesChart view={{ ...view, peers: [
      { id: "DEU", label: "Allemagne", role: "peer", points: [{ x: 2018, y: 1.2 }] },
      { id: "SWE", label: "Suède", role: "peer", points: [{ x: 2018, y: 1.4 }] },
    ] }} />);
    expect(screen.getAllByRole("checkbox")).toHaveLength(3);
    const deu = screen.getByRole("checkbox", { name: "Allemagne" });
    await userEvent.click(deu);
    expect(deu).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Suède" })).not.toBeChecked();
  });
  it("renders no toggle when there is no comparison", () => {
    render(<TimeSeriesChart view={{ ...view, comparison: undefined }} />);
    expect(screen.queryByRole("checkbox")).toBeNull();
  });
});
