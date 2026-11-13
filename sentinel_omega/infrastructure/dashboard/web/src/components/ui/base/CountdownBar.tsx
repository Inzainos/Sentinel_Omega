import { useEffect, useState } from "react";

interface CountdownBarProps {
  daysRemaining?: [number, number] | null;
  daysElapsed?: number;
  active?: boolean;
  label?: string;
  className?: string;
}

export function CountdownBar({ daysRemaining, daysElapsed = 0, active = false, label = "Ventana temporal", className = "" }: CountdownBarProps) {
  const [progress, setProgress] = useState(() => {
    if (!active || !daysRemaining) return 0;
    const [start, end] = daysRemaining;
    const total = Math.max(1, end - start + 1);
    const elapsed = Math.max(0, daysElapsed);
    return Math.min(1, Math.max(0, 1 - elapsed / total));
  });
  const [timeLeft, setTimeLeft] = useState<string>(() => {
    if (!active || !daysRemaining) return "—";
    const [, end] = daysRemaining;
    const endDate = new Date(end * 1000);
    const diff = endDate.getTime() - Date.now();
    if (diff <= 0) return "0:00";
    const h = Math.floor(diff / 36e5);
    const m = Math.floor((diff % 36e5) / 6e4);
    return `${h}:${m.toString().padStart(2, "0")}`;
  });

  useEffect(() => {
    if (!active || !daysRemaining) {
      setProgress(0);
      setTimeLeft("—");
      return;
    }

    const [start, end] = daysRemaining;
    const total = Math.max(1, end - start + 1);
    const elapsed = Math.max(0, daysElapsed);
    const p = Math.min(1, Math.max(0, 1 - elapsed / total));
    setProgress(p);

    const updateTime = () => {
      const now = new Date();
      const endDate = new Date();
      endDate.setDate(now.getDate() + Math.max(0, end - elapsed));
      const diff = endDate.getTime() - now.getTime();
      if (diff <= 0) {
        setTimeLeft("Expirada");
        return;
      }
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      if (days > 0) setTimeLeft(`${days}d ${hours}h`);
      else setTimeLeft(`${hours}h`);
    };
    updateTime();
    const interval = setInterval(updateTime, 60000);
    return () => clearInterval(interval);
  }, [active, daysRemaining, daysElapsed]);

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span className="mono text-xs text-accent-cyan">{timeLeft}</span>
      </div>
      <div className="relative h-2 rounded-full bg-bg-panel overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${progress * 100}%`,
            background: active
              ? "linear-gradient(90deg, #00d4ff, #7c4dff)"
              : "linear-gradient(90deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
            boxShadow: active ? "0 0 12px #00d4ff80, 0 0 24px #7c4dff40" : "none",
          }}
        />
        {active && (
          <div className="absolute inset-y-0 left-0 rounded-full animate-shimmer" style={{ width: `${progress * 100}%` }} />
        )}
      </div>
      <div className="flex justify-between text-[10px] text-muted mono">
        <span>Hoy</span>
        {daysRemaining && <span>{daysRemaining[1]}d</span>}
      </div>
    </div>
  );
}