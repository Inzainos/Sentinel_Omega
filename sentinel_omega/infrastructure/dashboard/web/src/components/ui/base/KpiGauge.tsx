import { useEffect, useRef, useState } from "react";

interface KpiGaugeProps {
  value: number;
  label: string;
  unit?: string;
  min?: number;
  max?: number;
  thresholds?: Array<{ value: number; color: string; label: string }>;
  size?: number;
  strokeWidth?: number;
  showValue?: boolean;
  animate?: boolean;
  className?: string;
}

const DEFAULT_THRESHOLDS = [
  { value: 25, color: "#10b981", label: "LOW" },
  { value: 50, color: "#ffc107", label: "MODERATE" },
  { value: 75, color: "#ff9100", label: "HIGH" },
  { value: 100, color: "#ff1744", label: "CRITICAL" },
];

export function KpiGauge({
  value,
  label,
  unit = "",
  min = 0,
  max = 100,
  thresholds = DEFAULT_THRESHOLDS,
  size = 120,
  strokeWidth = 8,
  showValue = true,
  animate = true,
  className = "",
}: KpiGaugeProps) {
  const [displayValue, setDisplayValue] = useState(() => animate ? min : value);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!animate) {
      // Use a timeout to avoid synchronous setState in effect
      setTimeout(() => setDisplayValue(value), 0);
      return;
    }
    const start = min;
    const end = Math.max(min, Math.min(max, value));
    const duration = 800;
    const startTime = performance.now();

    function animateFrame(now: number) {
      const progress = Math.min(1, (now - startTime) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(start + (end - start) * eased);
      if (progress < 1) {
        requestAnimationFrame(animateFrame);
      }
    }
    requestAnimationFrame(animateFrame);
  }, [value, animate, min, max]);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedValue = Math.max(min, Math.min(max, displayValue));
  const progress = (clampedValue - min) / (max - min);
  const offset = circumference * (1 - progress);

  const currentThreshold = [...thresholds].reverse().find(t => clampedValue >= t.value) || thresholds[0];

  return (
    <div className={`relative flex flex-col items-center gap-2 ${className}`} style={{ width: size, height: size + 40 }}>
      <svg ref={svgRef} width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.04)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={currentThreshold.color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{
            transition: animate ? "stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.3s" : "stroke 0.3s",
            filter: `drop-shadow(0 0 8px ${currentThreshold.color}80)`,
          }}
        />
      </svg>
      <div className="flex flex-col items-center gap-0.5">
        {showValue && (
          <span className="mono text-xl font-bold tabular-nums" style={{ color: currentThreshold.color }}>
            {clampedValue.toFixed(clampedValue < 10 ? 1 : 0)}
            {unit && <span className="text-xs font-normal text-muted ml-1">{unit}</span>}
          </span>
        )}
        <span className="text-xs font-medium uppercase tracking-wider text-muted">{label}</span>
        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded" style={{ background: `${currentThreshold.color}20`, color: currentThreshold.color }}>
          {currentThreshold.label}
        </span>
      </div>
    </div>
  );
}