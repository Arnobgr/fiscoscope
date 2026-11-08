import { useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import type { KpiView, ViewSeries } from "../data/types";
import { fmtValue, fmtAxis } from "../data/format";

const COLORS: Record<ViewSeries["role"], string> = {
  france: "#0055A4", oecd: "#8A8576", peer: "#A39E90", secondary: "#CC785C",
};
// Fixed per-series hues, none near France's bleu: muted peer countries, then the
// lines of multi-series charts (deficit by sub-sector, debt holders).
const SERIES_COLORS: Record<string, string> = {
  DEU: "#5F8A78", ESP: "#B8894A", ITA: "#A06A5E", NLD: "#C08A9A", GBR: "#8A6C93", SWE: "#7D8A45",
  local: "#CC785C", social_security: "#5F8A78", total: "#4A4740",
  central_bank: "#CC785C", other_residents: "#8A6C93",
};

function merge(seriesList: ViewSeries[]): Record<string, number | string>[] {
  const byX = new Map<number | string, Record<string, number | string>>();
  for (const s of seriesList) {
    for (const p of s.points) {
      const row = byX.get(p.x) ?? { x: p.x };
      row[s.id] = p.y;
      byX.set(p.x, row);
    }
  }
  return [...byX.values()].sort((a, b) => String(a.x).localeCompare(String(b.x)));
}

export function TimeSeriesChart({ view }: { view: KpiView }) {
  const [shown, setShown] = useState<Set<string>>(new Set());
  const options = [...(view.comparison ? [view.comparison] : []), ...(view.peers ?? [])];
  const toggle = (id: string) => setShown((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  // Comparisons first so France is drawn on top.
  const active = [...options.filter((s) => shown.has(s.id)), ...view.series];
  const data = merge(active);
  return (
    <div className="chart">
      {options.length > 0 && (
        <fieldset className="chart__compare">
          <legend className="chart__compare-label">Comparer à</legend>
          {options.map((s) => (
            <label key={s.id} className="chart__toggle">
              <input type="checkbox" checked={shown.has(s.id)} onChange={() => toggle(s.id)} />
              {s.label}
            </label>
          ))}
        </fieldset>
      )}
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E7E2D6" />
          <XAxis dataKey="x" />
          <YAxis width={64} tickFormatter={(v: number) => fmtAxis(v, view.unit)} />
          <Tooltip formatter={(v) => fmtValue(Number(v), view.unit)} />
          <Legend />
          {active.map((s) => (
            <Line key={s.id} type="monotone" dataKey={s.id} name={s.label}
              stroke={SERIES_COLORS[s.id] ?? COLORS[s.role]}
              strokeWidth={s.role === "france" ? 2.5 : s.role === "peer" ? 1.25 : 1.75}
              strokeDasharray={s.role === "oecd" ? "6 4" : undefined}
              dot={false} isAnimationActive={false} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
