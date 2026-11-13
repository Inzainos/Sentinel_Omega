import { useEffect, useRef, useState, useMemo } from "react";

interface CimaticaPattern {
  id: string;
  ambito: string;
  event_class: string;
  frecuencia: number;
  similitud?: number;
  timestamp: number;
}

interface CimaticaLiveProps {
  patterns: CimaticaPattern[];
  currentClave?: string;
  librarySize?: number;
  hits?: number;
  width?: number;
  height?: number;
  className?: string;
  autoPlay?: boolean;
}

export function CimaticaLive({
  patterns,
  currentClave,
  librarySize,
  hits,
  width = 300,
  height = 300,
  className = "",
  autoPlay = true,
}: CimaticaLiveProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const timeRef = useRef(0);
  const [isPlaying, setIsPlaying] = useState(autoPlay);

  const currentPattern = useMemo(() => {
    if (!currentClave || !patterns.length) return null;
    return patterns.find(p => p.id === currentClave) || patterns[0];
  }, [currentClave, patterns]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = Math.min(width, height) / 2 - 20;

    let lastTime = 0;

    const draw = (timestamp: number) => {
      if (!isPlaying) {
        animationRef.current = requestAnimationFrame(draw);
        return;
      }

      const delta = (timestamp - lastTime) / 1000;
      lastTime = timestamp;
      timeRef.current += delta * 0.5;

      ctx.clearRect(0, 0, width, height);

      // Background glow
      const bgGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, maxRadius + 30);
      bgGradient.addColorStop(0, "rgba(0, 212, 255, 0.03)");
      bgGradient.addColorStop(0.5, "rgba(124, 77, 255, 0.01)");
      bgGradient.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = bgGradient;
      ctx.fillRect(0, 0, width, height);

      // Draw cymatic pattern based on current pattern
      if (currentPattern) {
        const freq = currentPattern.frecuencia || 1;
        const similitud = currentPattern.similitud || 0;
        const baseHue = similitud > 0.7 ? 180 : similitud > 0.4 ? 270 : 300; // cyan -> violet -> magenta

        // Chladni-like pattern
        const rings = 8 + Math.floor(freq / 10);
        const nodes = 4 + (freq % 6);

        for (let ring = 1; ring <= rings; ring++) {
          const radius = (ring / rings) * maxRadius;
          const phase = timeRef.current * (0.5 + ring * 0.1);

          ctx.beginPath();
          for (let angle = 0; angle <= Math.PI * 2; angle += Math.PI / 180) {
            const r = radius + Math.sin(angle * nodes + phase) * (maxRadius / rings) * 0.3 * (1 + similitud);
            const x = centerX + r * Math.cos(angle);
            const y = centerY + r * Math.sin(angle);
            if (angle === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.closePath();

          const hue = (baseHue + ring * 15) % 360;
          const opacity = 0.15 * (1 - ring / rings) * (0.5 + similitud * 0.5);
          ctx.strokeStyle = `hsla(${hue}, 80%, 60%, ${opacity})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Fill with gradient
          const fillGradient = ctx.createRadialGradient(centerX, centerY, radius * 0.8, centerX, centerY, radius);
          fillGradient.addColorStop(0, `hsla(${hue}, 80%, 60%, ${opacity * 0.3})`);
          fillGradient.addColorStop(1, `hsla(${hue}, 80%, 60%, 0)`);
          ctx.fillStyle = fillGradient;
          ctx.fill();
        }

        // Central core
        const coreSize = maxRadius * 0.15 * (1 + similitud);
        const coreGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, coreSize);
        coreGradient.addColorStop(0, `hsla(${baseHue}, 80%, 70%, 0.8)`);
        coreGradient.addColorStop(0.5, `hsla(${baseHue}, 80%, 50%, 0.4)`);
        coreGradient.addColorStop(1, `hsla(${baseHue}, 80%, 30%, 0)`);
        ctx.fillStyle = coreGradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, coreSize, 0, Math.PI * 2);
        ctx.fill();

        // Pulsing ring on high similitud
        if (similitud > 0.6) {
          const pulseRadius = coreSize + Math.sin(timeRef.current * 3) * 8 + 8;
          ctx.beginPath();
          ctx.arc(centerX, centerY, pulseRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `hsla(${baseHue}, 80%, 60%, ${0.4 * similitud})`;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      } else {
        // Idle state - subtle rotating geometry
        const rings = 5;
        for (let ring = 1; ring <= rings; ring++) {
          const radius = (ring / rings) * maxRadius * 0.7;
          const phase = timeRef.current * 0.3 + ring * 0.5;

          ctx.beginPath();
          for (let angle = 0; angle <= Math.PI * 2; angle += Math.PI / 90) {
            const r = radius + Math.sin(angle * 3 + phase) * (maxRadius / rings) * 0.15;
            const x = centerX + r * Math.cos(angle);
            const y = centerY + r * Math.sin(angle);
            if (angle === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.closePath();

          const opacity = 0.05 * (1 - ring / rings);
          ctx.strokeStyle = `rgba(0, 212, 255, ${opacity})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      // Grid reference lines
      ctx.strokeStyle = "rgba(255,255,255,0.02)";
      ctx.lineWidth = 0.5;
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(centerX + maxRadius * Math.cos(angle), centerY + maxRadius * Math.sin(angle));
        ctx.stroke();
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    animationRef.current = requestAnimationFrame(draw);

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [width, height, isPlaying, currentPattern, patterns, autoPlay]);

  return (
    <div className={`relative ${className}`} style={{ width, height }}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{ width: "100%", height: "100%", display: "block", borderRadius: "12px" }}
      />
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {currentPattern && (
          <div className="absolute bottom-3 left-3 right-3 flex flex-col gap-1 text-center">
            <div className="flex items-center justify-center gap-2 text-[10px] text-muted mono">
              <span className="px-1.5 py-0.5 rounded bg-bg-panel/80 border border-border-dim">
                {currentPattern.ambito}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-bg-panel/80 border border-border-dim">
                {currentPattern.event_class}
              </span>
            </div>
            {currentPattern.similitud !== undefined && (
              <div className="flex items-center justify-center gap-1.5">
                <span className="text-xs font-semibold" style={{ color: currentPattern.similitud > 0.7 ? "#10b981" : currentPattern.similitud > 0.4 ? "#ffc107" : "#ff9100" }}>
                  Similitud: {(currentPattern.similitud * 100).toFixed(0)}%
                </span>
                <div className="h-1.5 w-24 bg-bg-panel rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${currentPattern.similitud * 100}%`,
                      background: currentPattern.similitud > 0.7
                        ? "linear-gradient(90deg, #10b981, #00d4ff)"
                        : currentPattern.similitud > 0.4
                          ? "linear-gradient(90deg, #ffc107, #ff9100)"
                          : "linear-gradient(90deg, #ff9100, #ff1744)",
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
        {!currentPattern && (
          <div className="text-center text-muted">
            <div className="text-xs mono mb-1">ESPERANDO PATRÓN</div>
            <div className="text-[10px]">La cimática aparece al detectar firma</div>
          </div>
        )}
      </div>

      <div className="absolute top-2 right-2 flex items-center gap-2">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-1.5 rounded-lg bg-bg-panel/80 border border-border-dim hover:border-border-glow transition-colors"
          aria-label={isPlaying ? "Pausar" : "Reproducir"}
        >
          {isPlaying ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="5 3 19 12 5 21" />
            </svg>
          )}
        </button>
        <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-muted mono px-2 py-0.5 rounded bg-bg-panel/60 border border-border-dim">
          <span>Biblioteca: {librarySize?.toLocaleString() || "—"}</span>
          <span className="text-accent-cyan">Hits: {hits || "—"}</span>
        </div>
      </div>
    </div>
  );
}