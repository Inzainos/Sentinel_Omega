import { useEffect, useRef, useMemo } from "react";
import * as d3 from "d3";
import type { ScaleQuantize, ScaleLinear } from "d3-scale";

interface HeatmapDataPoint {
  row: string;
  col: string;
  value: number;
}

interface HeatmapD3Props {
  data: HeatmapDataPoint[];
  rows: string[];
  cols: string[];
  height?: number;
  cellSize?: number;
  colorScale?: "cyan-violet" | "risk" | "custom";
  customColors?: string[];
  showValues?: boolean;
  valueFormat?: (v: number) => string;
  onCellClick?: (row: string, col: string, value: number) => void;
  className?: string;
  caption?: string;
}

type ColorScaleFn = ScaleQuantize<string> | ScaleLinear<number, string>;

export function HeatmapD3({
  data,
  rows,
  cols,
  height = 300,
  cellSize = 28,
  colorScale = "cyan-violet",
  customColors,
  showValues = true,
  valueFormat = (v) => v.toFixed(3),
  onCellClick,
  className = "",
  caption,
}: HeatmapD3Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const colorScaleFn = useMemo((): ColorScaleFn => {
    const values = data.map(d => d.value).filter(v => v > 0);
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 1);

    if (colorScale === "risk") {
      return d3.scaleQuantize<string>()
        .domain([0, max])
        .range(["#10b981", "#ffc107", "#ff9100", "#ff1744"]) as ScaleQuantize<string>;
    }
    if (colorScale === "custom" && customColors) {
      return d3.scaleLinear<string>()
        .domain([min, max] as [number, number])
        .range(customColors) as unknown as ScaleLinear<number, string>;
    }
    return d3.scaleLinear<string>()
      .domain([min, max] as [number, number])
      .range(["#00d4ff", "#7c4dff"]) as unknown as ScaleLinear<number, string>;
  }, [data, colorScale, customColors]);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    container.innerHTML = "";

    const width = cols.length * cellSize;
    const chartHeight = rows.length * cellSize;

    const svg = d3.select(container)
      .append("svg")
      .attr("width", width + 160)
      .attr("height", chartHeight + 40)
      .style("font-family", "JetBrains Mono, monospace")
      .style("font-size", "10px");

    const g = svg.append("g")
      .attr("transform", `translate(140, 20)`);

    const cellSelection = g.selectAll<SVGGElement, HeatmapDataPoint>(".heatmap-cell")
      .data(data)
      .enter()
      .append("g")
      .attr("class", "heatmap-cell")
      .attr("transform", (d: HeatmapDataPoint) => `translate(${cols.indexOf(d.col) * cellSize}, ${rows.indexOf(d.row) * cellSize})`);

    cellSelection.append("rect")
      .attr("width", cellSize - 2)
      .attr("height", cellSize - 2)
      .attr("rx", 3)
      .attr("ry", 3)
      .attr("fill", (d: HeatmapDataPoint) => d.value > 0 ? colorScaleFn(d.value) : "rgba(255,255,255,0.02)")
      .attr("stroke", (d: HeatmapDataPoint) => d.value > 0 ? "rgba(255,255,255,0.08)" : "none")
      .attr("stroke-width", 0.5)
      .style("cursor", onCellClick ? "pointer" : "default")
      .style("transition", "fill 0.2s, stroke 0.2s")
      .on("mouseover", function (this: SVGGElement, event: MouseEvent, d: HeatmapDataPoint) {
        d3.select(this).select<SVGRectElement>("rect")
          .attr("stroke", "#00d4ff")
          .attr("stroke-width", 2);
        if (tooltipRef.current) {
          tooltipRef.current.style.opacity = "1";
          tooltipRef.current.style.left = `${event.pageX + 10}px`;
          tooltipRef.current.style.top = `${event.pageY - 10}px`;
          tooltipRef.current.innerHTML = `
            <div style="padding: 6px 10px; background: rgba(11,12,13,0.98); border: 1px solid rgba(0,212,255,0.3); border-radius: 6px; font-size: 11px;">
              <div style="color: #00d4ff; font-weight: 600; margin-bottom: 4px;">${d.row} × ${d.col}</div>
              <div style="color: #a0a8b8;">Valor: <span style="color: #f0f4f8; font-weight: 600;">${valueFormat(d.value)}</span></div>
            </div>
          `;
        }
      })
      .on("mousemove", (event: MouseEvent) => {
        if (tooltipRef.current) {
          tooltipRef.current.style.left = `${event.pageX + 10}px`;
          tooltipRef.current.style.top = `${event.pageY - 10}px`;
        }
      })
      .on("mouseout", function (this: SVGGElement, _event: MouseEvent) {
        const d = d3.select(this).datum() as HeatmapDataPoint;
        d3.select(this).select<SVGRectElement>("rect")
          .attr("stroke", d.value > 0 ? "rgba(255,255,255,0.08)" : "none")
          .attr("stroke-width", 0.5);
        if (tooltipRef.current) tooltipRef.current.style.opacity = "0";
      })
      .on("click", function (_event: MouseEvent, d: HeatmapDataPoint) {
        if (onCellClick) onCellClick(d.row, d.col, d.value);
      });

    if (showValues) {
      cellSelection.append("text")
        .attr("x", (cellSize - 2) / 2)
        .attr("y", (cellSize - 2) / 2 + 3)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .attr("fill", (d: HeatmapDataPoint) => {
          if (d.value <= 0) return "transparent";
          const color = colorScaleFn(d.value);
          const rgb = d3.color(color);
          if (!rgb) return "#f0f4f8";
          const { r, g, b } = rgb as d3.RGBColor;
          const luminance = (r * 0.299 + g * 0.587 + b * 0.114);
          return luminance > 150 ? "#050607" : "#f0f4f8";
        })
        .attr("font-size", "9px")
        .attr("font-weight", 600)
        .text((d: HeatmapDataPoint) => d.value > 0 ? valueFormat(d.value) : "—");
    }

    // Row labels
    g.selectAll<SVGTextElement, string>(".row-label")
      .data(rows)
      .enter()
      .append("text")
      .attr("class", "row-label")
      .attr("x", -8)
      .attr("y", (d: string, i: number) => i * cellSize + cellSize / 2 + 3)
      .attr("text-anchor", "end")
      .attr("dominant-baseline", "middle")
      .attr("fill", "#6b7280")
      .attr("font-size", "9px")
      .attr("font-family", "JetBrains Mono, monospace")
      .text((d: string) => d.length > 18 ? d.slice(0, 16) + "…" : d);

    // Column labels
    g.selectAll<SVGTextElement, string>(".col-label")
      .data(cols)
      .enter()
      .append("text")
      .attr("class", "col-label")
      .attr("x", (d: string, i: number) => i * cellSize + cellSize / 2)
      .attr("y", -8)
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "bottom")
      .attr("fill", "#6b7280")
      .attr("font-size", "9px")
      .attr("font-family", "JetBrains Mono, monospace")
      .attr("transform", (d: string) => `rotate(-45, ${cols.indexOf(d) * cellSize + cellSize / 2}, -8)`)
      .text((d: string) => d.length > 16 ? d.slice(0, 14) + "…" : d);

    // Legend
    const LEGEND_WIDTH = 120;
    const LEGEND_HEIGHT = 12;

    const legendGroup = g.append("g")
      .attr("transform", `translate(140, ${chartHeight + 30})`);

    const gradient = legendGroup.append("defs")
      .append("linearGradient")
      .attr("id", "heatmap-gradient")
      .attr("x1", "0%")
      .attr("x2", "100%");

    const colorRange = colorScale === "risk"
      ? ["#10b981", "#ffc107", "#ff9100", "#ff1744"]
      : colorScale === "custom" && customColors
        ? customColors
        : ["#00d4ff", "#7c4dff"];

    const stopsData = colorRange.map((color, i) => ({ color, index: i }));

    gradient.selectAll<SVGStopElement, { color: string; index: number }>("stop")
      .data(stopsData)
      .enter()
      .append("stop")
      .attr("offset", (d: { color: string; index: number }) => `${(d.index / (stopsData.length - 1)) * 100}%`)
      .attr("stop-color", (d: { color: string }) => d.color);

    legendGroup.append("rect")
      .attr("width", LEGEND_WIDTH)
      .attr("height", LEGEND_HEIGHT)
      .attr("rx", 3)
      .style("fill", "url(#heatmap-gradient)");

    const minVal = d3.min(data.map(d => d.value).filter(v => v > 0)) || 0;
    const maxVal = d3.max(data.map(d => d.value)) || 1;

    legendGroup.append("text")
      .attr("x", 0)
      .attr("y", LEGEND_HEIGHT + 14)
      .attr("fill", "#6b7280")
      .attr("font-size", "8px")
      .attr("font-family", "JetBrains Mono, monospace")
      .text(minVal.toFixed(2));

    legendGroup.append("text")
      .attr("x", LEGEND_WIDTH)
      .attr("y", LEGEND_HEIGHT + 14)
      .attr("text-anchor", "end")
      .attr("fill", "#6b7280")
      .attr("font-size", "8px")
      .attr("font-family", "JetBrains Mono, monospace")
      .text(maxVal.toFixed(2));

    if (tooltipRef.current) {
      tooltipRef.current.style.opacity = "0";
      tooltipRef.current.style.position = "fixed";
      tooltipRef.current.style.pointerEvents = "none";
      tooltipRef.current.style.zIndex = "9999";
      tooltipRef.current.style.transition = "opacity 0.15s";
      document.body.appendChild(tooltipRef.current);
    }

    return () => {
      if (tooltipRef.current) tooltipRef.current.remove();
    };
  }, [data, rows, cols, cellSize, colorScale, customColors, showValues, valueFormat, onCellClick, colorScaleFn]);

  return (
    <div className={`relative ${className}`} style={{ height }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      <div ref={tooltipRef} />
      {caption && (
        <p className="mt-3 text-xs text-muted text-center">{caption}</p>
      )}
    </div>
  );
}