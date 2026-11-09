import { Link } from "react-router-dom";

export function Methodology() {
  return (
    <article className="methodology-page">
      <nav className="breadcrumb"><Link to="/">← Tous les indicateurs</Link></nav>
      <h1>Méthodologie</h1>
      <p>
        Fiscoscope mesure la productivité et l’efficacité de l’administration publique française
        à partir de données publiques, sous forme de ratios (par euro dépensé), sur longue période
        (depuis 1995) et, lorsque c’est possible, en comparaison d’autres pays européens.
      </p>
      <h2>Sources</h2>
      <ul>
        <li><strong>INSEE</strong> — comptes nationaux (séries BDM), pour les agrégats des administrations publiques et le PIB.</li>
        <li><strong>Eurostat</strong> — comptes des administrations publiques (dépenses par fonction COFOG, soldes par sous-secteur, intérêts, recettes, détenteurs de la dette), pour la France et les pays comparés (Allemagne, Espagne, Italie, Pays-Bas, Suède) et la moyenne de l’Union européenne.</li>
        <li><strong>OCDE</strong> — Government at a Glance 2025 (dont l’emploi public), Revenue Statistics (impôts et cotisations) et statistiques de santé, pour les pays comparés (Allemagne, Espagne, Italie, Pays-Bas, Royaume-Uni, Suède), la moyenne de l’OCDE et l’espérance de vie.</li>
        <li><strong>GTED</strong> — Global Tax Expenditures Database (CC-BY-4.0), pour les dépenses fiscales.</li>
        <li><strong>Urssaf</strong> — masse salariale du secteur privé (open.urssaf.fr), pour le ratio masse salariale public / privé.</li>
        <li><strong>Ministère de l’Économie et des Finances</strong> — situation mensuelle du budget de l’État (data.economie.gouv.fr), pour l’exécution budgétaire mensuelle ; indicateurs de performance des programmes du budget de l’État (cibles et résultats publiés dans les rapports annuels de performance, et part des cibles atteintes depuis 2007), pour les cibles de performance.</li>
      </ul>
      <h2>Limites</h2>
      <p>
        Les comparaisons tirées d’Eurostat portent sur cinq pays, depuis 1995 pour la plupart des
        séries, et sur la moyenne de
        l’Union européenne à 27, agrégat publié par Eurostat (depuis 2010 pour les dépenses par
        fonction) ; le Royaume-Uni n’y figure plus depuis le Brexit. Les comparaisons tirées de
        l’OCDE incluent le Royaume-Uni mais débutent en 2007 (1965 pour les impôts et cotisations) ; la
        « moyenne des 6 pays » qui accompagne certaines d’entre elles est la moyenne simple (non pondérée) des six pays comparés, et non la moyenne de
        l’ensemble des pays de l’OCDE. Les dernières années de certaines séries sont des prévisions.
      </p>
    </article>
  );
}
