import { IconAlertaLow, IconAlertaMid, IconAlertaHigh, IconAlertaCritical } from "@/components/icons";

type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

const RISK_CONFIG: Record<RiskLevel, { color: string; bg: string; border: string; label: string; icon: React.ComponentType<any> }> = {
  LOW: { color: "#10b981", bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", label: "LOW", icon: IconAlertaLow },
  MODERATE: { color: "#ffc107", bg: "rgba(255,193,7,0.12)", border: "rgba(255,193,7,0.3)", label: "MODERATE", icon: IconAlertaMid },
  HIGH: { color: "#ff9100", bg: "rgba(255,145,0,0.12)", border: "rgba(255,145,0,0.3)", label: "HIGH", icon: IconAlertaHigh },
  CRITICAL: { color: "#ff1744", bg: "rgba(255,23,68,0.15)", border: "rgba(255,23,68,0.4)", label: "CRITICAL", icon: IconAlertaCritical },
};

interface RiskBadgeProps {
  level: RiskLevel;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  showIcon?: boolean;
  pulse?: boolean;
  className?: string;
}

const ICON_SIZES = { sm: 10, md: 12, lg: 14 };

export function RiskBadge({ level, size = "md", showLabel = true, showIcon = true, pulse = false, className = "" }: RiskBadgeProps) {
  const config = RISK_CONFIG[level];
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center font-semibold uppercase tracking-wider transition-all duration-200 ${pulse ? "animate-pulse-glow" : ""} ${className}`}
      style={{
        background: config.bg,
        color: config.color,
        border: `1px solid ${config.border}`,
        borderRadius: "9999px",
        ...(pulse && { boxShadow: `0 0 12px ${config.color}60` }),
      }}
    >
      {showIcon && <Icon size={ICON_SIZES[size]} className="flex-shrink-0" />}
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}