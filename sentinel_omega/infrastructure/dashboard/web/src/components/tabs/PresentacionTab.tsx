/**
 * PRESENTACIÓN — primera pestaña y carta de presentación de Sentinel Omega.
 *
 * Landing honesta: vende el sistema con datos que el propio sistema mide, sin
 * claims inventados. Toda cifra tiene su contraparte en la DB o en el
 * changelog medido. Ninguna predicción puntual de sismos (hipótesis cerrada en
 * negativo); se dice explícitamente.
 *
 * Fuentes de datos (contratos verificados contra :8787):
 *   /api/overview     → fantasma, muro, Kp, Bz, viento, actividad Schumann,
 *                       conteo de nodos/sismos, distribución de riesgo, salud
 *   /api/cimatica/ahora → clave y figura cimática del ciclo actual, conteo
 *                       de patrones, estado de la biblioteca
 *   /api/aciertos     → aciertos / falsas alarmas / omisiones (fase viva)
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import {
  Panel,
  Metrica,
  Cifra,
  BarraVeredictos,
  BannerError,
  nivelDe,
  colorNivel,
  accionNivel,
} from "@/components/ui/data";
import { CimaticaFigura } from "@/components/CimaticaFigura";

const DOMINIOS = [
  {
    nombre: "Espacio",
    detalle: "Tormentas geomagnéticas (Kp≥5), grietas de escudo (Bz≤−10), viento solar extremo, lluvia de protones, fulguraciones GOES.",
    sensores: "NOAA SWPC · OMNI2 (30 años) · GOES X-ray",
    estado: "8.439 tormentas en historia · scanner vivo",
  },
  {
    nombre: "Tierra",
    detalle: "Enjambres sísmicos, sismicidad por nodo, actividad volcánica (SO₂, VEI≥3).",
    sensores: "USGS FDSN · NASA MSVOLSO2L4",
    estado: "191.592 eventos · 756+ firmas de erupciones",
  },
  {
    nombre: "Atmósfera",
    detalle: "Presión anómala, química atmosférica, niebla, gradiente barométrico con pronóstico 5d/3h observacional.",
    sensores: "OpenWeatherMap (4 estaciones + 6 volcanes + forecast)",
    estado: "Vivo cada ciclo · campos NULL honestos",
  },
  {
    nombre: "Financiero",
    detalle: "Estrés de mercado (VIX, Fear & Greed, volatilidad BTC) y atención pública como contexto, nunca como predicción.",
    sensores: "Yahoo Finance · CoinGecko · Trends→Wikipedia",
    estado: "Techo WATCH · nunca ALERT",
  },
];

const BOTS = [
  {
    nombre: "Alfa-1",
    rol: "Clima espacial",
    detalle: "Bz GSM, viento solar, Kp, protones. Memoria 1994→.",
    familia: "space_weather",
  },
  {
    nombre: "Alfa-2",
    rol: "Satélites + rayos X",
    detalle: "ESA Sentinel térmico por PRECEDENTE de zona + GOES clase M→WATCH / X→ALERT. Vivo 2026-07→.",
    familia: "space_weather",
  },
  {
    nombre: "Beta-1",
    rol: "El latido (cimática)",
    detalle: "Resonancia Schumann y espectro Kp. Figura determinista por ciclo. 1994→.",
    familia: "schumann_cymatics",
  },
  {
    nombre: "Beta-2",
    rol: "Atmósfera",
    detalle: "Desgasificación volcánica / química atmósfera, presión y niebla con NULLs honestos. 2012→.",
    familia: "schumann_cymatics",
  },
  {
    nombre: "Delta",
    rol: "Financiero",
    detalle: "Bolsa, cripto y tendencias. Contexto del Padre, techo WATCH (nunca ALERT). 2016→.",
    familia: "financial_sentiment",
  },
  {
    nombre: "Omega",
    rol: "Ritmo cósmico",
    detalle: "Fase lunar, sicigias, envolvente solar, acoplamiento Schumann↔mercado. Memoria/correlación, no agente en vivo.",
    familia: "correlación",
  },
  {
    nombre: "Loki",
    rol: "Resonancia solar",
    detalle: "Tormenta Kp≥5 hace 26–29 d (Carrington), ganancia 3,4× medida. Solo sube confianza cuando confirma.",
    familia: "resonancia",
  },
  {
    nombre: "Padre",
    rol: "Árbitro",
    detalle: "Consenso jerárquico cruzado entre familias. ≥2 familias + ≥2 alertas + corroboración schumann_cymatics > 0,3.",
    familia: "árbitro",
  },
];

const RESULTADOS = [
  { etiqueta: "Firmas consolidadas", valor: "23.274", nota: "memoria de patrones por bot (ventana 14 d previa al evento)" },
  { etiqueta: "Firmas exigibles", valor: "11.377", nota: "49 % — discriminan eventos frente a calma (lift ≥ 2,0)" },
  { etiqueta: "Familias activas", valor: "3", nota: "space_weather · schumann_cymatics · financial_sentiment" },
  { etiqueta: "ONNX aprobados", valor: "0", nota: "compuerta de habilidad negó a los 7 (AUC ~0,5 vs nulo 0,899)" },
];

const NO_HACE = [
  "NO predice sismos M4.5+ vía Schumann: hipótesis cerrada en negativo en dos estaciones independientes (Granada 2013-2017, Eskdalemuir 2025).",
  "NO tiene modelos ONNX aprobados: la compuerta de habilidad midió a los siete y ninguno aprobó.",
  "NO mide la frecuencia Schumann en vivo: retirada el 2026-10-09; solo la actividad (intensidad del espectrograma de Tomsk).",
  "NO es un sistema de lotería ni de «Elite»: Sentinel Titan vive en otra rama, fuera de main.",
];

export function PresentacionTab() {
  const ovF = useCallback(() => api.overview(), []);
  const ciF = useCallback(() => api.cimaticaAhora(), []);
  const acF = useCallback(() => api.aciertos(200), []);

  const ov = usePoll(ovF, 30000);
  const ci = usePoll(ciF, 30000);
  const ac = usePoll(acF, 60000);

  if (ov.error) return <Panel titulo="Sin telemetría" nota={ov.error}><BannerError mensaje={ov.error} /></Panel>;

  const d: any = ov.data ?? {};
  const fantasma = d.fantasma ?? {};
  const muro = d.muro ?? {};
  const ciclo = d.ciclo ?? {};
  const counts = d.counts ?? {};
  const risk = d.risk_distribution ?? {};
  const calert = d.cycle_alert_rate ?? {};

  const nivel = nivelDe(ciclo.nivel_riesgo ?? fantasma.nivel_riesgo);
  const fantasmaValor = fantasma.value != null ? Number(fantasma.value) : null;
  const kp = fantasma.kp != null ? Number(fantasma.kp) : null;
  const bz = fantasma.bz_nT != null ? Number(fantasma.bz_nT) : null;
  const viento = fantasma.viento_km_s != null ? Number(fantasma.viento_km_s) : null;
  const schAct = fantasma.schumann_activity != null ? Number(fantasma.schumann_activity) : null;

  const c: any = ci.data ?? {};
  const claveFigura = c.current_clave || null;
  const figuraJson = c.current_figura ?? null;
  const patronesN = c.patrones_n != null ? Number(c.patrones_n) : null;
  const bibliotecaPresente = c.biblioteca_presente === true;
  const bibliotecaN = c.biblioteca_n != null ? Number(c.biblioteca_n) : null;

  const a: any = ac.data ?? {};
  const summary = a.summary ?? {};
  const aciertosN = Number(summary.aciertos ?? 0);
  const fallosN = Number(summary.fallos ?? 0);
  const fpsN = Number(summary.falsos_positivos ?? 0);
  const ganancia = summary.ganancia_real != null ? Number(summary.ganancia_real) : null;
  const tasaBase = summary.tasa_base != null ? Number(summary.tasa_base) : null;

  const chipRiesgo = (
    <span className="mono texto-micro font-bold" style={{ color: colorNivel(nivel) }}>
      {accionNivel(nivel)} {nivel === "DESCONOCIDO" ? "(sin lectura)" : ""}
    </span>
  );

  return (
    <div className="space-y-0 max-w-7xl mx-auto">
      {/* ===== HERO ===== */}
      <section
        className="relative rounded-xl border border-border/70 bg-surface px-6 py-10 lg:px-10 lg:py-14 overflow-hidden"
        style={{ backgroundImage: "radial-gradient(circle at 85% -10%, color-mix(in oklch, var(--color-acento) 12%, transparent) 0%, transparent 45%)" }}
      >
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-border/50 text-xs text-muted mb-4">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--color-calma)" }} />
            Sistema en operación · lectura en vivo
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight leading-[1.05] mb-4">
            Sentinel Omega
          </h1>
          <p className="text-lg md:text-xl text-muted leading-relaxed max-w-[62ch] mb-6">
            Plataforma de detección y caracterización de anomalías naturales en
            <strong>cuatro dominios</strong>: espacio, tierra, atmósfera y
            financiero. Ocho bots especializados analizan señales en tiempo real
            y un consenso jerárquico valida cada detección antes de avisar.
          </p>
          <div className="flex flex-wrap gap-3 md:gap-4">
            <button
              onClick={() => {}}
              disabled
              className="px-5 py-2.5 rounded-lg border border-border/60 bg-surface-raised text-foreground text-sm font-semibold"
            >
              Ver dominios
            </button>
            <button
              onClick={() => {}}
              disabled
              className="px-5 py-2.5 rounded-lg border border-border/60 bg-transparent text-muted text-sm font-semibold"
            >
              Los 8 bots
            </button>
          </div>

          {/* Estado vivo del momento */}
          <div className="mt-8 grid grid-cols-2 md:grid-cols-6 gap-3 border-t border-border/40 pt-6">
            <div className="bg-surface-raised/50 rounded-lg p-3 border border-border/40">
              <div className="texto-micro texto-desvanecido uppercase tracking-wider">Fantasma</div>
              <div className="mono text-foreground font-bold text-xl">
                <Cifra valor={fantasmaValor} digits={1} />
              </div>
              <div className="texto-micro texto-desvanecido mt-0.5">{chipRiesgo}</div>
            </div>
            <div className="bg-surface-raised/50 rounded-lg p-3 border border-border/40">
              <div className="texto-micro texto-desvanecido uppercase tracking-wider">Kp</div>
              <div className="mono text-foreground font-bold text-xl">
                <Cifra valor={kp} digits={2} />
              </div>
              <div className="texto-micro texto-desvanecido mt-0.5">
                {kp != null && kp >= 5 ? "tormenta" : kp != null && kp >= 4 ? "inquietud" : "calma"}
              </div>
            </div>
            <div className="bg-surface-raised/50 rounded-lg p-3 border border-border/40">
              <div className="texto-micro texto-desvanecido uppercase tracking-wider">Bz (nT)</div>
              <div className="mono text-foreground font-bold text-xl">
                <Cifra valor={bz} digits={1} />
              </div>
            </div>
            <div className="bg-surface-raised/50 rounded-lg p-3 border border-border/40">
              <div className="texto-micro texto-desvanecido uppercase tracking-wider">Viento (km/s)</div>
              <div className="mono text-foreground font-bold text-xl">
                <Cifra valor={viento} digits={0} />
              </div>
            </div>
            <div className="bg-surface-raised/50 rounded-lg p-3 border border-border/40">
              <div className="texto-micro texto-desvanecido uppercase tracking-wider">Act. Schumann</div>
              <div className="mono text-foreground font-bold text-xl">
                <Cifra valor={schAct} digits={1} unidad="%" />
              </div>
            </div>
            <div className="bg-surface-raised/50 rounded-lg p-3 border border-border/40">
              <div className="texto-micro texto-desvanecido uppercase tracking-wider">Muro</div>
              <div className="mono text-foreground font-bold text-xl">
                {muro.walls_active != null ? Number(muro.walls_active) : "—"} / 5
              </div>
              <div className="texto-micro texto-desvanecido mt-0.5">
                {muro.muro_breach ? "breach" : "estable"}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== DOMINIOS ===== */}
      <section className="mt-10 space-y-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-2xl font-bold text-foreground">Qué detecta el sistema</h2>
          <p className="texto-meta texto-desvanecido">Cuatro dominios, sensores reales, datos medidos</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {DOMINIOS.map((dom) => (
            <Panel
              key={dom.nombre}
              titulo={dom.nombre}
              meta={dom.estado}
              nota={dom.sensores}
            >
              <p className="texto-meta texto-desvanecido">{dom.detalle}</p>
            </Panel>
          ))}
        </div>
      </section>

      {/* ===== LOS 8 BOTS ===== */}
      <section className="mt-10 space-y-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-2xl font-bold text-foreground">Los 8 bots del consenso</h2>
          <p className="texto-meta texto-desvanecido">Cada uno con su dominio, su memoria y su rol en el Padre</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {BOTS.map((bot) => (
            <Panel
              key={bot.nombre}
              titulo={bot.nombre}
              meta={bot.rol}
              nota={bot.familia}
            >
              <p className="texto-micro texto-desvanecido">{bot.detalle}</p>
            </Panel>
          ))}
        </div>
      </section>

      {/* ===== RESULTADOS MEDIDOS ===== */}
      <section className="mt-10 space-y-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-2xl font-bold text-foreground">Resultados medidos (no prometidos)</h2>
          <p className="texto-meta texto-desvanecido">Cada cifra tiene su modelo nulo al lado</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {RESULTADOS.map((r) => (
            <Panel
              key={r.etiqueta}
              titulo={r.etiqueta}
              nota={r.nota}
            >
              <div className="mono text-foreground font-bold text-2xl">
                <Cifra valor={r.valor} digits={0} />
              </div>
            </Panel>
          ))}
        </div>

        <Panel
          titulo="La vara honesta: asertividad vs ganancia"
          meta="el nulo del Juez · fase viva"
          nota={
            <>
              La asertividad cuenta como acierto cada silencio en calma —y la calma es casi todo—. La ganancia (Molchan) compara contra el bot que nunca alarma.{" "}
              <strong>1× = no aporta nada.</strong> Aquí se leen juntas, nunca solas.
            </>
          }
        >
          <div className="grid gap-4 md:grid-cols-4">
            <Metrica
              etiqueta="Asertividad viva"
              valor={`${(summary.asertividad * 100).toFixed(1)}%`}
              contexto="incluye silencios en calma"
              jerarquia="compacta"
            />
            <Metrica
              etiqueta="Ganancia sobre ciego"
              valor={ganancia != null ? `${ganancia.toFixed(2)}×` : "—"}
              contexto={tasaBase != null ? `tasa base del nodo ${(tasaBase * 100).toFixed(1)}%` : "sin medir"}
              jerarquia="compacta"
            />
            <Metrica
              etiqueta="Falsas alarmas"
              valor={fpsN.toLocaleString("es-MX")}
              contexto="avisó y no pasó nada"
              jerarquia="compacta"
            />
            <Metrica
              etiqueta="Omisiones"
              valor={fallosN.toLocaleString("es-MX")}
              contexto="pasó algo y no avisó — pesa 10×"
              jerarquia="compacta"
            />
          </div>
          <BarraVeredictos aciertos={aciertosN} falsosPositivos={fpsN} fallos={fallosN} />
        </Panel>
      </section>

      {/* ===== LO QUE NO HACE ===== */}
      <section className="mt-10 space-y-6">
        <Panel
          titulo="Lo que Sentinel Omega NO hace"
          meta="medido, no especulado"
          nota="Decir lo que no se sabe es parte del producto. Cada afirmación está verificada contra datos reales."
        >
          <ul className="space-y-3 text-muted texto-meta">
            {NO_HACE.map((item, i) => (
              <li key={i} className="flex gap-3">
                <span className="mono texto-micro font-bold" style={{ color: "var(--color-aviso)" }}>
                  ▸
                </span>
                {item}
              </li>
            ))}
          </ul>
        </Panel>
      </section>

      {/* ===== CIMÁTICA VIVA ===== */}
      <Panel
        titulo="La firma cimática del ciclo actual"
        meta="clave de telemetría → figura determinista (tipo Chladni)"
        nota={
          <>
            La misma clave siempre dibuja la misma figura — reconocible de
            reojo, como las placas de Chladni. Es la semilla de comparación
            contra la biblioteca de vísperas. Color neutro a propósito: la
            figura es dato, no estado de riesgo.
            {figuraJson ? (
              <>
                <br />
                Telemetría de la firma: {claveFigura ? String(claveFigura).slice(0, 100) : "sin clave"}.
              </>
            ) : null}
          </>
        }
      >
        <div className="grid gap-6 lg:grid-cols-2 items-center">
          <div className="flex flex-col items-center gap-4">
            <CimaticaFigura clave={claveFigura} size={260} />
            {claveFigura ? (
              <p className="mono break-all text-micro leading-relaxed text-muted text-center max-w-xs">
                {String(claveFigura).slice(0, 140)}{String(claveFigura).length > 140 ? "…" : ""}
              </p>
            ) : (
              <p className="text-meta text-muted">
                Sin clave cimática aún — esperando el primer snapshot del ciclo.
              </p>
            )}
          </div>
          <div>
            <div className="grid gap-3 md:grid-cols-2">
              <Metrica
                etiqueta="Patrones en ciclo"
                valor={patronesN != null ? patronesN.toLocaleString("es-MX") : "—"}
                contexto="tbl_cimatica_patrones · conteo de repetición"
                jerarquia="compacta"
              />
              <Metrica
                etiqueta="Biblioteca de figuras"
                valor={
                  bibliotecaN != null
                    ? bibliotecaN.toLocaleString("es-MX")
                    : bibliotecaPresente
                      ? "0"
                      : "no construida"
                }
                contexto={
                  bibliotecaPresente
                    ? "vísperas etiquetadas comparables"
                    : "sin tabla propia — la comparación viva usa los patrones"
                }
                jerarquia="compacta"
              />
              <Metrica
                etiqueta="Frescura"
                valor={c.edad_s != null ? `${Math.round(Number(c.edad_s))} s` : "—"}
                contexto="edad del snapshot de cimática"
                jerarquia="compacta"
              />
              <Metrica
                etiqueta="Nodos vigilados"
                valor={counts.nodos != null ? String(counts.nodos) : "—"}
                contexto="malla UVG-125"
                jerarquia="compacta"
              />
            </div>
            <p className="mt-4 texto-meta texto-desvanecido">
              La figura se calcula en cada ciclo del launcher a partir de la
              telemetría viva y viaja con cada predicción del Padre. El Juez la
              registra junto al veredicto: predicción → realidad → figura.
            </p>
          </div>
        </div>
      </Panel>

      {/* ===== SISMOS ===== */}
      <Panel
        titulo="Sismicidad reciente"
        meta="M≥4.5 · catálogo USGS"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <Metrica
            etiqueta="Sismos M4.5+"
            valor={counts.sismos_m45 != null ? Number(counts.sismos_m45).toLocaleString("es-MX") : "—"}
            contexto="ventana del catálogo"
            jerarquia="compacta"
          />
          <Metrica
            etiqueta="Ciclos con ALERT"
            valor={
              calert.total_cycles
                ? `${calert.alert_cycles} de ${Number(calert.total_cycles).toLocaleString("es-MX")}`
                : "—"
            }
            contexto="tasa de alerta en vivo"
            jerarquia="compacta"
          />
        </div>
        <div className="mt-3 grid gap-4 md:grid-cols-4">
          {Object.entries(risk).map(([nivelKey, n]) => {
            const nvl = nivelDe(nivelKey);
            return (
              <Metrica
                key={nivelKey}
                etiqueta={nivelKey}
                valor={<Cifra valor={Number(n ?? 0)} digits={0} />}
                nivel={nvl}
                jerarquia="compacta"
              />
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
