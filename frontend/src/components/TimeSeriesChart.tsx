import { useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import type { KpiView, ViewSeries } from "../data/types";

const COLORS: Record<ViewSeries["role"], string> = {
  france: "#0055A4", oecd: "#8A8576", secondary: "#CC785C",
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
  const [showOecd, setShowOecd] = useState(false);
  const active = [...view.series, ...(showOecd && view.comparison ? [view.comparison] : [])];
  const data = merge(active);
  return (
    <div className="chart">
      {view.comparison && (
        <label className="chart__toggle">
          <input type="checkbox" checked={showOecd} onChange={(e) => setShowOecd(e.target.checked)} />
          Comparer à la moyenne OCDE
        </label>
      )}
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E7E2D6" />
          <XAxis dataKey="x" />
          <YAxis />
          <Tooltip />
          <Legend />
          {active.map((s) => (
            <Line key={s.id} type="monotone" dataKey={s.id} name={s.label}
              stroke={COLORS[s.role]} strokeWidth={s.role === "france" ? 2.5 : 1.75}
              strokeDasharray={s.role === "oecd" ? "6 4" : undefined}
              dot={false} isAnimationActive={false} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
      {view.hasBreak2020 && (
        <p className="chart__note">
          <span className="chart__note-text">
            <strong className="chart__note-label">Rupture de série 2020.</strong>{" "}
            Changement de base méthodologique (INSEE → OCDE).
          </span>
        </p>
      )}
    </div>
  );
}
