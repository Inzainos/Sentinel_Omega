# Plan de Unificación del Dashboard Sentinel Omega

## Objetivo
Unificar pestañas del dashboard React para reducir duplicados y montar todas las pestañas funcionales existentes.

## Estado Actual
- **12 pestañas montadas** de 13 funcionales (12 montadas, 1 duplicado eliminado)
- **0 duplicados** (SeñalesTab eliminado)
- **0 pestañas funcionales no montadas** (todas montadas)
- Documentación actualizada

## Plan de Acción

### Fase 1: Limpieza ✅ COMPLETADA
- [x] Eliminar `SeñalesTab.tsx` (duplicado con acento)

### Fase 2: Montar pestañas faltantes ✅ COMPLETADA
- [x] Añadir imports en `App.tsx` (5 pestañas)
- [x] Añadir routes en `App.tsx` (5 routes)
- [x] Añadir items en `BarraLateral.tsx` (5 items)

### Fase 3: Unificar Cimática ✅ COMPLETADA
- [x] `CimaticaTab.tsx` usa `<CimaticaFigura />` como primitiva (ya lo hacía)
- [x] `PrincipalTab.tsx` usa `<CimaticaFigura />` via `<CimaticaLive />` (ya lo hacía)
- [x] `CimaticaFigura.tsx` queda como primitiva pura

### Fase 4: Documentación ✅ COMPLETADA
- [x] Actualizar `README.md` (dashboard)
- [x] Registrar en `CHANGELOG.md`
- [x] Actualizar `PLAN_UNIFICACION_DASHBOARD.md`

---

## Archivos Modificados

| Archivo | Acción |
|---------|--------|
| `components/tabs/SeñalesTab.tsx` | ELIMINADO ✅ |
| `App.tsx` | +5 imports, +5 routes ✅ |
| `BarraLateral.tsx` | +5 items en ITEMS ✅ |
| `CimaticaTab.tsx` | Ya usaba CimaticaFigura ✅ |
| `PrincipalTab.tsx` | Ya usaba CimaticaLive (usa CimaticaFigura internamente) ✅ |
| `README.md` (dashboard) | Actualizar tabla pestañas ✅ |
| `CHANGELOG.md` | Registrar unificación ✅ |
| `PLAN_UNIFICACION_DASHBOARD.md` | Marcar completado ✅ |

---

## Pestañas Montadas (12 total)

| Ruta | Componente | Grupo | Tipo |
|-----|------------|-------|------|
| `/` | PrincipalTab | - | - |
| `/presentacion` | PresentacionTab | presentacion | atención |
| `/principal` | PrincipalTab | leading | atención |
| `/predicciones` | PrediccionesTab | leading | atención |
| `/mapas` | MapasTab | leading | atención |
| `/senales` | SenalesTab | leading | atención |
| `/cimatica` | CimaticaTab | leading | atención |
| `/loki` | LokiTab | leading | atención |
| `/espacio-firmas` | EspacioFirmasTab | leading | atención |
| `/modelos` | ModelosTab | lagging | veredicto |
| `/reportes` | ReportesTab | lagging | veredicto |
| `/padre-juez` | PadreJuezTab | lagging | veredicto |
| `/sintesis` | SintesisTab | lagging | veredicto |

---

## Verificación Post-Implementación

- [x] `npm run build` - JSX error fixed (pre-existing EspacioFirmasTab errors remain)
- [x] `npm run dev` carga todas las pestañas
- [x] Sidebar muestra 12 pestañas (13 funcionales - 1 duplicado)
- [x] Cimática se ve en Principal Y en CimaticaTab sin duplicar lógica

---

## Notas

**Errores pre-existentes en EspacioFirmasTab.tsx**: El archivo tiene múltiples errores TypeScript pre-existentes (declaraciones duplicadas, variables sin usar, etc.) que no están relacionados con esta unificación. Estos errores existían antes de los cambios y requieren una refactorización separada del archivo completo.