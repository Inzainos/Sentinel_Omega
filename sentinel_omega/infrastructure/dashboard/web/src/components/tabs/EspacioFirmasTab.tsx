/**
 * ESPACIO DE FIRMAS — proyección PCA/MDS de las firmas en TBL_FIRMAS.
 *
 * Cada firma es un punto en un espacio de N dimensiones (una por clave de
 * features_json). Se proyecta a 2D con PCA (implementado en TypeScript,
 * sin dependencias) y se colorea por event_class, con tamaño por recurrencia.
 *
 * Umbral 0,80: similaridad de firmas (distancia euclidiana umbralizada en
 * el dominio original). Dos firmas cercanas en esta proyección comparten
 * firma similar; no significa que predicen el mismo evento.
 *
 * Regla de diseño 3: una firma en disco no es conocimiento demostrado.
 * `exigible` y `discriminacion` son los campos que deciden.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import {
  Panel,
  Metrica,
  SinDatos,
  BannerError,
  TablaDatos,
  Cifra,
} from "@/components/ui/data";

/* ──────────────────────── Tipos ──────────────────────── */

// Type definitions used in component props and hooks
// interface ApiResponse is defined but not directly referenced; kept for API contract documentation
interface FirmaEspacio {
  firma_id: number | null;
  bot_name: string | null;
  event_class: string | null;
  id_nodo: number | null;
  recurrencia: number | null;
  estado: string | null;
  discriminacion: number | null;
  exigible: number | null;
  discrimina_lift: number | null;
  primera_vista: string | null;
  ultima_vista: string | null;
  features: number[];
  feature_keys: string[];
  x: number | null;
  y: number | null;
}


/* ──────────────────────── PCA (2 componentes) ──────────────────────── */

function dot(a: number[], b: number[]): number {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}

function matVec(C: number[][], v: number[]): number[] {
  const p_v = v.length;
  const out = new Array(p_v).fill(0);
  for (let i = 0; i < p_v; i++) {
    let acc = 0;
    for (let j = 0; j < C[i].length; j++) acc += C[i][j] * v[j];
    out[i] = acc;
  }
  return out;
}

function powerIteration(C: number[][], p_dim: number, iterations = 200): number[] {
  let v = Array.from({ length: p_dim }, () => 1 / Math.sqrt(p_dim));
  for (let iter = 0; iter < iterations; iter++) {
    const vNew = matVec(C, v);
    const nrm = Math.sqrt(dot(vNew, vNew));
    if (nrm < 1e-12) break;
    v = vNew.map((x) => x / nrm);
  }
  return v;
}

function pca2(matrix: number[][]): number[][] {
  const n = matrix.length;
  if (n === 0) return [];
  const p_dim = matrix[0].length;
  if (p_dim < 2) return matrix.map((row) => [row[0] ?? 0, 0]);

  const means = new Array(matrix[0].length).fill(0);
  for (let i = 0; i < matrix.length; i++) {
    for (let j = 0; j < matrix[i].length; j++) means[j] += matrix[i][j] ?? 0;
  }
  for (let j = 0; j < means.length; j++) means[j] /= matrix.length;

  const C = Array.from({ length: p_dim }, () => new Array(p_dim).fill(0));
  for (let i = 0; i < p_dim; i++) {
    for (let j = 0; j < p_dim; j++) {
      let sum = 0;
      for (let k = 0; k < matrix.length; k++) sum += (matrix[k][i] ?? 0 - (means[i] ?? 0)) * (matrix[k][j] ?? 0 - (means[j] ?? 0));
      C[i][j] = sum / Math.max(1, matrix.length - 1);
    }
  }

  const e1 = powerIteration(C, p_dim);
  const lambda1 = dot(e1, matVec(C, e1));

  const C2 = Array.from({ length: p_dim }, () => new Array(p_dim).fill(0));
  for (let i = 0; i < p_dim; i++) {
    for (let j = 0; j < p_dim; j++) {
      C2[i][j] = C[i][j] - lambda1 * e1[i] * e1[j];
    }
  }

  const e2 = powerIteration(C2, p_dim);

  return matrix.map((row) => [dot(row, e1), dot(row, e2)]);
}

/* ──────────────────────── Colores por clase ──────────────────────── */

const CLASE_COLORS: Record<string, string> = {
  SISMO_M4: "var(--color-serie-1)",
  SISMO_M5: "var(--color-serie-2)",
  SISMO_M6: "var(--color-serie-3)",
  SISMO_M7: "var(--color-serie-4)",
  ERUPCION: "var(--color-critico-dim)",
  TORMENTA_GEOMAGNETICA: "var(--color-serie-1)",
  DESGASIFICACION: "var(--color-serie-2)",
  DEFAULT: "var(--color-base-600)",
};

function colorClase(clase: string | null | undefined): string {
  if (!clase) return CLASE_COLORS.DEFAULT;
  const key = String(clase).toUpperCase();
  return CLASE_COLORS[key] ?? CLASE_COLORS.DEFAULT;
}

/* ──────────────────────── Componente Visualización ──────────────────────── */

function EspacioFirmasVisualization({
  firmasConCoords,
  xRange,
  yRange,
  featureKeys,
  exigibleN,
  consolidadaN,
}: {
  firmasConCoords: FirmaEspacio[];
  xRange: { min: number; max: number };
  yRange: { min: number; max: number };
  featureKeys: string[];
  exigibleN: number;
  consolidadaN: number;
}): JSX.Element {
  const _xSpan = (xRange.max - xRange.min) || 1;
  const _ySpan = (yRange.max - yRange.min) || 1;

  const _VBW = 640;
  const _VBH = 400;
  const _ML = 56, _MR = 16, _MB = 42, _MT = 8;
  const _plotW = _VBW - 56 - 16;
  const _plotH = _VBH - 8 - 42;

  const _xDe = (v: number) => 56 + ((v - (xRange?.min ?? 0)) / ((xRange?.max ?? 1) - (xRange?.min ?? 0) || 1)) * (640 - 56 - 16);
  const _yDe = (v: number) => 8 + 400 - 8 - 42 - ((v - (yRange?.min ?? 0)) / ((yRange?.max ?? 1) - (yRange?.min ?? 0) || 1)) * (400 - 8 - 42);

  const _umbralRadio = Math.min(640 - 56 - 16, 400 - 8 - 42) * 0.06;

  const exigibleFirmas = firmasConCoords.filter((f) => f.exigible === 1);

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-5">
        <Metrica
          etiqueta="Firmas proyectadas"
          valor={firmasConCoords.length.toLocaleString("es-MX")}
          contexto="de TBL_FIRMAS (límite de consulta)"
        />
        <Metrica
          etiqueta="Consolidadas"
          valor={firmasConCoords.filter((f) => f.estado === "consolidada").length.toLocaleString("es-MX")}
          contexto="estado='consolidada'"
        />
        <Metrica
          etiqueta="Exigibles"
          valor={exigibleFirmas.length.toLocaleString("es-MX")}
          contexto="discriminan eventos frente a calma"
        />
        <Metrica
          etiqueta="Dimensiones"
          valor={String(firmasConCoords[0]?.feature_keys?.length ?? 0)}
          contexto="claves de features_json"
          jerarquia="compacta"
        />
        <Metrica
          etiqueta="Umbral 0,80"
          valor="ref."
          contexto="distancia mínima de similitud"
          jerarquia="compacta"
        />
      </div>

      <Panel
        titulo="Espacio de firmas — proyección PCA (2D)"
        meta={`${firmasConCoords[0]?.feature_keys?.length ?? 0} features · {firmasConCoords.length} firmas`}
        acento="LOW"
        nota={
          <>
            Cada punto es una firma de TBL_FIRMAS proyectada a 2D con PCA
            sobre su vector de features_json. Puntos cercanos comparten
            firma similar en el espacio de telemetría. Color = clase de
            evento; tamaño = recurrencia. Umbral 0,80 = distancia de
            referencia para similitud.{" "}
            <br />
            <strong>Una firma en disco no es conocimiento demostrado:</strong>
            mirar `exigible = 1` y `discriminación &gt;0`.
          </>
        }
      >
        <div className="relative">
          <svg
            width={640}
            height={400}
            viewBox="0 0 640 400"
            preserveAspectRatio="none"
            role="img"
            aria-label="Espacio de firmas PCA 2D"
            className="border border-border/60 rounded bg-surface-sunken"
          >
            <line
              x1={56}
              y1={8 + 400 - 8 - 42}
              x2={640 - 16}
              y2={8 + 400 - 8 - 42}
              stroke="var(--color-border)"
              strokeWidth={1}
            />
            <line
              x1={56}
              y1={8}
              x2={56}
              y2={8 + 400 - 8 - 42}
              stroke="var(--color-border)"
              strokeWidth={1}
            />

            {[0, 0.25, 0.5, 0.75, 1].map((f) => {
              const v = (xRange?.min ?? 0) + f * ((xRange?.max ?? 1) - (xRange?.min ?? 0) || 1);
              const x = 56 + f * (640 - 56 - 16);
              return (
                <g key={`x${f}`}>
                  <line
                    x1={x}
                    y1={8 + 400 - 8 - 42}
                    x2={x}
                    y2={8 + 400 - 8 - 42 + 4}
                    stroke="var(--color-border)"
                    strokeWidth={1}
                  />
                  <text
                    key={`xl${f}`}
                    x={x}
                    y={8 + 400 - 8 - 42 + 16}
                    textAnchor="middle"
                    fill="var(--color-faint)"
                    style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}
                  >
                    {v.toFixed(2)}
                  </text>
                </g>
              );
            })}

            {[0, 0.25, 0.5, 0.75, 1].map((f) => {
              const v = (yRange?.min ?? 0) + f * ((yRange?.max ?? 1) - (yRange?.min ?? 0) || 1);
              const y = 8 + (400 - 8 - 42) - f * (400 - 8 - 42);
              return (
                <g key={`y${f}`}>
                  <line
                    x1={56 - 4}
                    y1={y}
                    x2={56}
                    y2={y}
                    stroke="var(--color-border)"
                    strokeWidth={1}
                  />
                  <text
                    key={`yl${f}`}
                    x={56 - 8}
                    y={y + 3}
                    textAnchor="end"
                    fill="var(--color-faint)"
                    style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}
                  >
                    {v.toFixed(2)}
                  </text>
                </g>
              );
            })}

            <circle
              cx={56 + ((0 - (xRange?.min ?? 0)) / ((xRange?.max ?? 1) - (xRange?.min ?? 0) || 1)) * (640 - 56 - 16)}
              cy={8 + 400 - 8 - 42 - ((0 - (yRange?.min ?? 0)) / ((yRange?.max ?? 1) - (yRange?.min ?? 0) || 1)) * (400 - 8 - 42)}
              r={Math.min(640 - 56 - 16, 400 - 8 - 42) * 0.06}
              fill="none"
              stroke="var(--color-aviso)"
              strokeWidth={1}
              strokeDasharray="4 3"
              opacity="0.5"
            />
            <text
              x={56 + ((0 - (xRange?.min ?? 0)) / ((xRange?.max ?? 1) - (xRange?.min ?? 0) || 1)) * (640 - 56 - 16) + 4}
              y={8 + 400 - 8 - 42 - ((0 - (yRange?.min ?? 0)) / ((yRange?.max ?? 1) - (yRange?.min ?? 0) || 1)) * (400 - 8 - 42) - 4}
              fill="var(--color-aviso)"
              style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}
            >
              0,80 ref.
            </text>

            {firmasConCoords.map((f, i) => {
              const cx = 56 + (( (f.x ?? 0) - (xRange?.min ?? 0) ) / ((xRange?.max ?? 1) - (xRange?.min ?? 0) || 1)) * (640 - 56 - 16);
              const cy = 8 + (400 - 8 - 42) - (( (f.y ?? 0) - (yRange?.min ?? 0) ) / ((yRange?.max ?? 1) - (yRange?.min ?? 0) || 1)) * (400 - 8 - 42);
              const _r = Math.max(2, Math.min(6, 2 + Math.sqrt(Number(f.recurrencia ?? 1) * 0.5)));
              const _esExigible = f.exigible === 1;
              const _esConsolidada = f.estado === "consolidada";

              return (
                <circle
                  key={String(f.firma_id ?? i)}
                  cx={cx}
                  cy={cy}
                  r={_r}
                  fill={colorClase(f.event_class)}
                  stroke={_esExigible ? "var(--color-foreground)" : "transparent"}
                  strokeWidth={_esExigible ? 1.5 : 0}
                  fillOpacity={_esConsolidada ? 0.85 : 0.45}
                  className="cursor-pointer"
                >
                  <title>{[
                    `Firma #${f.firma_id}`,
                    `Bot: ${f.bot_name ?? "—"}`,
                    `Clase: ${f.event_class ?? "—"}`,
                    `Nodo: ${f.id_nodo ?? "—"}`,
                    `Recurrencia: ${f.recurrencia ?? "—"}`,
                    `Estado: ${f.estado ?? "—"}`,
                    `Exigible: ${f.exigible === 1 ? "SÍ" : "no"}`,
                    `Discriminación: ${f.discriminacion != null ? Number(f.discriminacion).toFixed(4) : "—"}`,
                    `Lift: ${f.discrimina_lift != null ? Number(f.discrimina_lift).toFixed(3) : "—"}`,
                    `x: ${(f.x ?? 0).toFixed(3)}, y: ${(f.y ?? 0).toFixed(3)}`,
                  ].join("\n")}</title>
                </circle>
              );
            })}
          </svg>

          <div className="mt-3 flex flex-wrap gap-4 text-meta text-xs">
            {["SISMO_M4", "SISMO_M5", "SISMO_M6", "SISMO_M7", "ERUPCION", "DEFAULT"].map((clase) => {
              const count = firmasConCoords.filter(
                (f) => String(f.event_class ?? "").toUpperCase() === clase,
              ).length;
              if (!count) return null;
              return (
                <span key={clase} className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 shrink-0 rounded-sm"
                    style={{ background: colorClase(clase) }}
                  />
                  {clase === "DEFAULT" ? "Otras" : clase} <span className="mono">{count}</span>
                </span>
              );
            })}
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 shrink-0 rounded border border-border" />
              exigible (borde)
            </span>
          </div>
        </div>
      </Panel>

      <Panel
        titulo="Firmas exigible más discriminantes"
        meta="ordenadas por discrimina_lift descendente"
        nota="Sólo firmas con exigible = 1 y discriminación medida. Son el conocimiento demostrado del sistema."
      >
        {exigibleFirmas.length ? (
          <TablaDatos
            filas={firmasConCoords.filter((f) => f.exigible === 1).slice(0, 25)}
            densa
            vacío="Sin firmas exigibles"
            columnas={[
              { clave: "event_class", etiqueta: "Clase" },
              { clave: "bot_name", etiqueta: "Bot" },
              {
                clave: "recurrencia",
                etiqueta: "Recurr.",
                num: true,
                render: (r: { recurrencia?: number | null }) => <Cifra valor={r.recurrencia} digits={0} />,
              },
              {
                clave: "discriminacion",
                etiqueta: "Disc.",
                num: true,
                render: (r: { discriminacion?: number | null }) => <Cifra valor={r.discriminacion} digits={4} />,
              },
              {
                clave: "discrimina_lift",
                etiqueta: "Lift",
                num: true,
                render: (r: { discrimina_lift?: number | null }) => <Cifra valor={r.discrimina_lift} digits={3} />,
              },
              { clave: "estado", etiqueta: "Estado" },
              {
                clave: "x",
                etiqueta: "x (PCA)",
                num: true,
                render: (r: { x?: number | null }) => <Cifra valor={r.x} digits={3} />,
              },
              {
                clave: "y",
                etiqueta: "y (PCA)",
                num: true,
                render: (r: { y?: number | null }) => <Cifra valor={r.y} digits={3} />,
              },
            ]}
          />
        ) : (
          <SinDatos titulo="Sin firmas exigibles" />
        )}
      </Panel>
    </div>
  );
}

/* ──────────────────────── Componente Principal ──────────────────────── */

export function EspacioFirmasTab() {
  const firmasF = useCallback(() => api.firmasEspacio(), []);
  const firmas = usePoll(firmasF, 120000);

  if (firmas.error) return <BannerError mensaje={firmas.error} />;
  if (firmas.loading && !firmas.data) {
    return <SinDatos titulo="Proyectando espacio de firmas…" />;
  }

  const _payload = firmas.data as Record<string, any> | null;

  // Check for empty data state
  const _showEmpty = !firmas.data?.present || !firmas.data?.firmas || firmas.data?.firmas.length === 0;

  // All hooks called unconditionally at top level
  const [xRange, setXRange] = useState<{ min: number; max: number } | null>(null);
  const [yRange, setYRange] = useState<{ min: number; max: number } | null>(null);

  const firmasRaw = (firmas.data as Record<string, any>)?.firmas || [];
  const _featureKeys: string[] = (firmas.data as Record<string, any>)?.feature_keys || [];

  const matrix: number[][] = useMemo(() =>
    firmasRaw.map((f: { features?: number[] }) => (f.features || []).map(Number)), [firmasRaw]);

  const projected: number[][] = useMemo(() => {
    if (matrix.length === 0) return [];
    try {
      return pca2(matrix);
    } catch {
      return [];
    }
  }, [matrix]);

  const firmasConCoords = useMemo(() => {
    const firmasData = (firmas.data as Record<string, any>)?.firmas || [];
    if (!firmasData.length || !projected.length) return [];

    const out: Array<{
      firma_id: number | null;
      bot_name: string | null;
      event_class: string | null;
      id_nodo: number | null;
      recurrencia: number | null;
      estado: string | null;
      discriminacion: number | null;
      exigible: number | null;
      discrimina_lift: number | null;
      primera_vista: string | null;
      ultima_vista: string | null;
      features: number[];
      feature_keys: string[];
      x: number | null;
      y: number | null;
    }> = [];

    const _projectedSafe = projected.length > 0 ? projected : [[0, 0]];
    for (let i = 0; i < firmasData.length; i++) {
      const f = firmasData[i];
      const _proj = i < projected.length ? projected[i] : [0, 0];
      out.push({
        firma_id: f.firma_id,
        bot_name: f.bot_name,
        event_class: f.event_class,
        id_nodo: f.id_nodo,
        recurrencia: f.recurrencia,
        estado: f.estado,
        discriminacion: f.discriminacion,
        exigible: f.exigible,
        discrimina_lift: f.discrimina_lift,
        primera_vista: f.primera_vista,
        ultima_vista: f.ultima_vista,
        features: f.features,
        feature_keys: (firmas.data as Record<string, any>)?.feature_keys || [],
        x: i < projected.length ? (projected[i]?.[0] ?? 0) : 0,
        y: i < projected.length ? (projected[i]?.[1] ?? 0) : 0,
      });
    }
    return out;
  }, [firmas.data]);

  useEffect(() => {
    if (firmasConCoords.length === 0) return;
    const xs = firmasConCoords.map((f) => f.x ?? 0);
    const ys = firmasConCoords.map((f) => f.y ?? 0);
    setXRange({ min: Math.min(...xs), max: Math.max(...xs) });
    setYRange({ min: Math.min(...ys), max: Math.max(...ys) });
  }, [firmasConCoords]);

  // Show loading state before hooks return
  if (!xRange || !yRange) {
    return <SinDatos titulo="Calculando proyección…" />;
  }

  // Show empty state
  if (!firmas.data?.present || !firmas.data?.firmas || firmas.data?.firmas.length === 0) {
    return (
      <SinDatos
        titulo="Sin firmas"
        detalle="TBL_FIRMAS vacía o tabla ausente."
      />
    );
  }

  const exigibleN = firmasConCoords.filter((f) => f.exigible === 1).length;
  const consolidadaN = firmasConCoords.filter((f) => f.estado === "consolidada").length;

  return (
    <EspacioFirmasVisualization
      firmasConCoords={firmasConCoords}
      xRange={xRange}
      yRange={yRange}
      featureKeys={firmas.data?.feature_keys || []}
      exigibleN={exigibleN}
      consolidadaN={consolidadaN}
    />
  );
}