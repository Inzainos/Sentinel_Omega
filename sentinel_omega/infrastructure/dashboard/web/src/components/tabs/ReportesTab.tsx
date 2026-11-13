/**
 * REPORTES — reportes publicados, veredictos del Juez y exportación.
 *
 * /api/estado-sistema-unificado → estado agregado del sistema (ok/stale/congelado/desconocido)
 * /api/reportes                 → {present, dir, files[{name, bytes, mtime}], name, content}
 * /api/juez                     → veredictos fase viva (counts + items)
 * /api/reportes/export          → CSV/JSON de veredictos del Juez
 *
 * Regla de diseño: todo número tiene su contraparte; exportar permite
 * análisis externo sin depender del tablero.
 */
import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import {
  Panel,
  Metrica,
  Cifra,
  BarraVeredictos,
  SinDatos,
  BannerError,
  TablaDatos,
} from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

export function ReportesTab() {
  const estadoF = useCallback(() => api.estadoSistemaUnificado(), []);
  const reporteF = useCallback(() => api.reportes(), []);
  const juezF = useCallback(() => api.juez(100, "viva"), []);

  const estado = usePoll(estadoF, 60000);
  const reporte = usePoll(reporteF, 60000);
  const juez = usePoll(juezF, 30000);

  const [exportFormato, setExportFormato] = useState<"json" | "csv">("json");
  const [exportando, setExportando] = useState(false);
  const [exportResultado, setExportResultado] = useState<string | null>(null);

  if (estado.error) return <BannerError mensaje={estado.error} />;
  if (estado.loading && !estado.data) return <SinDatos titulo="Cargando estado del sistema…" />;

  const es: any = estado.data ?? {};
  const files: any[] = (reporte.data?.files ?? []) as any[];
  const counts: any[] = juez.data?.counts ?? [];

  const nDe = (res: string) =>
    counts
      .filter((c) => c.fase === "viva" && c.resultado === res)
      .reduce((a, c) => a + Number(c.n ?? 0), 0);
  const aciertos = nDe("ACIERTO");
  const fallos = nDe("FALLO");
  const falsosPositivos = nDe("FALSO_POSITIVO");
  const jItems: any[] = juez.data?.items ?? [];

  const totalVeredictos = aciertos + fallos + falsosPositivos;

  const manejarExport = async () => {
    setExportando(true);
    try {
      const res = await api.reportesExport(exportFormato);
      setExportando(false);
      if (res.rows && res.rows.length > 0) {
        if (exportFormato === "csv" && res.csv) {
          const blob = new Blob([res.csv], { type: "text/csv;charset=utf-8" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `sentinel_veredictos_${new Date().toISOString().slice(0, 10)}.csv`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          setExportResultado(`CSV exportado: ${res.total} veredictos`);
        } else {
          const blob = new Blob([JSON.stringify(res.rows, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `sentinel_veredictos_${new Date().toISOString().slice(0, 10)}.json`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          setExportResultado(`JSON exportado: ${res.total} veredictos`);
        }
      } else {
        setExportResultado("Sin veredictos para exportar");
      }
    } catch (e) {
      setExportando(false);
      setExportResultado(`Error al exportar: ${String(e)}`);
    }
  };

  return (
    <div className="space-y-5">
      {/* ── Estado del sistema (Fase 2) ── */}
      <Panel
        titulo="Estado del sistema (unificado)"
        meta={`edad ${es.edad_s != null ? Math.round(Number(es.edad_s)) : "—"} s`}
        acento={es.estado === "ok" ? "LOW" : es.estado === "stale" ? "MODERATE" : "CRITICAL"}
        nota={
          <>
            Agrega salud general, APIs, overview y snapshot vivo. Fuentes
            "desconocido" o "congelado" indican que la fuente se lee pero no
            mide (Tomsk serviendo imagen estática, por ejemplo).
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-6">
          <Metrica
            etiqueta="Estado global"
            valor={
              <span
                className="mono text-foreground font-bold"
                style={{ color: es.estado === "ok" ? "var(--color-calma)" : "var(--color-critico)" }}
              >
                {es.estado === "ok" ? "OK" : es.estado === "stale" ? "STALE" : "CONGELADO/DESCONOCIDO"}
              </span>
            }
          />
          <Metrica
            etiqueta="Fuentes OK"
            valor={es.fuentes?.ok != null ? String(es.fuentes.ok) : "—"}
            contexto="fuentes vivas y midiendo"
          />
          <Metrica
            etiqueta="Fuentes STALE"
            valor={es.fuentes?.stale != null ? String(es.fuentes.stale) : "—"}
            contexto="datos con rezago"
          />
          <Metrica
            etiqueta="Fuentes CONGELADO"
            valor={es.fuentes?.congelado != null ? String(es.fuentes.congelado) : "—"}
            contexto="refresca pero no mide"
          />
          <Metrica
            etiqueta="Fuentes DESCONOCIDO"
            valor={es.fuentes?.desconocido != null ? String(es.fuentes.desconocido) : "—"}
            contexto={es.fuentes?.desconocidas_lista?.length
              ? es.fuentes.desconocidas_lista.join(", ")
              : "sin lectura válida"}
          />
          <Metrica
            etiqueta="Fantasma"
            valor={<Cifra valor={es.fantasma} digits={2} />}
          />
        </div>
      </Panel>

      {/* ── Veredictos del Juez ── */}
      <Panel
        titulo="Resumen de veredictos del Juez"
        meta={`${totalVeredictos.toLocaleString("es-MX")} veredictos vivos evaluados`}
        nota="La omisión pesa 10× más que la falsa alarma (pérdida asimétrica)."
      >
        <BarraVeredictos aciertos={aciertos} falsosPositivos={falsosPositivos} fallos={fallos} />
      </Panel>

      {/* ── Últimos veredictos ── */}
      <Panel
        titulo="Últimos veredictos del Juez"
        meta={`mostrando ${Math.min(jItems.length, 12)} de ${jItems.length}`}
      >
        <TablaDatos
          filas={jItems.slice(0, 12)}
          densa
          vacío="Sin veredictos del Juez"
          columnas={[
            { clave: "bot_name", etiqueta: "Bot" },
            { clave: "prediccion", etiqueta: "Predicción" },
            { clave: "confianza", etiqueta: "Confianza", num: true, render: (row) => <Cifra valor={row.confianza} digits={2} /> },
            {
              clave: "resultado",
              etiqueta: "Resultado",
              render: (row) => (
                <span
                  className="mono texto-micro font-bold"
                  style={{
                    color:
                      row.resultado === "ACIERTO"
                        ? "var(--color-calma)"
                        : row.resultado === "FALSO_POSITIVO"
                          ? "var(--color-aviso)"
                          : "var(--color-critico)",
                  }}
                >
                  {String(row.resultado ?? "—")}
                </span>
              ),
            },
            { clave: "resuelto_at", etiqueta: "Resuelto", render: (row) => String(row.resuelto_at ?? "—").slice(0, 16) },
          ]}
        />
      </Panel>

      {/* ── Exportación (Fase 5) ── */}
      <Panel
        titulo="Exportar veredictos del Juez"
        meta="análisis externo (CSV/JSON)"
        nota="Exporta los 5.000 veredictos más recientes (fase viva, en_vivo=1) para análisis externo sin depender del tablero."
      >
        <div className="grid gap-3 md:grid-cols-4">
          <div className="flex items-center gap-3">
            <span className="texto-meta texto-desvanecido">Formato:</span>
            <button
              onClick={() => setExportFormato("json")}
              className={`px-3 py-1.5 rounded border text-xs font-medium transition-colors ${
                exportFormato === "json"
                  ? "bg-surface-raised text-foreground border-border"
                  : "text-muted border-border/50 hover:text-foreground"
              }`}
            >
              JSON
            </button>
            <button
              onClick={() => setExportFormato("csv")}
              className={`px-3 py-1.5 rounded border text-xs font-medium transition-colors ${
                exportFormato === "csv"
                  ? "bg-surface-raised text-foreground border-border"
                  : "text-muted border-border/50 hover:text-foreground"
              }`}
            >
              CSV
            </button>
          </div>
          <button
            onClick={manejarExport}
            disabled={exportando}
            className="px-4 py-2 rounded border border-border bg-surface-raised text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exportando ? "Exportando…" : `Exportar ${exportFormato.toUpperCase()}`}
          </button>
          {exportResultado && (
            <span className={`texto-meta ${exportResultado.startsWith("Error") ? "text-critico" : "text-faint"}`}>
              {exportResultado}
            </span>
          )}
        </div>
      </Panel>

      {/* ── Reportes disponibles ── */}
      <Panel
        titulo="Reportes publicados"
        meta={`${files.length} archivos${reporte.data?.dir ? ` · ${reporte.data.dir}` : ""}`}
        nota="El último reporte publicado es REPORTE.md; los cortes históricos viven en estado/historial/AAAA/MM/."
      >
        {files.length > 0 ? (
          <TablaDatos
            filas={files}
            densa
            vacío="Sin reportes"
            columnas={[
              { clave: "name", etiqueta: "Archivo" },
              {
                clave: "bytes",
                etiqueta: "Tamaño",
                num: true,
                render: (f) => (f.bytes != null ? `${(Number(f.bytes) / 1024).toFixed(1)} KB` : "—"),
              },
              {
                clave: "mtime",
                etiqueta: "Modificado",
                num: true,
                render: (f) => (f.mtime != null ? fmtTs(Number(f.mtime)) : "—"),
              },
            ]}
          />
        ) : (
          <SinDatos
            titulo="Sin reportes disponibles"
            detalle="Ejecute una corrida del reporte para generar archivos."
          />
        )}
      </Panel>
    </div>
  );
}
