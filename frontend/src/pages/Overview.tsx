import { useCallback, useEffect, useState } from "react";
import { REGISTRY, THEMES, buildView } from "../data/registry";
import { getKpi } from "../data/api";
import type { KpiView } from "../data/types";
import { KpiCard, KpiCardSkeleton, KpiCardError } from "../components/KpiCard";

type Card = { slug: string; ok: true; view: KpiView } | { slug: string; ok: false };

export function Overview() {
  const [cards, setCards] = useState<Card[] | null>(null); // null = loading
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let alive = true;
    setCards(null);
    Promise.allSettled(
      REGISTRY.map((e) => getKpi(e.apiId).then((raw) => buildView(e.slug, raw))),
    ).then((results) => {
      if (!alive) return;
      setCards(
        results.map((r, i) =>
          r.status === "fulfilled"
            ? { slug: REGISTRY[i].slug, ok: true as const, view: r.value }
            : { slug: REGISTRY[i].slug, ok: false as const },
        ),
      );
    });
    return () => { alive = false; };
  }, [reloadKey]);

  const retry = useCallback(() => setReloadKey((k) => k + 1), []);

  const loading = cards === null;
  const allFailed = !!cards && cards.length > 0 && cards.every((c) => !c.ok);

  return (
    <div className="overview">
      <h1 className="sr-only">
        Fiscoscope — indicateurs d’efficacité de l’administration publique française
      </h1>
      <p className="overview__intro">
        Des indicateurs longitudinaux (depuis 1995) mesurant l’efficacité de l’administration
        publique française, à partir de données publiques, comparés à la moyenne de l’OCDE.
      </p>

      {allFailed ? (
        <div className="state state--error" role="alert">
          <p>Impossible de charger les indicateurs pour le moment.</p>
          <button type="button" className="link-button" onClick={retry}>Réessayer</button>
        </div>
      ) : (
        THEMES.map((theme) => {
          const entries = REGISTRY.filter((e) => e.theme === theme.id);
          return (
            <section key={theme.id} className="theme-section">
              <h2 className="theme-section__title">{theme.label}</h2>
              <div className="kpi-grid">
                {loading
                  ? entries.map((e) => <KpiCardSkeleton key={e.slug} />)
                  : entries.map((e, i) => {
                      const card = cards!.find((c) => c.slug === e.slug);
                      return card && card.ok ? (
                        <KpiCard key={e.slug} view={card.view} index={i} />
                      ) : (
                        <KpiCardError key={e.slug} title={e.title} onRetry={retry} index={i} />
                      );
                    })}
              </div>
            </section>
          );
        })
      )}
    </div>
  );
}
