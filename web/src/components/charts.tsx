"use client";

import * as React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { pct } from "@/lib/utils";

const axisTick = { fill: "var(--muted-foreground)", fontSize: 12 };

function TooltipBox({
  active,
  payload,
  label,
  valueFormat,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number | null; color?: string }[];
  label?: string;
  valueFormat: (v: number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 text-sm shadow-md">
      <div className="mb-1 font-medium">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-muted-foreground">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: p.color }} aria-hidden />
          {payload.length > 1 ? <span>{p.name}:</span> : null}
          <span className="font-medium tabular-nums text-foreground">
            {p.value === null || p.value === undefined ? "–" : valueFormat(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Magnitude bars in a single hue (sequential job). */
export function MagnitudeBars({
  data,
  valueLabel,
  percent = true,
  height = 260,
  onSelect,
}: {
  data: { label: string; value: number | null; id?: string }[];
  valueLabel: string;
  percent?: boolean;
  height?: number;
  onSelect?: (id: string) => void;
}) {
  const fmt = (v: number) => (percent ? pct(v) : String(v));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }} barCategoryGap={8}>
        <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
        <XAxis dataKey="label" tick={axisTick} tickLine={false} axisLine={{ stroke: "var(--border)" }} interval={0} />
        <YAxis
          tick={axisTick}
          tickLine={false}
          axisLine={false}
          domain={percent ? [0, 100] : [0, "auto"]}
          allowDecimals={false}
        />
        <Tooltip
          cursor={{ fill: "var(--muted)" }}
          content={(props) => (
            <TooltipBox
              active={props.active}
              label={String(props.label ?? "")}
              payload={props.payload?.map((p) => ({ value: p.value as number, color: "var(--chart-seq)" }))}
              valueFormat={fmt}
            />
          )}
        />
        <Bar
          dataKey="value"
          name={valueLabel}
          fill="var(--chart-seq)"
          radius={[4, 4, 0, 0]}
          maxBarSize={56}
          cursor={onSelect ? "pointer" : undefined}
          onClick={(d) => {
            const id = (d as unknown as { id?: string }).id;
            if (onSelect && id) onSelect(id);
          }}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export type Series = { key: string; name: string };

/** Change over time: percentage per exam. Series colors follow fixed slot order. */
export function ProgressLines({
  data,
  series,
  height = 260,
}: {
  data: Record<string, string | number | null>[];
  series: Series[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -12 }}>
        <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
        <XAxis dataKey="label" tick={axisTick} tickLine={false} axisLine={{ stroke: "var(--border)" }} />
        <YAxis domain={[0, 100]} tick={axisTick} tickLine={false} axisLine={false} />
        <Tooltip
          cursor={{ stroke: "var(--muted-foreground)", strokeDasharray: "3 3" }}
          content={(props) => (
            <TooltipBox
              active={props.active}
              label={String(props.label ?? "")}
              payload={props.payload?.map((p) => ({
                name: String(p.name),
                value: p.value as number | null,
                color: String(p.color),
              }))}
              valueFormat={pct}
            />
          )}
        />
        {series.length > 1 ? <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} /> : null}
        {series.map((s, i) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={`var(--chart-${(i % 6) + 1})`}
            strokeWidth={2}
            dot={{ r: 4, strokeWidth: 2, stroke: "var(--card)", fill: `var(--chart-${(i % 6) + 1})` }}
            activeDot={{ r: 6, strokeWidth: 2, stroke: "var(--card)" }}
            connectNulls
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
