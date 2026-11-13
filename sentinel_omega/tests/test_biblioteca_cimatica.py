"""Tests del POBLADOR de la biblioteca cimática (construir_biblioteca).

El contrato, no la habilidad (regla del proyecto): n_eventos cuenta
EVENTOS cuya víspera produjo la clave — no avistamientos, no la frecuencia
mezclada de tbl_cimatica_patrones. La extracción de ventana se mockea
porque su maquinaria tiene sus propios tests; aquí se prueba la AGREGACIÓN.
"""
import sqlite3
from unittest.mock import patch

import pytest

from sentinel_omega.core.firmas import biblioteca_cimatica as bc


# ── Fixture: DB mínima con los anclajes de eventos ───────────────────────────
def _conn_minima(sismos, no_sismicos=()):
    """sismos: [(ts, nodo, mag)] · no_sismicos: [(ts, nodo, clase)]"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE tbl_historico_sismico_raw ("
        "timestamp_blk TEXT, id_nodo INTEGER, sismo_count INTEGER DEFAULT 0, "
        "sismo_max_mag REAL DEFAULT 0.0, "
        "PRIMARY KEY (timestamp_blk, id_nodo))"
    )
    conn.execute(
        "CREATE TABLE tbl_eventos_no_sismicos (timestamp_blk TEXT, "
        "id_nodo INTEGER, event_class TEXT, fuente TEXT, intensidad REAL)"
    )
    for ts, nodo, mag in sismos:
        conn.execute(
            "INSERT INTO tbl_historico_sismico_raw VALUES (?,?,?,?)",
            (ts, nodo, 1, mag),
        )
    for ts, nodo, clase in no_sismicos:
        conn.execute(
            "INSERT INTO tbl_eventos_no_sismicos VALUES (?,?,?,?,?)",
            (ts, nodo, clase, "test", 1.0),
        )
    return conn


FEAT_A = {"kp_max": 3.0, "viento_avg": 330.0, "bz_mean": 1.2}
FEAT_B = {"kp_max": 7.0, "viento_avg": 700.0, "bz_mean": -8.5}


class TestConstruirBiblioteca:

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_cuenta_eventos_no_avistamientos(self, mock_extraer):
        """Dos eventos cuya víspera dio LA MISMA clave → n_eventos=2, UNA fila.

        La frecuencia de patrones contaría avistamientos; la biblioteca
        cuenta eventos. Es el corazón del contrato (regla 11).
        """
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(FEAT_A)
        # Both events >= 5.5 (SISMO_M5) to test same class grouping
        conn = _conn_minima([
            ("2020-01-01 00:00", 25, 5.7),
            ("2020-02-01 00:00", 25, 5.8),   # misma clase (SISMO_M5), misma víspera
        ])
        stats = bc.construir_biblioteca(conn)

        filas = conn.execute(
            "SELECT clave_figura, event_class, n_eventos FROM tbl_cimatica_biblioteca"
        ).fetchall()
        assert len(filas) == 1
        assert filas[0]["event_class"] == "SISMO_M5"
        assert filas[0]["n_eventos"] == 2
        assert stats["vísperas"] == 2
        assert stats["figuras"] == 1

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_figuras_distintas_filas_distintas(self, mock_extraer):
        """Vísperas con telemetría distinta → claves distintas → 2 filas."""
        mock_extraer.side_effect = lambda conn, ts, nodo: (
            dict(FEAT_A) if "01" in ts else dict(FEAT_B)
        )
        conn = _conn_minima([
            ("2020-01-01 00:00", 25, 5.7),  # SISMO_M5
            ("2020-02-15 00:00", 25, 6.1),  # SISMO_M6
        ])
        bc.construir_biblioteca(conn)

        filas = conn.execute(
            "SELECT event_class, n_eventos FROM tbl_cimatica_biblioteca "
            "ORDER BY event_class"
        ).fetchall()
        assert len(filas) == 2
        assert {f["event_class"] for f in filas} == {"SISMO_M5", "SISMO_M6"}
        assert all(f["n_eventos"] == 1 for f in filas)

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_sin_datos_se_cuenta_no_se_inventa(self, mock_extraer):
        """Víspera sin cobertura (None) → sin_datos +1 y NINGUNA fila:
        la ventana vacía no entra a la biblioteca (regla 2)."""
        mock_extraer.return_value = None
        conn = _conn_minima([("2020-01-01 00:00", 25, 5.2)])
        stats = bc.construir_biblioteca(conn)

        n = conn.execute(
            "SELECT COUNT(*) FROM tbl_cimatica_biblioteca"
        ).fetchone()[0]
        assert n == 0
        assert stats["sin_datos"] == 1
        assert stats["vísperas"] == 0

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_idempotente_reconstruccion_completa(self, mock_extraer):
        """Correr dos veces no duplica: la tabla es DERIVADA, DELETE+INSERT."""
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(FEAT_A)
        conn = _conn_minima([
            ("2020-01-01 00:00", 25, 5.2),
            ("2020-02-01 00:00", 25, 5.2),
        ])
        bc.construir_biblioteca(conn)
        bc.construir_biblioteca(conn)

        filas = conn.execute(
            "SELECT n_eventos FROM tbl_cimatica_biblioteca"
        ).fetchall()
        assert len(filas) == 1
        assert filas[0]["n_eventos"] == 2

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_no_sismicos_con_su_clase(self, mock_extraer):
        """Los eventos no sísmicos entran con SU event_class, no con la del
        mag_0 (que sería SISMO_M2_obs — un sismo inexistente)."""
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(FEAT_B)
        conn = _conn_minima(
            sismos=[("2020-01-01 00:00", 25, 4.6)],
            no_sismicos=[("2020-03-01 00:00", 25, "TORMENTA_KP6")],
        )
        bc.construir_biblioteca(conn)

        clases = {
            r[0] for r in conn.execute(
                "SELECT event_class FROM tbl_cimatica_biblioteca"
            ).fetchall()
        }
        assert clases == {"SISMO_M4", "TORMENTA_KP6"}

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_figura_json_es_la_ultima_víspera(self, mock_extraer):
        """figura_json guarda la telemetría COMPLETA de la última víspera
        con esa clave — es el payload comparable de consultar()."""
        fe = {"kp_max": 3.0, "viento_avg": 330.0, "bz_mean": 1.2}
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(fe)
        conn = _conn_minima([("2020-01-01 00:00", 25, 5.2)])
        bc.construir_biblioteca(conn)

        import json
        fila = conn.execute(
            "SELECT figura_json FROM tbl_cimatica_biblioteca"
        ).fetchone()
        assert json.loads(fila["figura_json"]) == fe


class TestConsultarEscalaReal:

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_lookup_encuentra_mas_alla_del_top300(self, mock_extraer):
        """El bug del LIMIT 300 (2026-10-25): con una biblioteca grande, la
        figura viva casi nunca cae en el top-300 por n_eventos y el lookup
        daba 0 hits SIEMPRE. El escaneo completo debe encontrar la similar
        aunque esté fuera del top por n_eventos."""
        bc._CONSULTA_CACHE.clear()
        # 350 eventos con vísperas de baja frecuencia (n_eventos=1) y UNA
        # figura repetida en el medio: ninguna está en un top-300 por
        # n_eventos de forma distinguible... el punto es que el escaneo
        # completo las mira TODAS.
        def features_porEvento(conn, ts, nodo):
            return {"kp_max": 1.0, "viento_avg": 330.0 + hash(ts) % 50}
        mock_extraer.side_effect = features_porEvento
        sismos = [(f"2020-{i//28+1:02d}-{i%28+1:02d} 00:00", 25, 5.0 + (i % 3) * 0.5)
                  for i in range(350)]
        conn = _conn_minima(sismos)
        bc.construir_biblioteca(conn)

        # Clave viva que comparte tokens con las vísperas
        clave_viva = bc.clave_patron({"kp_max": 1.0, "viento_avg": 340.0})
        res = bc.consultar(conn, {}, {}, clave_figura=clave_viva)
        assert res["n_hits"] > 0
        assert res["best_similarity"] > 0
        assert all(s["source"] == "tbl_cimatica_biblioteca" for s in res["similares"])

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_lookup_match_exacto_sim_1(self, mock_extraer):
        """La misma clave de una víspera de la biblioteca → similitud 1.0."""
        bc._CONSULTA_CACHE.clear()
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(FEAT_B)
        conn = _conn_minima([("2020-01-01 00:00", 25, 6.2)])
        bc.construir_biblioteca(conn)
        clave_viva = bc.clave_patron(dict(FEAT_B))
        res = bc.consultar(conn, {}, {}, clave_figura=clave_viva)
        assert res["best_similarity"] == 1.0
        assert res["similares"][0]["event_class"] == "SISMO_M6"


class TestCimaticaEvidencia:

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_evidencia_match_exacto_con_etiqueta_honesta(self, mock_extraer):
        """Figura idéntica a una víspera → match_exacto=True CON la
        etiqueta de contexto (la calibración viaja dentro: la calma
        empareja igual). Un consumidor que lo lea como predicción tiene
        que toparse con el nulo."""
        bc._CONSULTA_CACHE.clear()
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(FEAT_A)
        conn = _conn_minima([("2020-01-01 00:00", 25, 5.7)])  # SISMO_M5 (enforceable)
        bc.construir_biblioteca(conn)

        ev = bc.cimatica_evidencia(conn, dict(FEAT_A))
        assert ev["presente"] is True
        assert ev["match_exacto"] is True
        assert ev["mejor_clase"] == "SISMO_M5"
        assert ev["mejor_n_eventos"] == 1
        assert ev["calibracion"]["calma_match_exacto"] > 0
        assert "no es predicción" in ev["resumen"]

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_evidencia_similar_no_exacta(self, mock_extraer):
        """Figura que comparte tokens pero no toda → similar, no exacta."""
        bc._CONSULTA_CACHE.clear()
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(FEAT_A)
        conn = _conn_minima([("2020-01-01 00:00", 25, 5.7)])  # SISMO_M5
        bc.construir_biblioteca(conn)

        viva = {"kp_max": 3.5, "viento_avg": 331.0, "bz_mean": 1.0}
        ev = bc.cimatica_evidencia(conn, viva)
        assert ev["match_exacto"] is False
        assert 0 < ev["mejor_sim"] < 1.0
        assert "no predicción" in ev["resumen"]

    def test_evidencia_sin_biblioteca(self):
        """Sin tabla → presente=False honesto, no excepción."""
        conn = _conn_minima([])
        ev = bc.cimatica_evidencia(conn, {"kp_max": 3.0})
        assert ev["presente"] is False


class TestIntegrarEventoBiblioteca:

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_integra_por_evento_y_es_idempotente(self, mock_extraer):
        """El evento M4.5+ integra las figuras de SU víspera: n_eventos+1
        por evento y figura. Correr OTRA VEZ el mismo epoch no infla
        (guarda de tbl_cimatica_bib_eventos)."""
        bc._CONSULTA_CACHE.clear()
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(FEAT_A)
        # patrón vivo previo: registrado con última aparición DENTRO de la
        # víspera del evento (2020-02-01 12:00, ventana 72h)
        conn = _conn_minima([])
        bc.clave_patron(dict(FEAT_A))
        from sentinel_omega.core.firmas.cimatica import registrar_snapshot
        registrar_snapshot(conn, dict(FEAT_A), id_nodo=None,
                            event_class=None, silencioso=True)
        # recoloca la última aparición dentro de la víspera del evento
        conn.execute(
            "UPDATE tbl_cimatica_patrones SET ultima_vez = '2020-02-01 06:00:00'"
        )
        conn.commit()

        ev = [{"epoch": _epoch("2020-02-01 12:00:00"), "magnitude": 5.0}]
        # secuencia de producción (verificacion.py): retroetiquetar PRIMERO
        # (etiqueta las figuras de la víspera), luego integrar
        from sentinel_omega.core.firmas.cimatica import (
            retroetiquetar_patrones,
        )
        retroetiquetar_patrones(conn, ev)
        bc.integrar_evento_biblioteca(conn, ev)
        fila = conn.execute(
            "SELECT n_eventos FROM tbl_cimatica_biblioteca"
        ).fetchone()
        assert fila is not None and fila["n_eventos"] == 1

        # idempotencia por epoch: re-verificar el mismo sismo no suma
        bc.integrar_evento_biblioteca(conn, ev)
        fila = conn.execute(
            "SELECT n_eventos FROM tbl_cimatica_biblioteca"
        ).fetchone()
        assert fila["n_eventos"] == 1

    @patch("sentinel_omega.core.firmas.signature_engine.extraer_features_ventana")
    def test_dedup_dentro_del_evento(self, mock_extraer):
        """Un evento con la MISMA clave en general y en nodo cuenta UNO
        (n_eventos cuenta eventos, no patrones — el mismo contrato del
        poblador)."""
        bc._CONSULTA_CACHE.clear()
        mock_extraer.side_effect = lambda conn, ts, nodo: dict(FEAT_A)
        conn = _conn_minima([])
        from sentinel_omega.core.firmas.cimatica import registrar_snapshot
        for nodo in (None, 25):
            registrar_snapshot(conn, dict(FEAT_A), id_nodo=nodo,
                               event_class=None, silencioso=True)
        conn.execute(
            "UPDATE tbl_cimatica_patrones SET ultima_vez = '2020-02-01 06:00:00'"
        )
        conn.commit()

        ev = [{"epoch": _epoch("2020-02-01 12:00:00"), "magnitude": 5.0}]
        from sentinel_omega.core.firmas.cimatica import (
            retroetiquetar_patrones,
        )
        retroetiquetar_patrones(conn, ev)
        bc.integrar_evento_biblioteca(conn, ev)
        fila = conn.execute(
            "SELECT n_eventos FROM tbl_cimatica_biblioteca"
        ).fetchone()
        assert fila["n_eventos"] == 1


def _epoch(ts: str) -> float:
    import datetime as dt
    return dt.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=dt.timezone.utc).timestamp()
