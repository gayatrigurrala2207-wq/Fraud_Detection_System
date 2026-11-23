import type { ReactNode } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

// Validated categorical slots (dataviz reference palette, light mode): blue, orange.
export const SERIES = ["#2a78d6", "#eb6834"];
const GRID = "#e5e7eb";
const AXIS = { fontSize: 11, fill: "#64748b" };

type Row = object;
const cell = (row: Row, key: string) => (row as Record<string, unknown>)[key];

function TableView({ data, columns }: { data: Row[]; columns: { key: string; label: string; format?: (v: number) => string }[] }) {
  return (
    <details className="mt-2 text-xs">
      <summary className="cursor-pointer text-slate-500 hover:text-slate-800">View as table</summary>
      <div className="mt-2 max-h-64 overflow-auto">
        <table className="w-full text-left tabular-nums">
          <thead className="sticky top-0 bg-white text-slate-500">
            <tr>{columns.map((c) => <th key={c.key} className="py-1 pr-3 font-medium">{c.label}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((row, i) => (
              <tr key={i}>
                {columns.map((c) => (
                  <td key={c.key} className="py-1 pr-3">
                    {typeof cell(row, c.key) === "number" && c.format ? c.format(cell(row, c.key) as number) : String(cell(row, c.key))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function ChartTooltip({ active, payload, label, format, labelFormat }: {
  active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string | number;
  format: (v: number) => string; labelFormat?: (v: string | number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-slate-800">{labelFormat ? labelFormat(label ?? "") : label}</p>
      {payload.map((item) => (
        <p key={item.name} className="flex items-center gap-2 text-slate-600">
          <span className="inline-block size-2 rounded-full" style={{ background: item.color }} aria-hidden />
          {item.name}: <span className="font-medium text-slate-900 tabular-nums">{format(item.value)}</span>
        </p>
      ))}
    </div>
  );
}

/** One measure per chart (never a second y-axis). */
export function BarSeries({ data, x, y, name, format, height = 240, horizontal = false, xLabel, color = SERIES[0] }: {
  data: Row[]; x: string; y: string; name: string; format: (v: number) => string; height?: number;
  horizontal?: boolean; xLabel?: string; color?: string;
}) {
  const chartHeight = horizontal ? Math.max(height, data.length * 26 + 40) : height;
  return (
    <>
      <div style={{ height: chartHeight }} role="img" aria-label={`${name} by ${xLabel ?? x}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 8, right: 16, left: 8, bottom: 4 }}
                    barCategoryGap={2}>
            <CartesianGrid stroke={GRID} vertical={horizontal} horizontal={!horizontal} />
            {horizontal ? (
              <>
                <XAxis type="number" tick={AXIS} tickFormatter={format} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey={x} tick={AXIS} width={110} axisLine={false} tickLine={false} />
              </>
            ) : (
              <>
                <XAxis dataKey={x} tick={AXIS} axisLine={{ stroke: GRID }} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={AXIS} tickFormatter={format} axisLine={false} tickLine={false} width={56} />
              </>
            )}
            <Tooltip cursor={{ fill: "#f1f5f9" }} content={<ChartTooltip format={format} />} />
            <Bar dataKey={y} name={name} fill={color} maxBarSize={28}
                 radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <TableView data={data} columns={[{ key: x, label: xLabel ?? x }, { key: y, label: name, format }]} />
    </>
  );
}

export function LineSeries({ data, name, xLabel, yLabel, height = 260, reference }: {
  data: { x: number; y: number }[]; name: string; xLabel: string; yLabel: string; height?: number;
  reference?: ReactNode;
}) {
  const format = (v: number) => v.toFixed(3);
  return (
    <>
      <div style={{ height }} role="img" aria-label={name}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 16 }}>
            <CartesianGrid stroke={GRID} />
            <XAxis type="number" dataKey="x" domain={[0, 1]} tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }}
                   label={{ value: xLabel, position: "insideBottom", offset: -8, style: AXIS }} />
            <YAxis type="number" domain={[0, 1]} tick={AXIS} tickLine={false} axisLine={false} width={40}
                   label={{ value: yLabel, angle: -90, position: "insideLeft", style: AXIS }} />
            {reference}
            <Tooltip content={<ChartTooltip format={format} labelFormat={(v) => `${xLabel} ${Number(v).toFixed(3)}`} />} />
            <Line type="monotone" dataKey="y" name={yLabel} stroke={SERIES[0]} strokeWidth={2} dot={false}
                  activeDot={{ r: 4 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <TableView data={data} columns={[{ key: "x", label: xLabel, format }, { key: "y", label: yLabel, format }]} />
    </>
  );
}

export { ReferenceLine };
