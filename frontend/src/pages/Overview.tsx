import { useEffect, useState } from "react";
import { REGISTRY, THEMES, buildView } from "../data/registry";
import { getKpi } from "../data/api";
import type { KpiView } from "../data/types";
import { KpiCard } from "../components/KpiCard";

export function Overview() {
  const [views, setViews] = useState<KpiView[]>([]);
  useEffect(() => {
    Promise.all(
      REGISTRY.map((e) => getKpi(e.apiId).then((raw) => buildView(e.slug, raw))),
    ).then(setViews);
  }, []);

  return (
    <div className="overview">
      <p className="overview__intro">
        Des indicateurs longitudinaux (depuis 1995) mesurant l’efficacité de l’administration
        publique française, à partir de données publiques, comparés à la moyenne de l’OCDE.
      </p>
      {THEMES.map((theme) => {
        const themeViews = views.filter(
          (v) => REGISTRY.find((e) => e.slug === v.slug)?.theme === theme.id,
        );
        return (
          <section key={theme.id} className="theme-section">
            <h2 className="theme-section__title">{theme.label}</h2>
            <div className="kpi-grid">
              {themeViews.map((v) => <KpiCard key={v.slug} view={v} />)}
            </div>
          </section>
        );
      })}
    </div>
  );
}
