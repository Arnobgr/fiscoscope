import { useParams, Link } from "react-router-dom";
import { useKpiView } from "../data/useData";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { StatCallout } from "../components/StatCallout";
import { MethodologyDisclosure } from "../components/MethodologyDisclosure";

export function KpiDetail() {
  const { slug = "" } = useParams();
  const { view, error } = useKpiView(slug);
  if (error) return <p className="state">Cet indicateur n’a pas pu être chargé. <Link to="/">Tous les indicateurs</Link></p>;
  if (!view) return <p className="state">Chargement…</p>;
  return (
    <article className="kpi-detail">
      <nav className="breadcrumb"><Link to="/">← Tous les indicateurs</Link></nav>
      <h1>{view.title}</h1>
      <p className="kpi-detail__explainer">{view.explainer}</p>
      <StatCallout view={view} />
      <TimeSeriesChart view={view} />
      {view.secondary && (
        <section className="kpi-detail__secondary">
          <h2>{view.secondary.title}</h2>
          <TimeSeriesChart view={{ ...view, series: view.secondary.series,
            comparison: view.secondary.comparison, secondary: undefined, hasBreak2020: false }} />
        </section>
      )}
      <MethodologyDisclosure source={view.source} methodology={view.methodology} />
    </article>
  );
}
