import { useCallback } from "react"
import { api } from "@/lib/api"
import { usePoll } from "@/hooks/usePoll"
import { TabIntro, Caption } from "@/components/TabIntro"
import { DataTable } from "@/components/DataTable"
import { EmptyState } from "@/components/EmptyState"
import { fmtNum, fmtTs } from "@/lib/utils"
import { SimpleBars } from "@/components/charts/Sparkline"

export function SenalesTab() {
  const telemF = useCallback(() => api.telemetry(), [])
  const histF = useCallback(() => api.telemetryHistory(48), [])
  const climaF = useCallback(() => api.climaEspacial(80), [])
  const schF = useCallback(() => api.schumannVivo(120), [])
  const deltaF = useCallback(() => api.delta(80), [])

  const telem = usePoll(telemF, 30000)
  const hist = usePoll(histF, 60000)
  const clima = usePoll(climaF, 60000)
  const sch = usePoll(schF, 60000)
  const delta = usePoll(deltaF, 60000)

  const latest = telem.data
  const kp = latest?.kp
  const bz = latest?.bz_gsm
  const vsw = latest?.vsw
  const proton = latest?.proton_flux

  const schItems = (sch.data?.items || []).slice(-20)
  const schSpark = schItems.map((s: any, i: number) => ({
    i,
    y: Number(s.intensity_wpc ?? s.value ?? 0),
  }))

  const climaItems = (clima.data?.items || []).slice(0, 10)

  const deltaItems = (delta.data?.items || []).slice(-40)
  const deltaSpark = deltaItems.map((d: any, i: number) => ({
    i,
    y: Number(d.value ?? 0),
  }))

  if (telem.error) return <div className="p-4 text-red-500">Error: {telem.error}</div>
  if (telem.loading && !telem.data) return <div className="p-4 text-muted">Cargando Señales…</div>

  return (
    <div className="space-y-6">
      <TabIntro title="Señales — telemetría viva de los 4 dominios">
        <p>
          Lectura cruda de los sensores: clima espacial (Kp, Bz, viento solar, protones), Schumann (actividad WPC
          Tomsk), presión ionosférica (Delta) y clima atmosférico. Sin predicción — solo el estado actual medido.
        </p>
      </TabIntro>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-bg-card p-4 space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted">Kp (NOAA)</div>
          <div className="text-3xl font-bold text-foreground mono">{kp ?? "—"}</div>
          <div className="text-xs text-muted">
            {kp != null && kp >= 5 ? "Tormenta geomagnética" : kp != null ? "Calma / inestable" : "Sin dato"}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-4 space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted">Bz GSM (nT)</div>
          <div className="text-3xl font-bold text-foreground mono">{bz ?? "—"}</div>
          <div className="text-xs text-muted">
            {bz != null && bz < -10 ? "Sur fuerte — reconexión" : bz != null && bz < 0 ? "Sur — acoplamiento" : "Norte / sin dato"}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-4 space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted">Viento solar (km/s)</div>
          <div className="text-3xl font-bold text-foreground mono">{vsw ? fmtNum(vsw) : "—"}</div>
          <div className="text-xs text-muted">
            {vsw != null && vsw > 500 ? "Alto" : vsw != null ? "Normal" : "Sin dato"}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-4 space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted">Protones (pfu)</div>
          <div className="text-3xl font-bold text-foreground mono">{proton ? fmtNum(proton) : "—"}</div>
          <div className="text-xs text-muted">
            {proton != null && proton >= 10 ? "Evento de radiación solar" : "Sin evento"}
          </div>
        </div>
      </div>

      <section className="space-y-4">
        <h4 className="text-sm font-medium">Schumann — actividad WPC Tomsk (últimos 20 ciclos)</h4>
        <Caption>Intensidad de la resonancia (no frecuencia Hz). Fuente: WPC Tomsk — el sistema mide actividad, no Hz.</Caption>
        {schSpark.length ? (
          <div className="rounded-xl border border-border bg-bg-card p-4">
            <SimpleBars
              data={schSpark}
              xKey="i"
              yKey="y"
              color="#00d4ff"
              height={140}
            />
          </div>
        ) : (
          <EmptyState title="Sin datos Schumann" detail="Verificar endpoint /api/schumann_vivo" />
        )}
      </section>

      <section className="space-y-4">
        <h4 className="text-sm font-medium">Clima espacial — últimos eventos (NOAA / GOES)</h4>
        <DataTable
          rows={climaItems}
          empty="Sin eventos de clima espacial recientes."
          columns={[
            { key: "timestamp", label: "Tiempo", render: (r: any) => fmtTs(r.timestamp) },
            { key: "tipo", label: "Tipo" },
            { key: "intensidad", label: "Intensidad", render: (r: any) => String(r.intensidad ?? r.magnitud ?? "—") },
            { key: "region", label: "Región", render: (r: any) => String(r.region ?? "—") },
          ]}
        />
      </section>

      <section className="space-y-4">
        <h4 className="text-sm font-medium">Delta — presión ionosférica (últimos 40 ciclos)</h4>
        <Caption>Variable derivada de TEC / ionosfera. Picos preceden a inestabilidad atmosférica.</Caption>
        {deltaSpark.length ? (
          <div className="rounded-xl border border-border bg-bg-card p-4">
            <SimpleBars
              data={deltaSpark}
              xKey="i"
              yKey="y"
              color="#ff9100"
              height={140}
            />
          </div>
        ) : (
          <EmptyState title="Sin datos Delta" detail="Verificar endpoint /api/delta" />
        )}
      </section>

      <section className="space-y-4">
        <h4 className="text-sm font-medium">Historial telemetría (últimas 48h)</h4>
        <Caption>Serie cruda: Kp, Bz, viento solar, protones. Para análisis manual de precursores.</Caption>
        <DataTable
          rows={(hist.data?.items || []).slice(0, 20)}
          empty="Sin historial de telemetría."
          columns={[
            { key: "timestamp", label: "Tiempo", render: (r: any) => fmtTs(r.timestamp) },
            { key: "kp", label: "Kp", render: (r: any) => (r.kp != null ? fmtNum(r.kp) : "—") },
            { key: "bz_gsm", label: "Bz (nT)", render: (r: any) => (r.bz_gsm != null ? fmtNum(r.bz_gsm) : "—") },
            { key: "vsw", label: "Vsw (km/s)", render: (r: any) => (r.vsw != null ? fmtNum(r.vsw) : "—") },
            { key: "proton_flux", label: "Protones", render: (r: any) => (r.proton_flux != null ? fmtNum(r.proton_flux) : "—") },
          ]}
        />
      </section>
    </div>
  )
}