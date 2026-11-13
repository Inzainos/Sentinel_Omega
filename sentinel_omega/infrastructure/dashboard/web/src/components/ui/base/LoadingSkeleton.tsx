interface LoadingSkeletonProps {
  variant?: "card" | "kpi" | "table" | "chart" | "text" | "gauge";
  rows?: number;
  className?: string;
}

export function LoadingSkeleton({ variant = "card", rows = 3, className = "" }: LoadingSkeletonProps) {
  const baseStyle = {
    background: "linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(0,212,255,0.08) 50%, rgba(255,255,255,0.02) 75%)",
    backgroundSize: "200% 100%",
    animation: "shimmer 1.5s ease-in-out infinite",
    borderRadius: "8px",
  };

  const variants = {
    card: (
      <div className="space-y-3 p-4 rounded-xl glass card-shadow" style={{ minHeight: 200 }}>
        <div style={{ ...baseStyle, height: 24, width: "40%" }} />
        <div style={{ ...baseStyle, height: 40, width: "60%" }} />
        <div style={{ ...baseStyle, height: 16, width: "80%" }} />
        <div className="flex gap-2 mt-4">
          <div style={{ ...baseStyle, height: 32, width: 80, borderRadius: "9999px" }} />
          <div style={{ ...baseStyle, height: 32, width: 80, borderRadius: "9999px" }} />
        </div>
      </div>
    ),
    kpi: (
      <div className="space-y-2 p-4 rounded-xl glass card-shadow">
        <div style={{ ...baseStyle, height: 12, width: "50%" }} />
        <div style={{ ...baseStyle, height: 32, width: "70%" }} />
        <div style={{ ...baseStyle, height: 10, width: "60%" }} />
      </div>
    ),
    table: (
      <div className="space-y-2 rounded-lg overflow-hidden glass card-shadow">
        <div className="px-4 py-2" style={{ background: "rgba(255,255,255,0.02)" }}>
          <div className="flex gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{ ...baseStyle, height: 12, width: i === 0 ? "120px" : "80px" }} />
            ))}
          </div>
        </div>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="px-4 py-3 border-t border-white/5 flex gap-4">
            {Array.from({ length: 5 }).map((_, j) => (
              <div key={j} style={{ ...baseStyle, height: 14, width: j === 0 ? "120px" : "80px" }} />
            ))}
          </div>
        ))}
      </div>
    ),
    chart: (
      <div className="aspect-video rounded-xl glass card-shadow relative overflow-hidden">
        <div className="absolute inset-0" style={{ background: "rgba(255,255,255,0.01)" }} />
        <div className="absolute bottom-0 left-0 right-0 h-full" style={{ background: "linear-gradient(to top, rgba(0,212,255,0.05), transparent)" }} />
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 200" preserveAspectRatio="none">
          <defs>
            <linearGradient id="skeletonGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#7c4dff" stopOpacity="0.05" />
            </linearGradient>
          </defs>
          <path
            d="M0,180 C50,120 150,100 200,140 C250,180 350,60 400,80"
            stroke="url(#skeletonGradient)"
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ filter: "drop-shadow(0 0 8px #00d4ff80)" }}
          />
        </svg>
      </div>
    ),
    text: (
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} style={{ ...baseStyle, height: 16, width: i === 0 ? "60%" : "90%" }} />
        ))}
      </div>
    ),
    gauge: (
      <div className="flex flex-col items-center gap-3">
        <svg width="100" height="100" viewBox="0 0 100 100" className="transform -rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="8" />
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="url(#gaugeGradient)"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray="264"
            strokeDashoffset="132"
            style={{ filter: "drop-shadow(0 0 8px #00d4ff80)" }}
          />
          <defs>
            <linearGradient id="gaugeGradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#00d4ff" />
              <stop offset="100%" stopColor="#7c4dff" />
            </linearGradient>
          </defs>
        </svg>
        <div className="space-y-1">
          <div style={{ ...baseStyle, height: 28, width: "80px" }} />
          <div style={{ ...baseStyle, height: 10, width: "60px" }} />
        </div>
      </div>
    ),
  };

  return <div className={className}>{variants[variant]}</div>;
}