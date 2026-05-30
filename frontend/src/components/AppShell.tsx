import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { fmtDateFr } from "../data/format";

export function AppShell({ lastUpdated, children }: { lastUpdated?: string; children: ReactNode }) {
  return (
    <div className="app-shell">
      <header role="banner" className="app-header">
        <Link to="/" className="brand">🇫🇷 Fiscoscope</Link>
        <p className="tagline">L’efficacité de l’administration publique française, en chiffres</p>
        {lastUpdated && (
          <p className="last-updated">Dernière mise à jour : {fmtDateFr(lastUpdated)}</p>
        )}
      </header>
      <main>{children}</main>
      <footer className="app-footer">
        <p>
          Sources : INSEE, OCDE (Government at a Glance), GTED (CC-BY-4.0). Données publiques.{" "}
          <Link to="/methodologie">Méthodologie</Link>
        </p>
      </footer>
    </div>
  );
}
