# 🗓️ Reporte mensual — Sentinel Omega
*Generado 2026-11-01 00:00 hora MX — ventana 31 días*

> **Lectura rápida:** el sistema estuvo **inquieto** · Fantasma medio **10.8** (MODERATE · atención) · Muro con **1986 breach(es)** · asertividad viva **66%** con ganancia **0.78×** (no supera al azar).

## Resumen
- Ciclos corridos: **6671**
- Fantasma medio del periodo: **10.8**
- Fantasma máximo: **34.7**
- Breaches del Muro: **1986**
- Asertividad viva del periodo: **66%** (n=2480 resueltas)

## 🌤️ GOES X-ray — Sin fulguración significativa

> Flux máx 24 h: **4.8e-07 W/m²** a las 2026-11-01 05:00 (< clase C).

## 🛰️ Alfa-2 · Anomalías térmicas por precedente de zona

| Zona | Anomalías | Cobertura | Pases limpios / totales |
|---|---:|---:|---:|
| nodo024 | **2** | 0.67 | 0 / 24 |
| nodo025 | **2** | 0.90 | 35 / 67 |
| nodo003 | **2** | 0.68 | 0 / 31 |
| nodo027 | **1** | 0.89 | 33 / 87 |
| nodo028 | **1** | 0.67 | 0 / 20 |
| nodo005 | **1** | 0.84 | 12 / 33 |
| nodo033 | **4** | 0.94 | 42 / 76 |
| nodo034 | **4** | 0.91 | 37 / 95 |
| nodo007 | **4** | 0.68 | 0 / 38 |
| nodo040 | **4** | 0.84 | 16 / 43 |
| nodo041 | **4** | 0.89 | 15 / 38 |
| nodo011 | **4** | 0.68 | 0 / 36 |
| nodo042 | **7** | 0.81 | 18 / 70 |
| nodo043 | **7** | 0.85 | 26 / 68 |
| nodo012 | **7** | 0.68 | 0 / 29 |

## Cimática
- Patrones `general`: 104574 (frecuencia máx 76)
- Patrones `nodo`: 110017 (frecuencia máx 104)

| Patrón | Ámbito | Evento asociado | Frecuencia |
|---|---|---|---:|
| 5169443 | nodo 67 | SISMO_M5 | 104 |
| 5169550 | general | SISMO_M4 | 76 |
| 5169553 | nodo 26 | SISMO_M5 | 76 |
| 5169521 | nodo 67 | SISMO_M5 | 74 |
| 5169323 | nodo 67 | SISMO_M5 | 62 |
| 5169551 | nodo 67 | SISMO_M4 | 56 |
| 5169552 | nodo 60 | SISMO_M5 | 56 |
| 5169538 | general | SISMO_M5 | 55 |
| 5169539 | nodo 26 | SISMO_M5 | 55 |
| 5169540 | nodo 67 | SISMO_M4 | 55 |

## ✅ Aciertos — Últimos 31 días

| Métrica | Valor |
|---------|-------|
| **Aciertos** | 1495 |
| **Fallos** | 165 |
| **Falsos positivos** | 652 |
| **Tasa de acierto** | 64.2% `▓▓▓▓▓▓▓▓░░░░` |
| **Total predicciones** | 2328 |

![Distribución de veredictos](graficas/aciertos_31d_pastel.png)

### 🤖 Desempeño por Bot

| Bot | Aciertos | Tasa | Confianza | Anticipación |
|-----|----------|------|-----------|---------------|
| beta1 | 239/289 | 83% `▓▓▓▓▓▓▓░` | 0.33 | 0.1d |
| delta | 237/289 | 82% `▓▓▓▓▓▓▓░` | 0.34 | 0.1d |
| beta2 | 235/289 | 81% `▓▓▓▓▓▓▓░` | 0.24 | 0.1d |
| omega | 228/289 | 79% `▓▓▓▓▓▓░░` | 0.43 | 0.1d |
| loki | 224/289 | 78% `▓▓▓▓▓▓░░` | 0.27 | 0.1d |
| padre | 191/289 | 66% `▓▓▓▓▓░░░` | 0.24 | 0.1d |
| alfa1 | 74/289 | 26% `▓▓░░░░░░` | 0.63 | 0.1d |
| alfa2 | 67/289 | 23% `▓▓░░░░░░` | 0.70 | 0.1d |

![Desempeño por bot](graficas/aciertos_31d_barras.png)

![Fantasma medio diario](graficas/mensual_fantasma.png)
![Alertas por día](graficas/mensual_alertas.png)
![Breaches del Muro por día](graficas/mensual_breaches.png)

## ℹ️ Cómo leer este reporte

- **Fantasma** — índice de *riesgo cósmico* (TITAN V32). **No es un sismo**: mide la
  tensión del sistema combinando campo magnético (Bz), viento solar, resonancia
  Schumann, presión y más. Escala: **LOW <5** (calma) · **MODERATE 5–15** (atención)
  · **HIGH 15–30** (avisar) · **CRITICAL ≥30** (protocolo).
- **Muro de los 5 Eventos** — cinco "paredes" de correlación (geofísica, atmosférica,
  oceánica, solar/geomagnética y financiera). Hay *breach* cuando **3 o más** se
  activan a la vez.
- **Asertividad viva** — de las predicciones ya verificadas contra la realidad (USGS),
  qué porcentaje resultó **ACIERTO**. El conteo impreso conserva la `ventana_h`
  almacenada en cada fila; no es todavía un filtro de **M>=6.0
  dentro de 24 h** ni una relabelización del histórico.
  Ese es el blanco objetivo para reportes nuevos. El umbral del muro no cambia.
  El Juez audita aparte (nunca predice).
- **Cimática** — patrones de telemetría que el sistema ve repetirse; si un patrón
  antecede a un evento real se etiqueta con su clase (SISMO_M4…M7, ERUPCION_VEI…).
  La frecuencia es cuántas veces se ha visto ese patrón.
- **Anticipación** — días de adelanto promedio entre la señal y el evento.
