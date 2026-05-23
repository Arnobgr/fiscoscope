import { useEffect, useState } from "react";
import { getKpi, getMeta } from "./api";
import { buildView } from "./registry";
import type { KpiView, Meta } from "./types";

export function useMeta() {
  const [meta, setMeta] = useState<Meta | null>(null);
  useEffect(() => { getMeta().then(setMeta).catch(() => setMeta(null)); }, []);
  return meta;
}
export function useKpiView(slug: string) {
  const [view, setView] = useState<KpiView | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let live = true;
    getKpi(`kpi_${slug}`)
      .then((raw) => live && setView(buildView(slug, raw)))
      .catch(() => live && setError(true));
    return () => { live = false; };
  }, [slug]);
  return { view, error };
}
