import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getKpi } from "../data/api";
import { PERFORMANCE_STATUS } from "../data/adapters";
import type {
  PerformanceKpi, PerformanceDetail as Detail, PerfCounts, PerfMission, PerfRow, PerfStatus,
} from "../data/types";

type Filter = "all" | "missed" | "not_reported";
const FILTERS: [Filter, string][] = [
  ["all", "Tous les indicateurs"],
  ["missed", "Objectifs manqués"],
  ["not_reported", "Résultats non renseignés"],
];
const keep = (filter: Filter, status: PerfStatus | null) =>
  filter === "all"
  || (filter === "missed" ? status === "improved" || status === "not_improved" : status === "not_reported");

const COUNTED = ["met", "improved", "not_improved", "not_reported"] as const;
const nf = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });
// Values are shown as published: numbers formatted fr-FR, text (e.g. "26 500 000", "-") untouched.
const cell = (v: string | number | null) => (v == null ? "—" : typeof v === "number" ? nf.format(v) : v);

// Keep only the rows matching the filter; drop the branches left empty.
function filterMission(m: PerfMission, filter: Filter): PerfMission | null {
  if (filter === "all") return m;
  const groups = m.groups.map((g) => ({
    ...g,
    objectives: g.objectives.map((o) => ({
      ...o,
      indicators: o.indicators
        .map((i) => ({ ...i, rows: i.rows.filter((r) => keep(filter, r.status)) }))
        .filter((i) => i.rows.length),
    })).filter((o) => o.indicators.length),
  })).filter((g) => g.objectives.length);
  return groups.length ? { ...m, groups } : null;
}

function Counts({ counts }: { counts: PerfCounts }) {
  return (
    <span className="perf-counts">
      {COUNTED.map((k) => (
        <span key={k} className="perf-counts__item">{PERFORMANCE_STATUS[k]} : <strong>{counts[k]}</strong></span>
      ))}
    </span>
  );
}

function Row({ label, sub, row }: { label: string; sub?: string | null; row: PerfRow }) {
  return (
    <tr className="perf-table__row">
      <th scope="row">
        {label}
        {sub && <span className="perf-table__sub">{sub}</span>}
      </th>
      <td data-label="Unité">{row.unit ?? "—"}</td>
      <td data-label="Cible" className="perf-table__num">{cell(row.target)}</td>
      <td data-label="Résultat" className="perf-table__num">
        {cell(row.result)}
        {row.comment && <span className="perf-table__sub">{row.comment}</span>}
      </td>
      <td data-label="Évaluation">{PERFORMANCE_STATUS[row.status ?? "unassessed"]}</td>
    </tr>
  );
}

function Mission({ mission, index }: { mission: PerfMission; index: number }) {
  return (
    <details className="perf-mission">
      <summary>
        <span className="perf-mission__name">{mission.mission}</span>
        <Counts counts={mission.counts} />
      </summary>
      {mission.groups.map((g, gi) => {
        const id = `perf-${index}-${gi}`;
        return (
          <section key={id} className="perf-group">
            <h3 id={id}>
              {g.programme_code == null ? "Indicateurs de la mission" : `Programme ${g.programme_code} — ${g.programme}`}
            </h3>
            <div className="perf-table__scroll">
              <table className="perf-table" aria-labelledby={id}>
                <thead>
                  <tr>
                    <th scope="col">Indicateur</th>
                    <th scope="col">Unité</th>
                    <th scope="col">Cible</th>
                    <th scope="col">Résultat</th>
                    <th scope="col">Évaluation</th>
                  </tr>
                </thead>
                <tbody>
                  {g.objectives.map((o, oi) => [
                    <tr key={`o${oi}`} className="perf-table__objective">
                      <th scope="colgroup" colSpan={5}>Objectif : {o.objective ?? "—"}</th>
                    </tr>,
                    ...o.indicators.flatMap((ind, ii) => {
                      const only = ind.rows.length === 1 ? ind.rows[0] : null;
                      if (only) {
                        const sub = only.sub_indicator !== ind.indicator ? only.sub_indicator : null;
                        return [<Row key={`i${oi}-${ii}`} label={ind.indicator} sub={sub} row={only} />];
                      }
                      return [
                        <tr key={`i${oi}-${ii}`} className="perf-table__indicator">
                          <th scope="colgroup" colSpan={5}>{ind.indicator}</th>
                        </tr>,
                        ...ind.rows.map((r, ri) => (
                          <Row key={`i${oi}-${ii}-${ri}`} label={r.sub_indicator ?? ind.indicator} row={r} />
                        )),
                      ];
                    }),
                  ])}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </details>
  );
}

export function PerformanceDetail() {
  const [params, setParams] = useSearchParams();
  const [years, setYears] = useState<number[] | null>(null);
  const [loaded, setLoaded] = useState<Detail | null>(null);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => {
    getKpi("kpi_performance")
      .then((raw) => setYears((raw as PerformanceKpi).detail_years))
      .catch(() => setError(true));
  }, []);

  const asked = Number(params.get("annee"));
  const year = years?.length ? (years.includes(asked) ? asked : years[years.length - 1]) : null;

  useEffect(() => {
    if (year == null) return;
    let live = true;
    getKpi(`performance_detail_${year}`)
      .then((raw) => live && setLoaded(raw as Detail))
      .catch(() => live && setError(true));
    return () => { live = false; };
  }, [year]);

  const detail = loaded?.year === year ? loaded : null;
  const missions = useMemo(
    () => (detail?.missions ?? []).map((m) => filterMission(m, filter)).filter((m): m is PerfMission => !!m),
    [detail, filter],
  );

  if (error) return <p className="state">Les indicateurs n’ont pas pu être chargés. <Link to="/kpi/performance">Retour</Link></p>;
  return (
    <article className="perf-page">
      <nav className="breadcrumb"><Link to="/kpi/performance">← Part des cibles de performance atteintes</Link></nav>
      <h1>Cibles et résultats, indicateur par indicateur</h1>
      <p className="perf-page__intro">
        Pour chaque programme du budget de l’État, l’administration fixe une cible à ses indicateurs
        de performance, puis publie le résultat obtenu dans le rapport annuel de performance. Voici,
        tels que publiés, chaque indicateur, sa cible et son résultat. Les missions sont classées par
        ordre alphabétique.
      </p>
      <p className="perf-page__note">
        Certains indicateurs de mission reprennent un indicateur de programme : ils figurent aux deux
        niveaux et sont comptés deux fois, comme dans le décompte officiel. «&nbsp;Objectifs manqués&nbsp;»
        regroupe les cibles non atteintes, en amélioration ou non.
      </p>

      {years && year != null && (
        <div className="perf-controls">
          <label className="perf-controls__year">
            Année
            <select value={year} onChange={(e) => setParams({ annee: e.target.value })}>
              {years.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
          </label>
          <fieldset className="perf-controls__filter">
            <legend>Afficher</legend>
            {FILTERS.map(([id, label]) => (
              <label key={id} className="chart__toggle">
                <input type="radio" name="perf-filter" value={id} checked={filter === id} onChange={() => setFilter(id)} />
                {label}
              </label>
            ))}
          </fieldset>
        </div>
      )}

      {!detail ? <p className="state">Chargement…</p> : (
        <>
          <section className="perf-summary" aria-label={`Bilan ${detail.year}`}>
            <h2>En {detail.year}, sur l’ensemble des missions</h2>
            <dl className="perf-summary__list">
              {COUNTED.map((k) => (
                <div key={k}><dt>{PERFORMANCE_STATUS[k]}</dt><dd>{detail.counts[k]}</dd></div>
              ))}
            </dl>
            <p className="perf-page__note">
              Non comptés : {detail.counts.not_retained} indicateurs non retenus
              et {detail.counts.unassessed} sans évaluation.
            </p>
          </section>

          {missions.length === 0
            ? <p className="state">Aucun indicateur ne correspond à ce filtre en {detail.year}.</p>
            : missions.map((m, i) => <Mission key={m.mission} mission={m} index={i} />)}

          <p className="perf-page__source"><strong>Source :</strong> {detail.source}</p>
        </>
      )}
    </article>
  );
}
