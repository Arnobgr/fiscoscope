import { LineChart, Line, YAxis } from "recharts";
import type { ViewSeries } from "../data/types";

export function Sparkline({ series }: { series: ViewSeries }) {
  const data = series.points.map((p) => ({ x: p.x, y: p.y }));
  return (
    <LineChart width={120} height={36} data={data} aria-hidden="true">
      <YAxis hide domain={["dataMin", "dataMax"]} />
      <Line type="monotone" dataKey="y" dot={false} strokeWidth={2} stroke="#0055A4" isAnimationActive={false} />
    </LineChart>
  );
}
