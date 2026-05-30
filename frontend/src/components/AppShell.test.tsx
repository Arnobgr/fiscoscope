import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("renders the title and a last-updated badge", () => {
    render(
      <MemoryRouter>
        <AppShell lastUpdated="2026-05-21T10:03:39Z">
          <p>contenu</p>
        </AppShell>
      </MemoryRouter>,
    );
    expect(screen.getByRole("banner")).toHaveTextContent(/🇫🇷 Fiscoscope/i);
    expect(screen.getByText(/Dernière mise à jour/i)).toHaveTextContent(/21 mai 2026/);
    expect(screen.getByText("contenu")).toBeInTheDocument();
  });
});
