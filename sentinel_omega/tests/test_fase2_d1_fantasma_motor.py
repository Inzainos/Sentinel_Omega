"""FASE 2 — D1: los 7 sitios de lectura usan la escala del MOTOR (11.5/28.6/77.7).

Ancla: las FUNCIONES, no las cadenas (regla 12 del repo). Cada test llama
a la función y comprueba su VALOR DE RETORNO en los bordes exactos del
motor. Los viejos cortes V32 (5/15/30) aparecen solo como los valores que
DEBEN DEJAR de clasificar como antes: p. ej. fantasma=15.0 ya no es HIGH
(era HIGH en V32) sino MODERATE; fantasma=30.0 ya no es CRITICAL sino HIGH.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from sentinel_omega.core.precursor.risk_calculator import RISK_THRESHOLDS
from sentinel_omega.core.precursor.scanner import PrecursorScanner

REPO_ROOT = Path(__file__).resolve().parents[2]

import sys
sys.path.insert(0, str(REPO_ROOT))

from deploy.reporte_ejecutivo import _estado_ejecutivo  # noqa: E402
from deploy.reporte_periodico import _nivel_fantasma  # noqa: E402
from sentinel_omega.infrastructure.messaging.consenso_vigilante import (  # noqa: E402
    _nivel_from_fantasma,
)


def test_umbrales_del_motor_son_los_del_risk_calculator():
    assert RISK_THRESHOLDS == {
        "LOW": 0.0, "MODERATE": 11.5, "HIGH": 28.6, "CRITICAL": 77.7,
    }


class TestScanFantasmaMotor:
    def _scanner(self):
        return PrecursorScanner()

    def test_por_debajo_de_high_no_emite(self):
        s = self._scanner()
        assert s._scan_fantasma(SimpleNamespace(fantasma=28.5, risk_level="MODERATE")) == []
        assert s._scan_fantasma(SimpleNamespace(fantasma=11.5, risk_level="MODERATE")) == []
        assert s._scan_fantasma(SimpleNamespace(fantasma=15.0, risk_level="HIGH")) == []

    def test_en_high_emite_confianza_07(self):
        s = self._scanner()
        dets = s._scan_fantasma(SimpleNamespace(fantasma=28.6, risk_level="HIGH"))
        assert len(dets) == 1
        assert dets[0].confidence == 0.7
        assert dets[0].values["fantasma"] == 28.6

    def test_en_critical_emite_confianza_085(self):
        s = self._scanner()
        dets = s._scan_fantasma(SimpleNamespace(fantasma=77.7, risk_level="CRITICAL"))
        assert len(dets) == 1
        assert dets[0].confidence == 0.85

    def test_sin_risk_o_sin_fantasma_no_emite(self):
        s = self._scanner()
        assert s._scan_fantasma(None) == []
        assert s._scan_fantasma(SimpleNamespace(fantasma=None, risk_level="LOW")) == []
        assert s._scan_fantasma(SimpleNamespace(risk_level="LOW")) == []


class TestNivelFantasmaMotor:
    @pytest.mark.parametrize("valor,esperado", [
        (None, "—"),
        (0.0, "LOW · calma"),
        (11.4, "LOW · calma"),
        (11.5, "MODERATE · atención"),
        (15.0, "MODERATE · atención"),  # V32 decía HIGH; motor dice MODERATE
        (28.5, "MODERATE · atención"),
        (28.6, "HIGH · avisar"),
        (30.0, "HIGH · avisar"),  # V32 decía CRITICAL; motor dice HIGH
        (77.6, "HIGH · avisar"),
        (77.7, "CRITICAL · protocolo"),
        (100.0, "CRITICAL · protocolo"),
    ])
    def test_bordes(self, valor, esperado):
        assert _nivel_fantasma(valor) == esperado


class TestEstadoEjecutivoMotor:
    def test_rojo_solo_breach_mas_critical(self):
        assert _estado_ejecutivo(77.7, 0, True, 0.0) == ("ROJO", "ESCALAMIENTO")
        # 30.0 era CRITICAL en V32; en motor es HIGH -> NARANJA, no ROJO
        assert _estado_ejecutivo(30.0, 0, True, 0.0) == ("NARANJA", "PRE-ESCALAMIENTO")

    def test_naranja_breach_o_high_mas_firma(self):
        assert _estado_ejecutivo(28.6, 0, False, 0.9) == ("NARANJA", "PRE-ESCALAMIENTO")
        assert _estado_ejecutivo(0.0, 0, True, 0.0) == ("NARANJA", "PRE-ESCALAMIENTO")
        # 15.0 con firma 0.9: en V32 era HIGH+firma -> NARANJA; en motor
        # 15.0 es MODERATE -> AMARILLO
        assert _estado_ejecutivo(15.0, 0, False, 0.9) == ("AMARILLO", "VIGILANCIA REFORZADA")

    def test_amarillo_moderate_o_firma_080(self):
        assert _estado_ejecutivo(11.5, 0, False, 0.0) == ("AMARILLO", "VIGILANCIA REFORZADA")
        assert _estado_ejecutivo(0.0, 0, False, 0.80) == ("AMARILLO", "VIGILANCIA REFORZADA")

    def test_azul_y_verde_no_caen_en_none(self):
        # La cola AZUL/VERDE existía en el original; la inserción del helper
        # H3 la había dejado como código muerto (reparado 2026-11-12). Sin
        # ella, el estado en calma devolvía None y el desempaquetado del
        # llamador (:290) rompía el reporte ejecutivo.
        assert _estado_ejecutivo(11.4, 0, False, 0.0) == ("AZUL", "OBSERVACIÓN")
        assert _estado_ejecutivo(0.0, 2, False, 0.0) == ("AZUL", "OBSERVACIÓN")
        assert _estado_ejecutivo(0.0, 0, False, 0.0) == ("VERDE", "ESTABLE")
        assert _estado_ejecutivo(None, 0, False, 0.0) == ("VERDE", "ESTABLE")


class TestNivelFromFantasmaEsVocabularioDistinto:
    # D1: NO se unifica a la escala del motor (texto de Telegram, no bandas
    # de riesgo). Se fija el comportamiento para que un cambio futuro sea
    # deliberado, no accidental.
    @pytest.mark.parametrize("valor,esperado", [
        (6.0, "alto"), (6.5, "alto"), (3.0, "medio"), (5.9, "medio"),
        (0.0, "bajo"), (2.9, "bajo"), (None, "n/d"), ("x", "n/d"),
    ])
    def test_cortes_6_3_sin_cambio(self, valor, esperado):
        assert _nivel_from_fantasma(valor) == esperado


def test_sentinel_yaml_usa_valores_del_motor():
    cfg = yaml.safe_load((REPO_ROOT / "sentinel_omega" / "config" / "sentinel.yaml").read_text(encoding="utf-8"))
    prec = cfg["precursor"]
    assert prec["phantom_threshold"] == 28.6
    assert prec["risk_levels"] == {
        "low": 0.0, "moderate": 11.5, "high": 28.6, "critical": 77.7,
    }
