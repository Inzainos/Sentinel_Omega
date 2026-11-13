import { IconMuro } from "@/components/icons";

interface WallSegmentProps {
  name: string;
  types: string[];
  active: boolean;
  activeTypes?: Set<string>;
  className?: string;
}

const ICON_COLORS: Record<string, string> = {
  "Geofísico": "#00d4ff",
  "Atmosférico": "#7c4dff",
  "Oceánico": "#00ffff",
  "Solar / Geomag.": "#ff9100",
  "Financiero": "#d946ef",
};

export function WallSegment({ name, types, active, activeTypes = new Set(), className = "" }: WallSegmentProps) {
  const color = ICON_COLORS[name] || "#00d4ff";

  return (
    <div
      className={`relative flex flex-col gap-2 rounded-xl p-4 transition-all duration-300 ${className}`}
      style={{
        background: active ? `linear-gradient(135deg, ${color}15, ${color}05)` : "rgba(17,18,20,0.7)",
        border: active ? `1px solid ${color}50` : "1px solid rgba(255,255,255,0.06)",
        boxShadow: active ? `0 0 24px ${color}30, inset 0 1px 0 ${color}20` : "none",
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative flex h-8 w-8 items-center justify-center rounded-lg" style={{ background: active ? `${color}20` : "rgba(255,255,255,0.04)" }}>
            <IconMuro size={16} color={active ? color : "rgba(255,255,255,0.3)"} strokeWidth={2} />
            {active && (
              <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full animate-pulse" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
            )}
          </div>
          <span className="font-semibold text-sm" style={{ color: active ? color : "inherit" }}>{name}</span>
        </div>
        <span className="h-2 w-2 rounded-full transition-all duration-300" style={{ background: active ? color : "rgba(255,255,255,0.1)", boxShadow: active ? `0 0 8px ${color}` : "none" }} />
      </div>
      <div className="flex flex-wrap gap-1.5">
        {types.map((type) => {
          const isActive = activeTypes.has(type.toUpperCase().replace(/[^A-Z]/g, ""));
          return (
            <span
              key={type}
              className="mono rounded px-2 py-0.5 text-[10px] font-medium transition-all duration-200"
              style={{
                background: isActive ? `${color}20` : "rgba(255,255,255,0.05)",
                color: isActive ? color : "rgba(138,143,152,0.7)",
                border: isActive ? `1px solid ${color}40` : "none",
              }}
            >
              {type}
            </span>
          );
        })}
      </div>
    </div>
  );
}