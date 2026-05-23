import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { KpiCard } from "./KpiCard";
import overhead from "../fixtures/kpi_overhead_rate.json";
import { buildView } from "../data/registry";

function renderCard(raw: unknown, slug: string) {
  render(<MemoryRouter><KpiCard view={buildView(slug, raw)} /></MemoryRouter>);
}

describe("KpiCard", () => {
  it("shows the French title, formatted latest value, and links to detail", () => {
    renderCard(overhead, "overhead_rate");
    expect(screen.getByRole("link")).toHaveAttribute("href", "/kpi/overhead_rate");
    expect(screen.getByText(/Coût administratif/)).toBeInTheDocument();
    // latest overhead value 2025 formatted as fr percent
    expect(screen.getByTestId("kpi-latest").textContent).toMatch(/%/);
  });
  it("renders a YoY direction indicator", () => {
    renderCard(overhead, "overhead_rate");
    expect(screen.getByTestId("kpi-yoy")).toHaveAttribute("data-dir");
  });
});
