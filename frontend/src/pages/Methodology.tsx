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
        <li><strong>INSEE</strong> — comptes nationaux (séries BDM), pour les agrégats des administrations publiques et le PIB ; population moyenne et indice des prix à la consommation, pour les montants en euros par habitant.</li>
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
      <h2>Euros par habitant</h2>
      <p>
        Pour les indicateurs exprimés en euros ou en part du PIB, une seconde vue donne le montant
        par habitant : le montant annuel en euros courants est divisé par la population moyenne de
        l’année (INSEE, France entière), puis converti en euros constants de la dernière année
        complète avec l’indice des prix à la consommation de l’INSEE, disponible depuis 1996. Cette
        vue porte sur la France seule : comparer des euros par habitant entre pays demanderait de
        corriger les écarts de prix, les comparaisons internationales restent donc exprimées en ratios.
      </p>
      <h2>Phrases de contexte</h2>
      <p>
        La phrase sous la valeur de chaque indicateur est calculée automatiquement à chaque mise à
        jour des données, sur la série principale (en ratio, France). Elle retient le premier de ces
        trois faits qui s’applique : la valeur la plus haute ou la plus basse depuis une année
        remontant à cinq ans ou plus (« depuis le début de la série » si elle n’a jamais été atteinte,
        pour une série d’au moins dix ans) ; la France au plus haut ou au plus bas des pays
        comparés, l’année la plus récente où tous ont une valeur (les moyennes ne comptent pas comme
        un pays) ; sinon, l’évolution sur dix ans. Les prévisions sont exclues. Les révisions des
        années passées par l’INSEE ou Eurostat peuvent changer la phrase. Les cibles de performance
        (liste d’indicateurs différente chaque année) et l’exécution mensuelle n’en ont pas.
      </p>
    </article>
  );
}
