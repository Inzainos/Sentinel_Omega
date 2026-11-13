import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import { useMemo } from "react";

interface DataPoint {
  timestamp: number;
  value: number;
  label?: string;
}

interface FantasmaChartProps {
  data: DataPoint[];
  height?: number;
  thresholds?: Array<{ value: number; color: string; label: string }>;
  animate?: boolean;
  className?: string;
  showGrid?: boolean;
  showLegend?: boolean;
}

const DEFAULT_THRESHOLDS = [
  { value: 10, color: "#10b981", label: "LOW" },
  { value: 30, color: "#ffc107", label: "MODERATE" },
  { value: 60, color: "#ff9100", label: "HIGH" },
  { value: 100, color: "#ff1744", label: "CRITICAL" },
];

export function FantasmaChart({
  data,
  height = 200,
  thresholds = DEFAULT_THRESHOLDS,
  animate = true,
  className = "",
  showGrid = true,
  showLegend = false,
}: FantasmaChartProps) {
  const chartData = useMemo(() => {
    if (!data.length) return { data: [] as DataPoint[], domainMax: 10 };
    const maxVal = Math.max(...data.map(d => d.value), 10);
    const maxThreshold = Math.max(...thresholds.map(t => t.value));
    const domainMax = Math.max(maxVal, maxThreshold) * 1.15;
    return { data, domainMax };
  }, [data, thresholds]);

  const formattedData = useMemo(() =>
    data.map((d, i) => ({
      ...d,
      time: d.label || new Date(d.timestamp).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" }),
      index: i,
    })),
    [data]
  );

  if (!data.length) {
    return (
      <div className={`h-full flex items-center justify-center text-muted ${className}`} style={{ height }}>
        <span className="text-sm">Sin datos para Fantasma</span>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={formattedData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="fantasmaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.35} />
              <stop offset="60%" stopColor="#7c4dff" stopOpacity={0.12} />
              <stop offset="100%" stopColor="#7c4dff" stopOpacity={0} />
            </linearGradient>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {showGrid && (
            <CartesianGrid
              strokeDasharray="4 8"
              stroke="rgba(255,255,255,0.03)"
              vertical={false}
              horizontal={true}
            />
          )}

          <XAxis
            dataKey="time"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
            interval="preserveStartEnd"
            dy={8}
          />

          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
            domain={[0, chartData.domainMax]}
            tickCount={4}
            orientation="left"
            width={40}
            mirror={true}
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
            formatter={(value: any) => [value?.toFixed(value < 10 ? 1 : 0) ?? "—", "Fantasma"]}
            labelFormatter={(label: React.ReactNode) => `Ciclo ${label}`}
          />

          {thresholds.map((t, i) => (
            <ReferenceLine
              key={i}
              y={t.value}
              stroke={t.color}
              strokeWidth={1}
              strokeDasharray="4 6"
              label={{
                value: t.label,
                position: "right",
                fill: t.color,
                fontSize: 9,
                fontFamily: "JetBrains Mono",
                fontWeight: 600,
                offset: 5,
              }}
            />
          ))}

          <Area
            type="monotone"
            dataKey="value"
            stroke="#00d4ff"
            strokeWidth={2}
            fill="url(#fantasmaGradient)"
            filter="url(#glow)"
            animationDuration={animate ? 800 : 0}
            animationEasing="ease-out"
            isAnimationActive={animate}
          />

          {showLegend && (
            <Legend
              wrapperStyle={{ paddingTop: 8 }}
              formatter={(value) => <span style={{ color: "#a0a8b8", fontSize: 11 }}>{value}</span>}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}