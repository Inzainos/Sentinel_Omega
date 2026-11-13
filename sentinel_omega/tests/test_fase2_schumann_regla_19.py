"""FASE 2 — ítem 19: la regla Schumann está DESHABILITADA por defecto y sus
umbrales están calibrados a la escala real 0–100.

Mediciones (DB viva modo ro, 2026-11-12): escala limpia post-2026-10-09 y
<10: n=928, p50=1.88, p90=3.17, p99=4.45; 0 filas >=5.0 y 0 >=8.0. Máx WPC
histórico observado 8.3 %. Umbrales adoptados: BONUS 5.0 (por encima del
p99 limpio, por debajo del máx WPC) y EXTREMA 8.0 (actividad sola solo
dispara at/por encima del máx WPC histórico). Los viejos 150/200 eran
~18x/~24x el máx real y nunca discriminaban nada (regla 8 del repo).
"""
import pytest

import sentinel_omega.core.precursor.scanner as mod_scanner
from sentinel_omega.core.precursor.scanner import (
    SCHUMANN_ACTIVITY_BONUS,
    SCHUMANN_ACTIVITY_EXTREMA,
    SCHUMANN_RULE_ENABLED,
    PrecursorScanner,
    PrecursorType,
)


def _scanner():
    return PrecursorScanner()


class TestReglaDeshabilitadaPorDefecto:
    def test_flag_apagado_y_contador_existe(self):
        assert SCHUMANN_RULE_ENABLED is False
        assert mod_scanner._SCHUMANN_RULE_DISABLED_CALLS >= 0

    def test_schumann_no_dispara_con_hz_presente(self):
        assert _scanner()._scan_schumann(9.5, 250.0) == []
        assert _scanner()._scan_schumann(8.5, 9.0) == []

    def test_precipitacion_no_dispara_con_hz_presente(self):
        atm = [{"station": "Xalapa", "lat": 19.5, "lon": -96.9,
                "humidity_pct": 88.0, "temp_c": 26.0, "clouds_pct": 92.0,
                "pressure_hpa": 1010.0, "weather_id": 800}]
        assert _scanner()._scan_precipitacion(atm, 8.2) == []

    def test_cada_llamada_bloqueada_suma_al_contador(self):
        antes = mod_scanner._SCHUMANN_RULE_DISABLED_CALLS
        _scanner()._scan_schumann(9.5, 250.0)
        _scanner()._scan_precipitacion([], 8.2)
        assert mod_scanner._SCHUMANN_RULE_DISABLED_CALLS == antes + 2


class TestUmbralesCalibradosConFlagActivado:
    @pytest.fixture(autouse=True)
    def _enciende_regla(self, monkeypatch):
        monkeypatch.setattr(mod_scanner, "SCHUMANN_RULE_ENABLED", True)

    def test_constantes_calibradas(self):
        assert SCHUMANN_ACTIVITY_BONUS == 5.0
        assert SCHUMANN_ACTIVITY_EXTREMA == 8.0

    def test_sin_desviacion_y_actividad_baja_no_dispara(self):
        assert _scanner()._scan_schumann(8.0, 4.0) == []
        assert _scanner()._scan_schumann(7.83, 7.9) == []

    def test_actividad_extrema_sola_si_dispara(self):
        # dev 0.0 (hz = 7.83 exacto) pero pct 9.0 >= EXTREMA 8.0: la
        # actividad sola dispara solo at/por encima del máx WPC histórico.
        dets = _scanner()._scan_schumann(7.83, 9.0)
        assert len(dets) == 1
        assert dets[0].tipo == PrecursorType.SCHUMANN
        assert dets[0].confidence == pytest.approx(0.65)

    def test_desviacion_alta_mas_bonus_da_085(self):
        dets = _scanner()._scan_schumann(9.5, 6.0)
        assert len(dets) == 1
        assert dets[0].confidence == pytest.approx(0.85)
        assert dets[0].values["deviation_hz"] == pytest.approx(1.67, abs=0.01)

    def test_desviacion_alta_sin_bonus_da_07(self):
        dets = _scanner()._scan_schumann(9.5, 4.0)
        assert len(dets) == 1
        assert dets[0].confidence == pytest.approx(0.7)

    def test_desviacion_alta_sin_pct_da_07(self):
        dets = _scanner()._scan_schumann(9.5, None)
        assert len(dets) == 1
        assert dets[0].confidence == pytest.approx(0.7)

    def test_sin_hz_no_dispara_aunque_la_regla_este_encendida(self):
        assert _scanner()._scan_schumann(None, 9.0) == []

    def test_precipitacion_dispara_con_flag_encendido(self):
        atm = [{"station": "Xalapa", "lat": 19.5, "lon": -96.9,
                "humidity_pct": 88.0, "temp_c": 26.0, "clouds_pct": 92.0,
                "pressure_hpa": 1010.0, "weather_id": 800}]
        dets = _scanner()._scan_precipitacion(atm, 8.2)
        assert len(dets) == 1
        assert dets[0].tipo == PrecursorType.PRECIPITACION
