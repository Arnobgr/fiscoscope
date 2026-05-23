import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TimeSeriesChart } from "./TimeSeriesChart";
import type { KpiView } from "../data/types";

const view: KpiView = {
  slug: "x", apiId: "kpi_x", title: "T", explainer: "E", unit: "percent", xKind: "year",
  series: [{ id: "france", label: "France", role: "france",
    points: [{ x: 2018, y: 1 }, { x: 2019, y: 2 }] }],
  comparison: { id: "oecd", label: "Moyenne OCDE", role: "oecd",
    points: [{ x: 2018, y: 1.5 }, { x: 2019, y: 1.6 }] },
  hasBreak2020: false, source: "s", methodology: "m",
};

describe("TimeSeriesChart", () => {
  it("hides the OECD comparison until toggled on", async () => {
    render(<TimeSeriesChart view={view} />);
    const toggle = screen.getByRole("checkbox", { name: /moyenne ocde/i });
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    expect(toggle).toBeChecked();
  });
  it("renders no toggle when there is no comparison", () => {
    render(<TimeSeriesChart view={{ ...view, comparison: undefined }} />);
    expect(screen.queryByRole("checkbox")).toBeNull();
  });
});
