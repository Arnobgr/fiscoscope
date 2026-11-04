import { Link } from "react-router-dom";

export function Methodology() {
  return (
    <article className="methodology-page">
      <nav className="breadcrumb"><Link to="/">← Tous les indicateurs</Link></nav>
      <h1>Méthodologie</h1>
      <p>
        Fiscoscope mesure la productivité et l’efficacité de l’administration publique française
        à partir de données publiques, sous forme de ratios (par euro dépensé), sur longue période
        (depuis 1995) et, lorsque c’est possible, en comparaison de six autres pays européens.
      </p>
      <h2>Sources</h2>
      <ul>
        <li><strong>INSEE</strong> — comptes nationaux (séries BDM), pour les agrégats des administrations publiques et le PIB.</li>
        <li><strong>OCDE</strong> — Government at a Glance 2025 et statistiques de santé, pour les pays comparés (Allemagne, Espagne, Italie, Pays-Bas, Royaume-Uni, Suède) et l’espérance de vie.</li>
        <li><strong>GTED</strong> — Global Tax Expenditures Database (CC-BY-4.0), pour les dépenses fiscales.</li>
        <li><strong>Urssaf</strong> — masse salariale du secteur privé (open.urssaf.fr), pour le ratio masse salariale public / privé.</li>
        <li><strong>Ministère de l’Économie et des Finances</strong> — situation mensuelle du budget de l’État (data.economie.gouv.fr), pour l’exécution budgétaire mensuelle.</li>
      </ul>
      <h2>Limites</h2>
      <p>
        Les comparaisons internationales (données OCDE) débutent en 2007. La « moyenne des 6 pays »
        est la moyenne simple (non pondérée) des six pays comparés ; ce n’est pas la moyenne de
        l’ensemble des pays de l’OCDE. Un changement de base méthodologique INSEE intervient
        en 2020 sur certains indicateurs fonctionnels (signalé sur les graphiques concernés). Les
        dernières années de certaines séries sont des prévisions.
      </p>
    </article>
  );
}
