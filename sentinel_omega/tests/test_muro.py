"""El Muro de los 4 dice qué DOMINIOS están alterados. Tiene que ser verdad.
(Antes «Muro de los 5»: el muro FINANCIERO/SOCIAL se retiró el 2026-11-12,
decisión D11 de Elán — 0 activaciones en 16.031 eventos. Ver
`muro_cinco_eventos.py`, sección VERSIÓN.)

Auditado el 2026-09-26:

  · **FANTASMA estaba en el muro GEOFÍSICO** y es clima espacial puro (Bz,
    viento solar, Schumann). Medido: de 114 ciclos con el muro geofísico
    activo, **46 (40 %) lo tenían activo SOLO por FANTASMA**. Dos de cada cinco
    veces que el sistema decía «dominio geofísico alterado», lo alterado era el
    Sol --- y eso vacía la premisa entera del Muro.
  · Un muro se activa con UNA detección, sin umbral de confianza, y las
    confianzas son un valor fijo por tipo (0,95 / 0,9 / 0,7): banderas, no
    medidas.
  · Dos detectores están casi siempre encendidos: SEISMIC_CLUSTER (dispara con
    ~200 eventos regionales, lo normal en el planeta) y SILENT_TRIGGER (dispara
    PORQUE hay calma). Por eso el «breach» de 3 muros ocurría el 66 % de los
    ciclos, cuando su propia documentación dice que casi nunca es coincidencia.
"""
from dataclasses import dataclass

import pytest

from sentinel_omega.core.precursor.muro_cinco_eventos import (
    MURO_VERSION,
    WALL_FINANCIERO,
    WALL_GEOFISICO,
    WALL_MEMBERS,
    WALL_SOLAR,
    MuroCincoEventos,
)
from sentinel_omega.core.precursor.precursor_types import PrecursorType


@dataclass
class _Det:
    tipo: PrecursorType
    confidence: float = 0.9


def _muros_activos(detecciones):
    r = MuroCincoEventos().evaluate(detecciones)
    return {w.name for w in r.wall_statuses if w.active}


def test_el_fantasma_es_solar_no_geofisico():
    """El índice se calcula con Bz, viento y Schumann: clima espacial."""
    assert PrecursorType.FANTASMA in WALL_MEMBERS[WALL_SOLAR]
    assert PrecursorType.FANTASMA not in WALL_MEMBERS[WALL_GEOFISICO]


def test_el_fantasma_solo_ya_no_enciende_el_geofisico():
    # El caso exacto de los 46 ciclos medidos.
    activos = _muros_activos([_Det(PrecursorType.FANTASMA)])
    assert activos == {WALL_SOLAR}


def test_el_geofisico_se_enciende_con_lo_que_es_de_la_tierra():
    assert _muros_activos([_Det(PrecursorType.SEISMIC_CLUSTER)]) == {WALL_GEOFISICO}
    assert _muros_activos([_Det(PrecursorType.VOLCANICO)]) == {WALL_GEOFISICO}


def test_una_causa_solar_no_puede_encender_dos_muros():
    """La premisa del Muro: 3 frentes activos = 3 dominios distintos. Con el
    Fantasma en el geofísico, una sola condición solar encendía dos."""
    solares = [_Det(PrecursorType.FANTASMA), _Det(PrecursorType.SCHUMANN),
               _Det(PrecursorType.SILENT_TRIGGER)]
    assert _muros_activos(solares) == {WALL_SOLAR}


def test_tres_dominios_de_verdad_si_hacen_breach():
    r = MuroCincoEventos().evaluate([
        _Det(PrecursorType.SEISMIC_CLUSTER),   # tierra
        _Det(PrecursorType.NIEBLA_TULE),       # atmósfera
        _Det(PrecursorType.TSUNAMI),           # océano
    ])
    assert r.walls_active == 3 and r.muro_breach is True


def test_sin_detecciones_no_hay_muros():
    r = MuroCincoEventos().evaluate([])
    assert r.walls_active == 0 and r.muro_breach is False
    assert r.correlation_score == 0.0


def test_basta_UNA_deteccion_para_encender_un_muro():
    """Documentado como está, no como debería: no hay umbral de confianza, así
    que una detección floja pesa igual que una fuerte."""
    floja = MuroCincoEventos().evaluate([_Det(PrecursorType.TSUNAMI, confidence=0.01)])
    assert floja.walls_active == 1


def test_cada_tipo_cuenta_en_un_solo_muro():
    """Guarda: si un tipo apareciera en dos muros, una causa contaría doble y
    el 'breach' dejaría de significar 'dominios distintos'."""
    visto = {}
    for muro, miembros in WALL_MEMBERS.items():
        for t in miembros:
            assert t not in visto, f"{t} está en {visto.get(t)} y en {muro}"
            visto[t] = muro


def test_el_breach_necesita_tres():
    m = MuroCincoEventos()
    dos = m.evaluate([_Det(PrecursorType.SEISMIC_CLUSTER), _Det(PrecursorType.TSUNAMI)])
    assert dos.walls_active == 2 and dos.muro_breach is False


def test_financiero_retirado_no_enciende_ningun_muro():
    """D11 (2026-11-12): el muro FINANCIERO/SOCIAL está retirado. La
    detección CORRELACION_FINANCIERA sigue existiendo (el scanner la emite),
    pero ya no pertenece a ningún muro: no suma a walls_active ni al breach.
    Queda registrada en active_precursor_types, no se pierde el dato."""
    assert MURO_VERSION == "2.0"
    assert len(WALL_MEMBERS) == 4
    assert WALL_FINANCIERO not in WALL_MEMBERS
    r = MuroCincoEventos().evaluate([_Det(PrecursorType.CORRELACION_FINANCIERA)])
    assert r.walls_active == 0
    assert r.total_walls == 4
    assert r.muro_breach is False
    assert "CORRELACION_FINANCIERA" in r.active_precursor_types


def test_el_breach_sigue_siendo_tres_de_cuatro():
    """D11: el umbral es 3 ABSOLUTO (3 dominios), re-expresado 3/4. No se
    baja a 2: la ganancia Molchan 1,93x se midió con umbral 3."""
    m = MuroCincoEventos()
    assert m.min_walls_for_breach == 3
    tres = m.evaluate([
        _Det(PrecursorType.SEISMIC_CLUSTER),
        _Det(PrecursorType.NIEBLA_TULE),
        _Det(PrecursorType.TSUNAMI),
    ])
    assert tres.total_walls == 4
    assert tres.walls_active == 3 and tres.muro_breach is True
    assert tres.risk_label == "ALTO"
    cuatro = m.evaluate([
        _Det(PrecursorType.SEISMIC_CLUSTER),
        _Det(PrecursorType.NIEBLA_TULE),
        _Det(PrecursorType.TSUNAMI),
        _Det(PrecursorType.TORMENTA_SOLAR),
    ])
    assert cuatro.walls_active == 4 and cuatro.risk_label == "CRÍTICO"
