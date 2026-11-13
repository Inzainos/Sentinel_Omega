import { useCallback, useMemo } from "react"
import { api } from "@/lib/api"
import { usePoll } from "@/hooks/usePoll"
import { KpiCard } from "@/components/ui/base"
import { AskBox } from "@/components/AskBox"
import { TabIntro, Caption } from "@/components/TabIntro"
import { DataTable } from "@/components/DataTable"
import { FantasmaChart, MuroChart, CimaticaLive } from "@/components/charts"
import { Map2D } from "@/components/maps/Map2D"
import { fmtNum, fmtTs } from "@/lib/utils"

export function PrincipalTab() {
  const ovF = useCallback(() => api.overview(), [])
  const alF = useCallback(() => api.alertas(20), [])
  const ciF = useCallback(() => api.cimatica(30), [])
  const caF = useCallback(() => api.cimaticaAhora(), [])
  const nF = useCallback(() => api.nodos(), [])
  const sF = useCallback(() => api.sismos(4.5, 40), [])
  const cycF = useCallback(() => api.ciclos(40), [])
  const corrF = useCallback(() => api.correlaciones(), [])
  const repF = useCallback(() => api.reportes(), [])
  const tgF = useCallback(() => api.telegramStatus(), [])
  const precF = useCallback(() => api.precursores(40), [])
  const acF = useCallback(() => api.bots(), [])
  const hmF = useCallback(() => api.heatmaps(), [])

  const ov = usePoll(ovF, 20000)
  const al = usePoll(alF, 20000)
  const ci = usePoll(ciF, 30000)
  const ca = usePoll(caF, 30000)
  const n = usePoll(nF, 30000)
  const s = usePoll(sF, 30000)
  const cyc = usePoll(cycF, 20000)
  const corr = usePoll(corrF, 60000)
  const rep = usePoll(repF, 60000)
  const tg = usePoll(tgF, 60000)
  const prec = usePoll(precF, 20000)
  const ac = usePoll(acF, 60000)
  const hm = usePoll(hmF, 60000)

  const acData = ac.data as Record<string, unknown> | undefined
  const asertVivaGlobal = acData?.asertividad_viva_global
  const asertGlobal = asertVivaGlobal != null ? `${(Number(asertVivaGlobal) * 100).toFixed(1)}%` : "---"
  const gananciaReal = acData?.ganancia_real != null ? `${Number(acData.ganancia_real).toFixed(2)}x` : "---"
  const tmx = (hm.data?.telemetry_x_events || {}) as {
    present?: boolean
    features?: string[]
    events?: string[]
    matrix?: number[][]
  }

  const data = ov.data
  const risk = Object.entries(data?.risk_distribution || {}).map(([name, value]) => ({
    name,
    value: Number(value),
  }))
  const nivel = data?.fantasma?.nivel_riesgo || ""
  const calm =
    !["HIGH", "CRITICAL"].includes(String(nivel).toUpperCase()) && !data?.muro?.muro_breach

  const nodes = useMemo(
    () =>
      (n.data || [])
        .map((nd: any) => ({
          lat: Number(nd.lat),
          lon: Number(nd.lon),
          tipo: String(nd.tipo || ""),
          label: String(nd.nombre || ""),
          highlight:
            String(nd.nombre || "").toLowerCase().includes("tlaxcala") && String(nd.tipo) === "real",
        }))
        .filter((p: any) => Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [n.data],
  )
  const quakes = (s.data?.items || [])
    .map((q: any) => ({
      lat: Number(q.lat),
      lon: Number(q.lon),
      mag: Number(q.magnitude),
      label: String(q.region || ""),
    }))
    .filter((p: any) => Number.isFinite(p.lat) && Number.isFinite(p.lon))

  const fantasmaSpark = [...(cyc.data || [])]
    .reverse()
    .map((r, i) => ({ i, y: Number(r.fantasma ?? 0) }))

  const geo = ((al.data?.geo_alerts as Record<string, unknown>[]) || []).slice(0, 5)
  const breaches = ((al.data?.muro_breaches as Record<string, unknown>[]) || []).slice(0, 5)
  const hot = ((al.data?.hot_fantasma as Record<string, unknown>[]) || []).slice(0, 5)
  const topAlertas = [
    ...geo.map((r: any) => ({ ...r, _kind: "geo" })),
    ...breaches.map((r: any) => ({ ...r, _kind: "muro" })),
    ...hot.map((r: any) => ({ ...r, _kind: "fantasma" })),
  ].slice(0, 8)

  const padre: any = corr.data?.padre

  if (ov.error) return <div className="p-4 text-red-500">Error: {ov.error}</div>
  if (ov.loading && !ov.data) return <div className="p-4 text-muted">Cargando Principal...</div>

  const caData = ca.data || {}
  const tgData = tg.data || {}
  const repFiles = rep.data?.files || []

  return (
    <div className="space-y-6">
      <TabIntro title="Principal - pulso del sistema">
        <p>
          Vista unificada: Fantasma, Muro, telemetria, cimatica en vivo, alertas top y un mini mapa. Los numeros
          salen de SQLite en modo lectura. No es un juguete de prediccion ni un consejo de compra.
        </p>
        <p>
          {calm
            ? "Lectura actual: calma relativa. No hay que llamar a nadie solo por este tablero."
            : "Lectura actual: el sistema esta inquieto (riesgo alto o Muro roto). Revise alertas abajo y avise a quien corresponda."}
        </p>
      </TabIntro>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">FANTASMA</h4>
          <div className="text-3xl font-bold text-foreground">{Number(data?.fantasma?.value ?? 0)}</div>
          <div className="text-xs text-muted">indice de riesgo cosmico</div>
        </div>
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">MURO</h4>
          <div className="text-3xl font-bold text-foreground">{Number(data?.muro?.walls_active ?? 0)} / 5</div>
          <div className="text-xs text-muted">{data?.muro?.muro_breach ? "BREACH: 3+ paredes activas" : "sin rotura"}</div>
        </div>
        <KpiCard
          label="ASERTIVIDAD GLOBAL"
          value={asertGlobal}
          accent="#10b981"
          hint="aciertos/(aciertos+fallos) - cuenta los silencios, sin falsos positivos"
          size="md"
        />
        <KpiCard
          label="GANANCIA REAL"
          value={gananciaReal}
          accent="#ff9100"
          hint="precision de la alarma / tasa base * 1x = no aporta"
          size="md"
        />
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">NODOS</h4>
          <div className="text-3xl font-bold text-foreground">{data?.counts?.nodos ?? "---"}</div>
          <div className="text-xs text-muted">125 puntos de topologia</div>
        </div>
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">SISMOS &ge;4.5</h4>
          <div className="text-3xl font-bold text-foreground">{data?.counts?.sismos_m45 ?? "---"}</div>
          <div className="text-xs text-muted">umbral de alerta del Padre</div>
        </div>
      </div>

      <Caption>
        LOW &gt;5 calma - MODERATE 5-15 atencion - HIGH 15-30 avisar - CRITICAL &ge;30 protocolo. El Muro se rompe con 3
        de 5 paredes.
      </Caption>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <div className="space-y-4">
          <h4 className="text-sm font-medium">Fantasma (ultimos 40 ciclos)</h4>
          {fantasmaSpark.length ? (
            <FantasmaChart
              data={[...(cyc.data || [])].reverse().map((r, i) => ({
                // Use relative timestamps from base time to avoid impure Date.now() in render
                timestamp: (performance.now() / 1000) - (40 - i) * 60,
                value: Number(r.fantasma ?? 0),
              }))}
              height={160}
              animate
            />
          ) : (
            <Caption>Sin ciclos para sparkline.</Caption>
          )}
        </div>
        <div className="space-y-4">
          <h4 className="text-sm font-medium">Muro de los 5 (ultimos 40 ciclos)</h4>
          <MuroChart
            data={cyc.data || []}
            height={160}
            animate
          />
        </div>
        <div className="space-y-4">
          <h4 className="text-sm font-medium">Distribucion de riesgo</h4>
          {risk.length ? (
            <div className="h-48">
              <canvas id="risk-pie" />
            </div>
          ) : (
            <Caption>Sin distribucion de riesgo en esta DB.</Caption>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Mini mapa - nodos + sismos &ge;4.5</h4>
          <Map2D nodes={nodes} quakes={quakes} highlight={{ lat: 19.31, lon: -98.23, label: "Tlaxcala" }} />
        </div>
        <div className="space-y-3">
          <h4 className="text-sm font-medium">Cimatica ahora</h4>
          <CimaticaLive
            patterns={ci.data?.items || []}
            currentClave={ca.data?.current_clave}
            librarySize={ca.data?.biblioteca_n}
            hits={ca.data?.library?.n_hits}
            width={300}
            height={300}
          />
          <Caption>
            Clave actual: {String(caData.current_clave || "---")}.{" "}
            {String(caData.caption || "Lookup live vs biblioteca; sin entrenamiento.")}
          </Caption>
        </div>
      </div>

      <section className="space-y-2">
        <h4 className="text-sm font-medium">Top alertas</h4>
        <DataTable
          rows={topAlertas}
          empty="Sin alertas activas - todo en verde segun umbrales."
          columns={[
            { key: "_kind", label: "Tipo" },
            { key: "timestamp", label: "Tiempo", render: (r: any) => fmtTs(r.timestamp) },
            {
              key: "fantasma",
              label: "Fantasma",
              render: (r: any) => (r.fantasma != null ? fmtNum(r.fantasma) : "---"),
            },
            {
              key: "nivel_riesgo",
              label: "Riesgo",
              render: (r: any) => String(r.nivel_riesgo || r.risk_label || r.geo_signal || "---"),
            },
          ]}
        />
      </section>

      {tmx.present && (tmx.features?.length || 0) > 0 ? (
        <section className="space-y-2">
          <h4 className="text-sm font-medium">Mapa de calor - telemetria x evento</h4>
          <div className="h-64">
            <canvas id="heatmap-chart" />
          </div>
        </section>
      ) : null}

      <section className="space-y-2">
        <h4 className="text-sm font-medium">Mini heatmap correlaciones (Padre)</h4>
        {padre?.present && (padre.patrones?.length || 0) > 0 ? (
          <div className="h-64">
            <canvas id="padre-heatmap-chart" />
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-bg-card p-4 text-center text-muted">
            Sin correlaciones padre en esta DB
            <p className="text-xs mt-1">tbl_correlaciones_padre vacia hasta re-entrenar. No se inventan celdas.</p>
          </div>
        )}
      </section>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-border bg-bg-card/40 px-3 py-3 text-xs">
          <div className="font-medium text-sm mb-1">Reportes (estado/)</div>
          {rep.data?.present ? (
            <ul className="space-y-0.5 text-muted">
              {repFiles.slice(0, 5).map((f: any) => (
                <li key={f.name} className="mono">
                  {f.name} - {(f.bytes / 1024).toFixed(1)} KB
                </li>
              ))}
              {!repFiles.length ? <li>Carpeta presente, sin archivos.</li> : null}
            </ul>
          ) : (
            <p className="text-muted">Sin carpeta estado/ en este arbol.</p>
          )}
        </div>
        <div className="rounded-xl border border-border bg-bg-card/40 px-3 py-3 text-xs">
          <div className="font-medium text-sm mb-1">Telegram</div>
          <p className={tgData.configured ? "text-success" : "text-warning"}>
            {tgData.configured ? "Configurado" : "No configurado / dry-run"}
          </p>
          <p className="text-muted mt-1">
            token={String(tgData.has_token)} - chat={String(tgData.has_chat_id)} - dry_run=
            {String(tgData.dry_run)} - cooldown={String(tgData.cooldown_s ?? "---")}s
          </p>
          <Caption>No se muestran secretos. Solo banderas de configuracion.</Caption>
        </div>
      </div>

      {prec.data?.length ? (
        <div>
          <h4 className="mb-1 text-sm font-medium">Precursores recientes (Kp / Bz)</h4>
          <div className="h-32">
            <canvas id="precursores-chart" />
          </div>
        </div>
      ) : null}

      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#7c86dc" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 4 6v6c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V6z" /></svg>
          <h4 className="text-sm font-medium">Asistente - preguntale al Concilio</h4>
          <span className="mono ml-auto text-[10.5px] text-muted">lee la DB en vivo - nemotron &gt; deepseek &gt; gemma3</span>
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-4">
          <AskBox />
        </div>
      </section>
    </div>
  )
}
