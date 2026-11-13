"""Tests de la evidencia cimática en la cascada de plantillas (2026-10-26).

La P2H es la superficie que el operador lee en Telegram cada 3 h: la línea
de la figura del Padre lleva la etiqueta «contexto, no predicción» PEGADA
al número — la calibración mostró que la calma empareja igual, y sin la
etiqueta la línea se leería como predicción.
"""
import sqlite3

from sentinel_omega.infrastructure.messaging.plantillas_concilio import (
    _render_p2h,
)


def _snap_con_evidencia(exacta: bool):
    return {
        "ts": 0.0,
        "cimatica_evidencia": {
            "presente": True,
            "match_exacto": exacta,
            "mejor_sim": 1.0 if exacta else 0.91,
            "mejor_clase": "SISMO_M5",
            "mejor_n_eventos": 2,
            "resumen": "…",
        },
    }


class TestRenderP2hEvidencia:

    def test_linea_similar_con_etiqueta(self):
        txt = _render_p2h(_snap_con_evidencia(exacta=False))
        assert "Figura del Padre: similar 0.91 a víspera de" in txt
        assert "contexto, no predicción" in txt

    def test_linea_identica(self):
        txt = _render_p2h(_snap_con_evidencia(exacta=True))
        assert "IDÉNTICA" in txt
        assert "2×" in txt
        assert "contexto, no predicción" in txt

    def test_sin_evidencia_no_hay_linea(self):
        txt = _render_p2h({"ts": 0.0, "cimatica_evidencia": None})
        assert "Figura del Padre" not in txt

    def test_evidencia_sin_empareje_no_hay_linea(self):
        """mejor_sim 0 = sin emparejes: la P2H no se llena de ruido."""
        ev = _snap_con_evidencia(False)["cimatica_evidencia"]
        ev["mejor_sim"] = 0.0
        txt = _render_p2h({"ts": 0.0, "cimatica_evidencia": ev})
        assert "Figura del Padre" not in txt
