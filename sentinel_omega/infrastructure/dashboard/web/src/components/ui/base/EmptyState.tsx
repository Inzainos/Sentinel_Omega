import { IconInfo, IconWarning, IconSearch, IconRefresh } from "@/components/icons";

interface EmptyStateProps {
  title: string;
  description?: string;
  variant?: "info" | "warning" | "search" | "loading";
  action?: { label: string; onClick: () => void };
  className?: string;
  illustration?: React.ReactNode;
}

const VARIANT_CONFIG = {
  info: { icon: IconInfo, color: "#00d4ff", bg: "rgba(0,212,255,0.08)", border: "rgba(0,212,255,0.2)" },
  warning: { icon: IconWarning, color: "#ff9100", bg: "rgba(255,145,0,0.08)", border: "rgba(255,145,0,0.2)" },
  search: { icon: IconSearch, color: "#7c4dff", bg: "rgba(124,77,255,0.08)", border: "rgba(124,77,255,0.2)" },
  loading: { icon: IconRefresh, color: "#00d4ff", bg: "rgba(0,212,255,0.08)", border: "rgba(0,212,255,0.2)" },
};

export function EmptyState({ title, description, variant = "info", action, className = "", illustration }: EmptyStateProps) {
  const config = VARIANT_CONFIG[variant];
  const Icon = config.icon;

  return (
    <div
      className={`flex flex-col items-center justify-center gap-4 rounded-xl p-8 text-center ${className}`}
      style={{
        background: config.bg,
        border: `1px dashed ${config.border}`,
      }}
    >
      {illustration ? (
        illustration
      ) : (
        <div className="relative flex h-16 w-16 items-center justify-center rounded-xl" style={{ background: config.bg }}>
          <Icon size={32} color={config.color} className={variant === "loading" ? "animate-spin" : ""} />
        </div>
      )}
      <div className="space-y-1 max-w-sm">
        <h4 className="font-semibold text-base" style={{ color: config.color }}>{title}</h4>
        {description && <p className="text-sm text-muted leading-relaxed">{description}</p>}
      </div>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200"
          style={{
            background: `linear-gradient(135deg, ${config.color}, ${config.color}dd)`,
            color: "#050607",
            boxShadow: `0 4px 16px ${config.color}40`,
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}