import { Link } from "react-router-dom";

export function Methodology() {
  return (
    <article className="methodology-page">
      <nav className="breadcrumb"><Link to="/">← Tous les indicateurs</Link></nav>
      <h1>Méthodologie</h1>
      <p>
        fisc-o-scope mesure la productivité et l’efficacité de l’administration publique française
        à partir de données publiques, sous forme de ratios (par euro dépensé), sur longue période
        (depuis 1995) et, lorsque c’est possible, en comparaison de la moyenne de l’OCDE.
      </p>
      <h2>Sources</h2>
      <ul>
        <li><strong>INSEE</strong> — comptes nationaux (séries BDM), pour les agrégats des administrations publiques et le PIB.</li>
        <li><strong>OCDE</strong> — Government at a Glance 2025 et statistiques de santé, pour la moyenne OCDE et l’espérance de vie.</li>
        <li><strong>GTED</strong> — Global Tax Expenditures Database (CC-BY-4.0), pour les dépenses fiscales.</li>
      </ul>
      <h2>Limites</h2>
      <p>
        Les comparaisons OCDE débutent en 2007. Un changement de base méthodologique INSEE intervient
        en 2020 sur certains indicateurs fonctionnels (signalé sur les graphiques concernés). Les
        dernières années de certaines séries sont des prévisions.
      </p>
    </article>
  );
}
