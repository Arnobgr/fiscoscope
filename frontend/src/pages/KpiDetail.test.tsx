import { describe, it, expect } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { KpiDetail } from "./KpiDetail";

function renderAt(slug: string, query = "") {
  render(
    <MemoryRouter initialEntries={[`/kpi/${slug}${query}`]}>
      <Routes><Route path="/kpi/:slug" element={<KpiDetail />} /></Routes>
    </MemoryRouter>,
  );
}

describe("KpiDetail", () => {
  it("renders title, explainer, and methodology disclosure for a standard KPI", async () => {
    renderAt("overhead_rate");
    await waitFor(() => expect(screen.getByRole("heading", { name: /Part de la masse salariale publique/ })).toBeInTheDocument());
    expect(screen.getByText(/comprend les enseignants, les soignants, les policiers/)).toBeInTheDocument();
    expect(screen.getByText(/Méthodologie & sources/i)).toBeInTheDocument();
  });
  it("renders the secondary block title for sustainability (debt)", async () => {
    renderAt("sustainability");
    await waitFor(() => expect(screen.getByRole("heading", { name: /Dette publique/i })).toBeInTheDocument());
  });
  it("switches to the € par habitant view and back", async () => {
    renderAt("debt_service");
    const perCapita = await screen.findByRole("radio", { name: /€ par habitant \(euros 2025\)/ });
    expect(screen.getByRole("radio", { name: "% des recettes" })).toBeChecked();
    fireEvent.click(perCapita);
    expect(await screen.findByRole("heading", { name: /Intérêts de la dette par habitant, en euros 2025/ })).toBeInTheDocument();
    expect(screen.getByText(/^France seule :/)).toBeInTheDocument();
    expect(screen.getByText(/^par habitant en \d{4}$/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "% des recettes" }));
    await waitFor(() => expect(screen.queryByText(/^France seule :/)).not.toBeInTheDocument());
  });
  it("opens directly on the € par habitant view from ?vue=habitant", async () => {
    renderAt("tax_burden", "?vue=habitant");
    expect(await screen.findByRole("heading", { name: /Impôts et cotisations par habitant/ })).toBeInTheDocument();
  });
  it("shows no view switch on a KPI without euro amounts", async () => {
    renderAt("overhead_rate");
    await screen.findByRole("heading", { name: /Part de la masse salariale publique/ });
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });
});
