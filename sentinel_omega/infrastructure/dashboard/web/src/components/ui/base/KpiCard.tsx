import { useEffect, useRef, useState } from "react";
import { IconTrendUp, IconTrendDown, IconTrendNeutral } from "@/components/icons";

interface KpiCardProps {
  label: string;
  value: string | number;
  hint?: string;
  accent?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  icon?: React.ReactNode;
  size?: "sm" | "md" | "lg";
  className?: string;
  onClick?: () => void;
}

const SIZE_CLASSES = {
  sm: "px-3 py-2.5 gap-1.5",
  md: "px-4 py-3 gap-2",
  lg: "px-5 py-4 gap-2.5",
};

const SIZE_VALUE_CLASSES = {
  sm: "text-lg",
  md: "text-2xl",
  lg: "text-3xl",
};

export function KpiCard({
  label,
  value,
  hint,
  accent,
  trend = "neutral",
  trendValue,
  icon,
  size = "md",
  className = "",
  onClick,
}: KpiCardProps) {
  const [displayValue, setDisplayValue] = useState("");
  const valueRef = useRef(value);
  const isMounted = useRef(false);

  useEffect(() => {
    isMounted.current = true;
    const strValue = String(value);
    if (strValue !== valueRef.current) {
      valueRef.current = strValue;
      setDisplayValue("");
      let i = 0;
      const interval = setInterval(() => {
        if (i < strValue.length) {
          setDisplayValue(strValue.slice(0, i + 1));
          i++;
        } else {
          clearInterval(interval);
        }
      }, 30);
      return () => clearInterval(interval);
    }
  }, [value]);

  const TrendIcon = trend === "up" ? IconTrendUp : trend === "down" ? IconTrendDown : IconTrendNeutral;
  const trendColor = trend === "up" ? "#10b981" : trend === "down" ? "#ff1744" : "#6b7280";

  return (
    <div
      className={`group relative glass card-shadow rounded-xl border border-border-dim overflow-hidden transition-all duration-200 hover:border-border-glow hover:shadow-glow-cyan ${SIZE_CLASSES[size]} ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") onClick(); } : undefined}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-[rgba(0,212,255,0.02)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      <div className="relative flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">{label}</span>
            {icon && <span className="text-muted">{icon}</span>}
          </div>
          <div className="font-bold tabular-nums text-foreground transition-colors duration-200" style={{ fontSize: SIZE_VALUE_CLASSES[size], color: accent }}>
            {displayValue || String(value)}
          </div>
          {hint && <div className="mono mt-1 text-xs text-muted truncate">{hint}</div>}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {trendValue && (
            <span className="mono text-xs font-semibold px-1.5 py-0.5 rounded-full" style={{ background: `${trendColor}20`, color: trendColor }}>
              <TrendIcon size={10} className="inline-block mr-0.5" style={{ verticalAlign: "middle" }} />
              {trendValue}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}