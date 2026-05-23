import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Overview } from "./Overview";

describe("Overview", () => {
  it("renders the 3 theme headings and 10 KPI cards", async () => {
    render(<MemoryRouter><Overview /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("Efficacité administrative")).toBeInTheDocument();
    });
    expect(screen.getByText("Soutenabilité des finances publiques")).toBeInTheDocument();
    expect(screen.getByText("Dépenses & résultats")).toBeInTheDocument();
    const cards = await screen.findAllByRole("link");
    // 10 KPI cards (theme headings are not links)
    expect(cards.filter((c) => c.getAttribute("href")?.startsWith("/kpi/")).length).toBe(10);
  });
});
