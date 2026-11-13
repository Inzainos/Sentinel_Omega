# Dashboard Sentinel Omega — Cambios implementados (2026-11-03)

## Resumen
Se implementaron 5 fases de optimización e innovación sobre el dashboard moderno (React 19 + Vite 6 + Tailwind 4 → FastAPI, puerto 5173 dev / 8787 API) sin tocar los datos ni los archivos de conocimiento.

---

## Fase 1 — Bug fix y nuevo endpoint de espacio de firmas

### 1.1 Corrección de Bz en PrincipalTab
- **Archivo:** `sentinel_omega/infrastructure/dashboard/web/src/components/tabs/PrincipalTab.tsx`
- **Cambio:** `fantasma.bz_promedio` → `fantasma.bz_nT`
- **Motivo:** La API (`api.py:395`) sirve `bz_nT`, no `bz_promedio`. El tablero mostraba "—" para Bz en todos los ciclos.

### 1.2 Endpoint `/api/firmas-espacio`
- **Archivo:** `sentinel_omega/infrastructure/dashboard/api.py`
- **Qué hace:** Sirve todas las firmas de `TBL_FIRMAS` con `features_json` parseado a vector numérico, metadatos (bot, clase, recurrencia, estado, discriminación, exigible, lift), lista de `feature_keys`, y filtros opcionales por `bot` y `estado`.
- **Regla de diseño:** una firma en disco no es conocimiento demostrado — `exigible` y `discriminacion` son los campos que deciden.

### 1.3 Pestaña "Espacio de Firmas"
- **Archivo nuevo:** `sentinel_omega/infrastructure/dashboard/web/src/components/tabs/EspacioFirmasTab.tsx`
- **Qué hace:** Proyección PCA 2D implementada en TypeScript puro (centrado, matriz de covarianza, power iteration, deflación) sin dependencias nuevas.
- **Visualización:** SVG scatter plot con color por `event_class`, tamaño por `recurrencia`, borde blanco si `exigible=1`, círculo de referencia "0,80 ref.", tooltips con todos los datos de cada firma, tabla de las 25 firmas exigible más discriminantes.
- **Registro:** `App.tsx` (ruta `/espacio-firmas`) y `BarraLateral.tsx`.

### 1.4 Cliente API
- **Archivo:** `sentinel_omega/infrastructure/dashboard/web/src/lib/api.ts`
- **Cambio:** añadido `firmasEspacio()`.

---

## Fase 2 — Service layer y estado unificado

### Endpoint `/api/estado-sistema-unificado`
- **Archivo:** `sentinel_omega/infrastructure/dashboard/api.py`
- **Qué hace:** Agrega en una sola respuesta: salud general (`tbl_salud_sistema`), salud de APIs (LIVE/STALE/CONGELADO/DESCONOCIDO), overview (fantasma, muro, ciclo) y estado vivo (`/api/estado-vivo`).
- **Estado global:** `ok` / `stale` / `congelado` / `desconocido` / `degradado`.
- **Métricas de fuentes:** conteo por estado y lista de fuentes desconocidas por nombre.

### Cliente API
- **Archivo:** `sentinel_omega/infrastructure/dashboard/web/src/lib/api.ts`
- **Cambio:** añadido `estadoSistemaUnificado()`.

---

## Fase 3 — (Completada en Fase 1)
Pestaña Espacio de Firmas con PCA 2D.

---

## Fase 4 — Reorganización Leading vs Lagging

### Barra lateral dividida en grupos
- **Archivo:** `sentinel_omega/infrastructure/dashboard/web/src/components/BarraLateral.tsx`
- **Grupos:**
  - *Presentación* (hero, Decide/Learn): Presentación
  - *Leading* (ventana de atención): Principal, Predicciones, Señales, Espacio de Firmas, Cimática, Mapas, Síntesis
  - *Lagging* (veredicto histórico): Padre + Juez, Modelos, Reportes, Loki
- Cada grupo tiene etiqueta y chip de categoría ("atención" vs "veredicto").

---

## Fase 5 — BI y exportación de reportes

### Endpoint `/api/reportes/export`
- **Archivo:** `sentinel_omega/infrastructure/dashboard/api.py`
- **Qué hace:** Exporta veredictos del Juez (fase viva, `en_vivo=1`, max 5000 filas) en JSON o CSV. Filtro opcional por nombre de bot.

### ReportesTab reescrito
- **Archivo:** `sentinel_omega/infrastructure/dashboard/web/src/components/tabs/ReportesTab.tsx`
- **Paneles:**
  1. Estado del sistema unificado (6 métricas: estado global, fuentes OK/STALE/CONGELADO/DESCONOCIDO, fantasma)
  2. Barra de veredictos del Juez
  3. Últimos 12 veredictos en tabla
  4. Exportación: selector JSON/CSV, botón de descarga automática, resultado
  5. Lista de reportes publicados (archivos, tamaño, fecha)

### Cliente API
- **Archivo:** `sentinel_omega/infrastructure/dashboard/web/src/lib/api.ts`
- **Cambio:** añadido `reportesExport()`.

---

## Verificación técnica

| Comando | Resultado |
|---------|-----------|
| `tsc --noEmit` | 0 errores |
| `npm run build` | Éxito (~287 KB JS, ~17.4 KB CSS) |
| Python API sintaxis | Válida |

---

## Servicios systemd del dashboard

| Servicio | Archivo | Puerto | Comando de reinicio |
|----------|---------|--------|---------------------|
| Dashboard API | `sentinel-omega-dashboard-api.service` | 8787 | `systemctl --user restart sentinel-omega-dashboard-api.service` |
| Dashboard Web | `sentinel-omega-dashboard-web.service` | 5173 | `systemctl --user restart sentinel-omega-dashboard-web.service` |

**Nota:** El servicio API apunta a `/home/deamon/workspaces/.venv/bin/python` (ver `deploy/sentinel-omega-dashboard-api.service`). El servicio web usa `npm run dev`.

---

## Fase 0 — Sistema de diseño v4 "Cyber-Geológico" (2026-11-03)

### 0.1 Tokens CSS reescritos
- **Archivo:** `sentinel_omega/infrastructure/dashboard/web/src/index.css`
- **Qué cambia:** Tokens en oklch para consistencia perceptiva, jerarquía tipográfica completa (display, hero-num, metric, read, body, meta, micro), superficies cyber-geológicas (negro carbón, vidrio esmerilado, bordes neón tenue), animaciones (pulse-suave, slide-in, fade-in, count-up, breathe), glassmorphism, gradientes, scrollbar personalizada, focus-visible.

### 0.2 Jerarquía tipográfica
| Nivel | Uso | Tamaño | Peso |
|-------|-----|--------|------|
| `--text-display` | Héroe, títulos de sección | 2.5rem | 700 |
| `--text-hero-num` | Métrica principal | 1.875rem | 700 |
| `--text-metric` | Métrica normal | 1.125rem | 600 |
| `--text-read` | Métrica compacta | 0.875rem | 600 |
| `--text-body` | Texto de lectura | 1rem | 400-500 |
| `--text-meta` | Etiquetas, notas | 0.875rem | 500 |
| `--text-micro` | Chips, pequeños | 0.7rem | 500 |

### 0.3 Colores (oklch)
**Riesgo (saturado):** calma, atención, aviso, crítico (+ variantes -dim para fondos)
**Serie (datos, desaturado):** serie-1 a serie-4 (azul, teal, púrpura, ocre)
**Superficies:** surface, surface-raised, surface-sunken, surface-glass, border, border-strong, border-glow
**Texto:** foreground, muted, faint, inverse
**Acento UI:** acento, acento-dim (índigo eléctrico, no se usa para datos)

### 0.4 Animaciones
- `pulse-suave` — para estados activos
- `slide-in` — entrada de componentes
- `fade-in` — aparición suave
- `count-up` — animación de números
- `breathe` — indicador de atención

### 0.5 Utilidades nuevas
- `.glass` / `.glass-strong` — vidrio esmerilado con backdrop-filter
- `.grad-acento` / `.grad-surface` — gradientes
- `.boton`, `.boton-primario`, `.boton-fantasma` — botones con estados hover
- `.panel` — contenedor con borde neón opcional (`.panel-activo`)
- `.metrica`, `.etiqueta-metrica`, `.valor-metrica`, `.contexto-metrica` — jerarquías de métrica
- `.cifra`, `.cifra-ausente` — números con ausencia explícita
- `.escala-riesgo` — barra de riesgo con marcas de umbral
- `.chip-fuente` — estado de fuente de datos
- `.barra-veredictos` — barra de veredictos del Juez
- `.segmentos-muro` / `.muro-segmento` — 5 paredes del muro
- `.sin-datos`, `.banner-error` — estados vacíos y errores
- `.tabla-datos` — tabla genérica con columnas configurables

---

## Estado de los servicios (2026-11-03)

| Servicio | Estado | Puerto | Verificación |
|----------|--------|--------|--------------|
| `sentinel-omega-dashboard-api.service` | active | 8787 | `/api/health` → 200 |
| `sentinel-omega-dashboard-web.service` | active | 5173 | `/` → 200 |

### Endpoints verificados (todos 200 OK)
`/api/health`, `/api/overview`, `/api/estado-vivo`, `/api/firmas-espacio`, `/api/estado-sistema-unificado`, `/api/reportes`, `/api/bots`, `/api/modelos`, `/api/cimatica/ahora`, `/api/muro`, `/api/nodos`, `/api/sismos`, `/api/ciclos`, `/api/detecciones`, `/api/alertas`, `/api/aciertos`, `/api/juez`, `/api/layers`, `/api/lag`, `/api/muro_lags`, `/api/correlaciones`, `/api/consenso`, `/api/heatmaps`, `/api/telegram/status`

---

## Build de producción

| Comando | Resultado |
|---------|-----------|
| `tsc --noEmit` | 0 errores |
| `npm run build` | Éxito — CSS 19.82 KB (gzip 5.25 KB), JS 286.77 KB (gzip 90.21 KB) |

---

## Próximos pasos (pendientes)

1. **Refactor `data.tsx`** — actualizar Panel, Metrica, Cifra, TablaDatos con las nuevas jerarquías del sistema de diseño v4.
2. **Componentes nuevos:** Batería de la Tierra, Medidor de Asertividad, Mapa de Calor de Correlaciones, Hipercubo 4D, SkeletonPanel, FiltroGlobal.
3. **Refactor BarraLateral** — grupos visuales, indicador de ubicación, filtros rápidos.
4. **Refactor pestañas Leading:** Principal, Predicciones, Señales, Espacio de Firmas, Cimática, Mapas, Síntesis.
5. **Refactor pestañas Lagging:** Padre + Juez, Modelos, Reportes, Loki.
6. **Refactor PresentacionTab** — hero honesto, dominios, 8 bots, resultados medidos, lo que no hace.
7. **Service layer + Unit of Work en el backend API** (patrón Cosmic Python).
8. **Sincronizar ANEX. I de SUDO_UNIVERSE.md** si la biblioteca cambia.
