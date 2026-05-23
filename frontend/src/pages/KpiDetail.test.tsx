import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { KpiDetail } from "./KpiDetail";

function renderAt(slug: string) {
  render(
    <MemoryRouter initialEntries={[`/kpi/${slug}`]}>
      <Routes><Route path="/kpi/:slug" element={<KpiDetail />} /></Routes>
    </MemoryRouter>,
  );
}

describe("KpiDetail", () => {
  it("renders title, explainer, and methodology disclosure for a standard KPI", async () => {
    renderAt("overhead_rate");
    await waitFor(() => expect(screen.getByRole("heading", { name: /Coût administratif/ })).toBeInTheDocument());
    expect(screen.getByText(/chaque euro dépensé/)).toBeInTheDocument();
    expect(screen.getByText(/Méthodologie & sources/i)).toBeInTheDocument();
  });
  it("renders the secondary block title for sustainability (debt)", async () => {
    renderAt("sustainability");
    await waitFor(() => expect(screen.getByRole("heading", { name: /Dette publique/i })).toBeInTheDocument());
  });
});
