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
        <nav className="footer-links" aria-label="Liens personnels">
          <a href="https://www.linkedin.com/in/arno-beauger/" target="_blank" rel="noopener noreferrer">LinkedIn</a>
          <a href="https://github.com/Arnobgr/" target="_blank" rel="noopener noreferrer">GitHub</a>
          <a href="https://arno-id4.pages.dev/" target="_blank" rel="noopener noreferrer">Portfolio</a>
          <a href="https://x.com/arnobgr" target="_blank" rel="noopener noreferrer">X</a>
        </nav>
      </footer>
    </div>
  );
}
