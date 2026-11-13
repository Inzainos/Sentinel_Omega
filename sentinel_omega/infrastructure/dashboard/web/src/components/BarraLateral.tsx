/**
 * BarraLateral — navegación dividida en dos superficies (regla de KPIs):
 *
 * **Leading** (ventana de atención): fantasma, muro, firmas, predicciones,
 * señales, cimática. Datos que anticipan qué puede venir.
 *
 * **Lagging** (veredicto histórico): Modelos, Reportes.
 * Datos de lo que ya pasó: asertividad, ganancia, falsos positivos, omisiones.
 *
 * Presentación queda fuera: es la única superficie Decide/Learn (hero).
 *
 * Sólo Sentinel Omega: Padrón/Concilio/Watchdog quitados (viven en sus
 * propios proyectos).
 */
import React from "react"
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"

type Grupo = "presentacion" | "leading" | "lagging"

interface NavItem {
  to: string
  label: string
  grupo: Grupo
  /** Etiqueta corta del tipo para el chip de categoría. */
  tipo: "atencion" | "veredicto"
}

const ITEMS: NavItem[] = [
  // ── Presentación (hero, Decide/Learn) ────────────────────────────────
  { to: "/presentacion", label: "Presentación", grupo: "presentacion", tipo: "atencion" },

  // ── Leading: ventana de atención ─────────────────────────────────────
  { to: "/principal", label: "Principal", grupo: "leading", tipo: "atencion" },
  { to: "/predicciones", label: "Predicciones", grupo: "leading", tipo: "atencion" },
  { to: "/senales", label: "Señales", grupo: "leading", tipo: "atencion" },
  { to: "/mapas", label: "Mapas", grupo: "leading", tipo: "atencion" },
  { to: "/cimatica", label: "Cimática", grupo: "leading", tipo: "atencion" },
  { to: "/loki", label: "Loki", grupo: "leading", tipo: "atencion" },
  { to: "/espacio-firmas", label: "Espacio Firmas", grupo: "leading", tipo: "atencion" },

  // ── Lagging: veredicto histórico ─────────────────────────────────────
  { to: "/modelos", label: "Modelos", grupo: "lagging", tipo: "veredicto" },
  { to: "/reportes", label: "Reportes", grupo: "lagging", tipo: "veredicto" },
  { to: "/padre-juez", label: "Padre+Juez", grupo: "lagging", tipo: "veredicto" },
  { to: "/sintesis", label: "Síntesis", grupo: "lagging", tipo: "veredicto" },
]

const GRUPO_LABELS: Record<Grupo, string> = {
  presentacion: "Sistema",
  leading: "Ventana de atención (leading)",
  lagging: "Veredicto histórico (lagging)",
}

const TIPO_CHIP: Record<string, string> = {
  atencion: "atención",
  veredicto: "veredicto",
}

export function BarraLateral() {
  return (
    <aside className="w-56 shrink-0 border-r border-border/60 bg-bg-panel flex flex-col">
      <div className="px-4 py-5 border-b border-border/60">
        <div className="flex items-center gap-2">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 2 4 6v6c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V6z" stroke="var(--color-accent-cyan)" strokeWidth="1.6" strokeLinejoin="round" />
            <path d="M12 8v5M12 16v.6" stroke="var(--color-accent-cyan)" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
          <div>
            <div className="font-bold text-sm text-foreground">Sentinel Omega</div>
            <div className="text-[0.65rem] text-faint">precursores · lectura</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {ITEMS.map((item) => {
          const esPrimeroDelGrupo =
            ITEMS.findIndex((i) => i.grupo === item.grupo) ===
            ITEMS.indexOf(item)

          return (
            <React.Fragment key={item.to}>
              {esPrimeroDelGrupo && item.grupo !== "presentacion" && (
                <div className="px-3 py-1.5">
                  <span
                    className="block text-[0.6rem] uppercase tracking-wider text-faint mb-1"
                  >
                    {GRUPO_LABELS[item.grupo]}
                  </span>
                  <span
                    className="inline-flex items-center gap-1 rounded border border-border/50 bg-bg-card/50 px-2 py-0.5 text-[0.6rem] font-medium text-muted"
                  >
                    {TIPO_CHIP[item.tipo]}
                  </span>
                </div>
              )}
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "block px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-bg-card text-foreground border border-border-glow"
                      : "text-muted hover:text-foreground hover:bg-bg-card/50"
                  )
                }
              >
                {item.label}
              </NavLink>
            </React.Fragment>
          )
        })}
      </nav>
    </aside>
  )
}