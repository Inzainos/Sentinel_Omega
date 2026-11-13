import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
import { useMemo, useState } from "react";

interface AnticipacionDataPoint {
  clase: string;
  dias: number;
  events?: number;
  color?: string;
}

interface AnticipacionChartProps {
  data: AnticipacionDataPoint[];
  height?: number;
  animate?: boolean;
  className?: string;
  sortable?: boolean;
  maxBars?: number;
}

export function AnticipacionChart({
  data,
  height = 220,
  animate = true,
  className = "",
  sortable = true,
  maxBars = 10,
}: AnticipacionChartProps) {
  const [sortConfig] = useState<{ key: "dias" | "clase"; direction: "asc" | "desc" }>({ key: "dias", direction: "desc" });

  const sortedData = useMemo(() => {
    const result = [...data].slice(0, maxBars);
    if (sortable) {
      result.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [data, sortConfig, maxBars, sortable]);

  const maxDias = useMemo(() => Math.max(...sortedData.map(d => d.dias), 1), [sortedData]);

  if (!data.length) {
    return (
      <div className={`h-full flex items-center justify-center text-muted ${className}`} style={{ height }}>
        <span className="text-sm">Sin datos de anticipación</span>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sortedData} layout="vertical" margin={{ top: 10, right: 60, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="4 8" stroke="rgba(255,255,255,0.03)" vertical={true} horizontal={false} />
          <XAxis
            type="number"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
            domain={[0, maxDias * 1.2]}
            tickCount={4}
          />
          <YAxis
            dataKey="clase"
            type="category"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#a0a8b8", fontSize: 11, fontFamily: "JetBrains Mono" }}
            width={140}
            orientation="left"
            padding={{ top: 10, bottom: 10 }}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(11,12,13,0.95)",
              border: "1px solid rgba(0,212,255,0.2)",
              borderRadius: "8px",
              boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
            }}
            labelStyle={{ color: "#a0a8b8", fontFamily: "JetBrains Mono", fontSize: 11 }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) => [`${value?.toFixed(1) ?? "—"} días`, "Anticipación"]}
            labelFormatter={(label: React.ReactNode) => `Evento: ${label}`}
          />
          <Legend
            wrapperStyle={{ paddingTop: 8 }}
            formatter={() => (
              <span style={{ display: "flex", alignItems: "center", gap: 6, color: "#a0a8b8", fontSize: 11 }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: "linear-gradient(90deg, #00d4ff, #7c4dff)" }} />
                Días promedio de anticipación
              </span>
            )}
          />
          <Bar
            dataKey="dias"
            radius={[0, 6, 6, 0]}
            animationDuration={animate ? 800 : 0}
            animationEasing="ease-out"
            isAnimationActive={animate}
          >
            {sortedData.map((entry, index) => (
              <Cell
                key={`${entry.clase}-${index}`}
                fill={entry.color || (index % 2 === 0 ? "url(#anticipacionGradient1)" : "url(#anticipacionGradient2)")}
              />
            ))}
          </Bar>

          <defs>
            <linearGradient id="anticipacionGradient1" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#00d4ff" />
              <stop offset="100%" stopColor="#7c4dff" />
            </linearGradient>
            <linearGradient id="anticipacionGradient2" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#7c4dff" />
              <stop offset="100%" stopColor="#00d4ff" />
            </linearGradient>
          </defs>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}