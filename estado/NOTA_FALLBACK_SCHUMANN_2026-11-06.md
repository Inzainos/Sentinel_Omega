# Nota de Implementación — Fallback Schumann 2026-11-06

## Contexto
Tomsk sos70.ru caído desde 2026-11-01. Corte diario marca `tomsk_fallido` y el sistema opera con LOCF. Molchan gain 0.81x < 1.0.

## Cambios realizados
1. **schumann_fallback.py**
   - Creado `sentinel_omega/infrastructure/api/schumann_fallback.py` con adaptadores para HeartMath GCI y schumannresonance.today como referencia.
   - `fetch_heartmath_gci()` en modo prueba devuelve `(None, 2.68, 'heartmath_fallback_prueba')`.

2. **corte_diario**
   - `sentinel_omega/core/schumann_vivo.py` modificado: al fallar Tomsk, se intenta fallback antes de marcar día fallido.
   - Si fallback devuelve valor, se guarda en `tbl_schumann_diario` con fuente de fallback y se registra en serie viva.
   - Imágenes se eliminan tras extracción con `cleanup=True`.

3. **Backfill**
   - `scripts/backfill_schumann_missing.py` acumula días faltantes en `estado/missing_schumann_days.txt`.
   - 1 descarga/día máximo, sin reintentos 288 veces.

## Estado actual
- Fallback activo en modo prueba.
- Días faltantes acumulados en estado/missing_schumann_days.txt.
- Servicios operativos con paths correctos.

## Próximos pasos
- Reemplazar valor de prueba por integración real HeartMath GCI.
- Política de reducción de peso de beta1 cuando fuente = fallback.
- Monitor de salud de fuentes con alerta >24h sin en_vivo.

Firmado: 2026-11-06
