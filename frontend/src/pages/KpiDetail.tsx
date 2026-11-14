import { useParams, useSearchParams, Link } from "react-router-dom";
import { useKpiView } from "../data/useData";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { StatCallout } from "../components/StatCallout";
import { MethodologyDisclosure } from "../components/MethodologyDisclosure";
import type { KpiView, SecondaryBlock } from "../data/types";

// ?vue=habitant switches to the "€ par habitant" view (roadmap 2.1), so the view can be linked.
const PER_CAPITA_PARAM = "habitant";

function Block({ view, block }: { view: KpiView; block: SecondaryBlock }) {
  return (
    <section className="kpi-detail__secondary">
      <h2>{block.title}</h2>
      {block.note && <p className="kpi-detail__note">{block.note}</p>}
      <TimeSeriesChart view={{ ...view, unit: block.unit, series: block.series,
        comparison: block.comparison, peers: block.peers,
        secondary: undefined, panels: undefined }} />
    </section>
  );
}

export function KpiDetail() {
  const { slug = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const { view, error } = useKpiView(slug);
  if (error) return <p className="state">Cet indicateur n’a pas pu être chargé. <Link to="/">Tous les indicateurs</Link></p>;
  if (!view) return <p className="state">Chargement…</p>;
  const perCapita = params.get("vue") === PER_CAPITA_PARAM ? view.perCapita : undefined;
  const blocks = perCapita ? perCapita.blocks
    : [view.secondary, ...(view.panels ?? [])].filter((block): block is SecondaryBlock => !!block);
  return (
    <article className="kpi-detail">
      <nav className="breadcrumb"><Link to="/">← Tous les indicateurs</Link></nav>
      <h1>{view.title}</h1>
      <p className="kpi-detail__explainer">{view.explainer}</p>
      {view.perCapita && (
        <fieldset className="chart__compare kpi-detail__view">
          <legend className="chart__compare-label">Afficher</legend>
          {[[view.perCapita.ratioLabel, ""], [view.perCapita.label, PER_CAPITA_PARAM]].map(([label, value]) => (
            <label key={value} className="chart__toggle">
              <input type="radio" name="vue" checked={(perCapita ? PER_CAPITA_PARAM : "") === value}
                onChange={() => setParams(value ? { vue: value } : {}, { replace: true })} />
              {label}
            </label>
          ))}
        </fieldset>
      )}
      <StatCallout view={perCapita ? { ...view, latest: perCapita.latest, context: undefined } : view} />
      {!perCapita && <TimeSeriesChart view={view} />}
      {view.drilldown && (
        <p className="kpi-detail__drilldown"><Link to={view.drilldown.to}>{view.drilldown.label} →</Link></p>
      )}
      {blocks.map((block) => <Block key={block.title} view={view} block={block} />)}
      <MethodologyDisclosure source={view.source} methodology={view.methodology} />
    </article>
  );
}
