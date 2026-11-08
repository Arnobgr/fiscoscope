import { useParams, Link } from "react-router-dom";
import { useKpiView } from "../data/useData";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { StatCallout } from "../components/StatCallout";
import { MethodologyDisclosure } from "../components/MethodologyDisclosure";
import type { SecondaryBlock } from "../data/types";

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
      {[view.secondary, ...(view.panels ?? [])].filter((block): block is SecondaryBlock => !!block).map((block) => (
        <section key={block.title} className="kpi-detail__secondary">
          <h2>{block.title}</h2>
          {block.note && <p className="kpi-detail__note">{block.note}</p>}
          <TimeSeriesChart view={{ ...view, unit: block.unit, series: block.series,
            comparison: block.comparison, peers: block.peers,
            secondary: undefined, panels: undefined }} />
        </section>
      ))}
      <MethodologyDisclosure source={view.source} methodology={view.methodology} />
    </article>
  );
}
