import { describe, it, expect } from "vitest";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { PerformanceDetail } from "./PerformanceDetail";
import { KpiDetail } from "./KpiDetail";

function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/performance" element={<PerformanceDetail />} />
        <Route path="/kpi/:slug" element={<KpiDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PerformanceDetail", () => {
  it("defaults to the latest year and shows the national counts", async () => {
    renderAt("/performance");
    await waitFor(() => expect(screen.getByRole("heading", { name: /En 2025, sur l’ensemble des missions/ })).toBeInTheDocument());
    const summary = screen.getByRole("region", { name: "Bilan 2025" });
    expect(within(summary).getByText("684")).toBeInTheDocument(); // RAP 2025: targets met
    expect(screen.getByRole("combobox")).toHaveValue("2025");
  });

  it("honours ?annee= and lists missions alphabetically, accents ignored", async () => {
    const { container } = renderAt("/performance?annee=2022");
    await waitFor(() => expect(screen.getByRole("heading", { name: /En 2022/ })).toBeInTheDocument());
    const names = [...container.querySelectorAll(".perf-mission__name")].map((n) => n.textContent!);
    const norm = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
    expect(names.length).toBeGreaterThan(30);
    expect(names.map(norm)).toEqual([...names.map(norm)].sort());
  });

  it("filters to not-reported results only", async () => {
    const { container } = renderAt("/performance?annee=2025");
    await waitFor(() => expect(screen.getByRole("heading", { name: /En 2025/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("radio", { name: "Résultats non renseignés" }));
    const statuses = [...container.querySelectorAll(".perf-table__row td:last-child")].map((td) => td.textContent);
    expect(statuses.length).toBe(292);
    expect(new Set(statuses)).toEqual(new Set(["Résultat non renseigné"]));
  });

  it("is reachable from the KPI detail page", async () => {
    renderAt("/kpi/performance");
    const link = await screen.findByRole("link", { name: /Voir chaque indicateur/ });
    expect(link).toHaveAttribute("href", "/performance");
  });
});
