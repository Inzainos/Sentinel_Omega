import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useMemo } from "react";

interface MuroDataPoint {
  timestamp: number;
  label?: string;
  walls: Record<string, number>;
  total?: number;
}

interface MuroChartProps {
  data: MuroDataPoint[];
  height?: number;
  wallNames?: string[];
  animate?: boolean;
  className?: string;
  showLegend?: boolean;
  stacked?: boolean;
}

const WALL_COLORS: Record<string, string> = {
  "Geofísico": "#00d4ff",
  "Atmosférico": "#7c4dff",
  "Oceánico": "#00ffff",
  "Solar / Geomag.": "#ff9100",
  "Financiero": "#d946ef",
};

const DEFAULT_WALLS = ["Geofísico", "Atmosférico", "Oceánico", "Solar / Geomag.", "Financiero"];

interface FormattedMuroData {
  time: string;
  [key: string]: string | number;
  total: number;
  index: number;
}

export function MuroChart({
  data,
  height = 200,
  wallNames = DEFAULT_WALLS,
  animate = true,
  className = "",
  showLegend = true,
  stacked = true,
}: MuroChartProps) {
  const formattedData = useMemo((): FormattedMuroData[] => {
    if (!data.length) return [];
    return data.map((d, i) => ({
      time: d.label || new Date(d.timestamp).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }),
      ...wallNames.reduce((acc, wall) => {
        acc[wall] = d.walls[wall] ?? 0;
        return acc;
      }, {} as Record<string, number>),
      total: d.total ?? wallNames.reduce((sum, w) => sum + (d.walls[w] ?? 0), 0),
      index: i,
    }));
  }, [data, wallNames]);

  if (!data.length) {
    return (
      <div className={`h-full flex items-center justify-center text-muted ${className}`} style={{ height }}>
        <span className="text-sm">Sin datos del Muro</span>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={formattedData}
          layout={stacked ? "vertical" : "horizontal"}
          margin={{ top: 10, right: showLegend ? 80 : 20, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="4 8" stroke="rgba(255,255,255,0.03)" vertical={false} horizontal={true} />
          <XAxis
            type="number"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
            domain={stacked ? [0, "dataMax + 1"] : undefined}
            hide={!stacked}
          />
          <YAxis
            dataKey="time"
            type="category"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
            width={60}
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
            formatter={(value: any) => [value ?? 0, ""]}
            labelFormatter={(label: React.ReactNode) => `Ciclo ${label}`}
          />
          <Legend
            wrapperStyle={{ paddingTop: 8, paddingRight: 10 }}
            formatter={(value) => (
              <span style={{ display: "flex", alignItems: "center", gap: 6, color: "#a0a8b8", fontSize: 11 }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: WALL_COLORS[value as keyof typeof WALL_COLORS] || "#6b7280" }} />
                {value}
              </span>
            )}
          />

          {wallNames.map((wall, i) => (
            <Bar
              key={wall}
              dataKey={wall}
              stackId={stacked ? "muro" : undefined}
              fill={WALL_COLORS[wall] || "#6b7280"}
              radius={stacked ? [0, 4, 4, 0] : 4}
              animationDuration={animate ? 600 : 0}
              animationEasing="ease-out"
              isAnimationActive={animate}
            >
              {formattedData.map((entry, idx) => (
                <Cell
                  key={`${wall}-${idx}`}
                  fill={
                    (entry[wall] as number) > 0
                      ? WALL_COLORS[wall] || "#6b7280"
                      : "rgba(255,255,255,0.03)"
                  }
                />
              ))}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}