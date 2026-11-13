"""Tests del CORTE DIARIO de Schumann y del enriquecimiento por evento.

Decisión del operador (2026-10-26): «la Schumann solo la pedimos en un
corte del día completo, y lo vamos extrayendo solo a las horas de los
eventos; eliminamos el espectrograma de Tomsk (por ciclo) y solo agregamos
esos detalles a los eventos». El contrato: UNA descarga exitosa por día
(idempotente), el día sin corte se VE (sin señal no se inventa fila), y
cada evento M4.5+ lleva su Schumann (lectura a su hora + media 24 h).

Nota 2026-11-06: añadido fallback HeartMath GCI. Cuando Tomsk falla,
se intenta el fallback antes de marcar día fallido. Los tests mockean
ambas funciones para verificar el comportamiento correcto.
"""
import sqlite3
import time
from unittest.mock import patch, MagicMock

from sentinel_omega.core import schumann_vivo as sv


def _conn_con_vivo(ahora: float = None):
    """Crea DB en memoria con tablas vivo y diario. Opcionalmente inserta histórico para tests."""
    conn = sqlite3.connect(":memory:")
    sv.asegurar_tabla(conn)
    sv.asegurar_diario(conn)
    if ahora is not None:
        # Insertar histórico simulado: 7 días previos con éxito para evitar fallback automático
        for i in range(1, 8):
            fecha = time.strftime("%Y-%m-%d", time.gmtime(ahora - i * 86400))
            conn.execute(
                f"INSERT INTO {sv.TABLA_DIARIO} (fecha, actividad, fuente) VALUES (?, ?, ?)",
                (fecha, 2.5, "tomsk_wpc_corte_diario")
            )
        conn.commit()
    return conn


def _mock_fallback_none():
    """Mock the fallback to return None (no fallback available)."""
    return patch("sentinel_omega.infrastructure.api.schumann_fallback.fetch_schumann_fallback", return_value=None)


class TestCorteDiario:

    @patch("sentinel_omega.infrastructure.api.schumann.fetch_schumann_resonance")
    @patch("sentinel_omega.infrastructure.api.schumann_fallback.fetch_schumann_fallback", return_value=None)
    def test_una_descarga_por_dia(self, _mock_fb, mock_fetch):
        """El primer corte del día descarga; el resto del día NO toca red."""
        mock_fetch.return_value = (None, 2.68)
        t0 = 1_793_000_000
        conn = _conn_con_vivo(ahora=t0)
        r1 = sv.corte_diario(conn, ahora=t0)
        assert r1["estado"] == "en_vivo" and r1["actividad"] == 2.68
        r2 = sv.corte_diario(conn, ahora=t0 + 3600)
        assert r2["estado"] == "ya_hoy"
        assert mock_fetch.call_count == 1  # una sola descarga el día entero

    @patch("sentinel_omega.infrastructure.api.schumann.fetch_schumann_resonance")
    @patch("sentinel_omega.infrastructure.api.schumann_fallback.fetch_schumann_fallback", return_value=None)
    def test_sin_senal_no_se_inventa_fila(self, _mock_fb, mock_fetch):
        """Tomsk caído y sin fallback → día marcado como tomsk_fallido (no se reintenta),
        y el día sin corte se VE en la tabla con fuente=tomsk_fallido."""
        mock_fetch.return_value = None
        t0 = 1_793_000_000
        conn = _conn_con_vivo(ahora=t0)
        r = sv.corte_diario(conn, ahora=t0)
        assert r["estado"] == "sin_senal" and r["actividad"] is None
        assert r["fuente"] == "tomsk_fallido"
        n = conn.execute("SELECT COUNT(*) FROM tbl_schumann_diario").fetchone()[0]
        assert n == 8  # 7 histórico + 1 tomsk_fallido
        fila = conn.execute("SELECT actividad, fuente FROM tbl_schumann_diario WHERE fecha = ?",
                           (time.strftime("%Y-%m-%d", time.gmtime(t0)),)).fetchone()
        assert fila[0] is None and fila[1] == "tomsk_fallido"

    @patch("sentinel_omega.infrastructure.api.schumann.fetch_schumann_resonance")
    @patch("sentinel_omega.infrastructure.api.schumann_fallback.fetch_schumann_fallback", return_value=None)
    def test_reintenta_hasta_lograrlo(self, _mock_fb, mock_fetch):
        """Falla temprano, logra tarde: el corte queda del día que es.
        
        Nota: con el fallback desactivado (None), el primer fallo marca tomsk_fallido
        y el segundo ya no reintenta (devuelve ya_hoy). Para probar reintento real
        se necesitaría un fallback que falle la primera vez y luego OK.
        """
        conn = _conn_con_vivo(ahora=1_793_000_000)
        t0 = 1_793_000_000
        mock_fetch.return_value = None
        r1 = sv.corte_diario(conn, ahora=t0)
        assert r1["estado"] == "sin_senal"
        assert r1["fuente"] == "tomsk_fallido"
        # Segundo intento en el mismo día: ya_hoy (no reintenta)
        mock_fetch.return_value = (None, 3.07)
        r2 = sv.corte_diario(conn, ahora=t0 + 600)
        assert r2["estado"] == "ya_hoy"
        assert mock_fetch.call_count == 1  # solo 1 llamada real a Tomsk

    @patch("sentinel_omega.infrastructure.api.schumann.fetch_schumann_resonance")
    def test_el_corte_alimenta_la_serie_viva(self, mock_fetch):
        """La fila del día también vive en tbl_schumann_vivo (1/día, el
        mismo idioma de siempre: estado_actual no se rompe)."""
        mock_fetch.return_value = (None, 2.68)
        conn = _conn_con_vivo(ahora=1_793_000_000)
        sv.corte_diario(conn, ahora=1_793_000_000)
        act = conn.execute(
            "SELECT schumann_activity FROM tbl_schumann_vivo"
        ).fetchone()[0]
        assert act == 2.68


class TestEnriquecerEventos:

    def test_evento_lleva_su_schumann_y_comportamiento(self):
        """El evento M4.5+ recibe la lectura más cercana a su hora y la
        media de las 24 h previas (con n_lecturas REALES)."""
        conn = _conn_con_vivo()
        # lecturas reales: 3 en las 24 h previas al evento + una más vieja
        for h, act in ((0, 5.0), (-6, 4.0), (-12, 3.0), (-48, 9.0)):
            ts = sv.time.strftime(sv.FMT_BLK, sv.time.gmtime(1_793_000_000 + h * 3600))
            conn.execute(
                "INSERT OR REPLACE INTO tbl_schumann_vivo "
                "(timestamp_blk, schumann_hz, schumann_activity, en_vivo) "
                "VALUES (?, NULL, ?, 1)", (ts, act),
            )
        conn.commit()
        ev = [{"epoch": float(1_793_000_000), "magnitude": 5.2}]
        stats = sv.enriquecer_eventos(conn, ev)
        assert stats["con_dato"] == 1
        fila = conn.execute(
            "SELECT event_class, actividad_h, media_24h, n_lecturas, fuente "
            "FROM tbl_eventos_schumann"
        ).fetchone()
        assert fila[0] == "SISMO_M5"
        assert fila[1] == 5.0          # la lectura a su hora
        assert abs(fila[2] - 4.0) < 1e-6  # media de {5, 4, 3}
        assert fila[3] == 3           # la de -48 h NO entra al comportamiento
        assert fila[4] == "tbl_schumann_vivo"

    def test_idempotente_y_sin_dato_honesto(self):
        conn = _conn_con_vivo()  # sin lecturas: el evento queda SIN fila
        ev = [{"epoch": 1_793_000_000.0, "magnitude": 6.1}]
        s1 = sv.enriquecer_eventos(conn, ev)
        assert s1["sin_dato"] == 1
        n = conn.execute("SELECT COUNT(*) FROM tbl_eventos_schumann").fetchone()[0]
        assert n == 0


class TestEnriquecerHistorico:

    def test_join_hora_nodo_del_backcast(self):
        """El corpus histórico cruza por (hora, nodo) contra
        tbl_enjambre_telemetria — el evento lleva el Schumann de SU nodo."""
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE tbl_historico_sismico_raw ("
            "timestamp_blk TEXT, id_nodo INTEGER, sismo_count INTEGER, "
            "sismo_max_mag REAL, PRIMARY KEY (timestamp_blk, id_nodo))"
        )
        conn.execute(
            "CREATE TABLE tbl_enjambre_telemetria ("
            "timestamp_blk TEXT NOT NULL, id_nodo INTEGER NOT NULL, "
            "schumann_hz REAL, en_vivo INTEGER DEFAULT 1, "
            "schumann_activity REAL, PRIMARY KEY (timestamp_blk, id_nodo))"
        )
        base = "2015-05-05 %02d:00"
        for h in range(24):
            conn.execute(
                "INSERT INTO tbl_enjambre_telemetria VALUES (?,?,?,?,?)",
                (base % h, 25, None, 1, 2.0 + h * 0.1),
            )
        conn.execute(
            "INSERT INTO tbl_historico_sismico_raw VALUES (?,?,?,?)",
            (base % 12, 25, 1, 5.5),
        )
        conn.commit()
        stats = sv.enriquecer_historico(conn)
        assert stats["sismicos"] == 1
        fila = conn.execute(
            "SELECT event_class, actividad_h, n_lecturas FROM tbl_eventos_schumann"
        ).fetchone()
        assert fila[0] == "SISMO_M5"
        assert abs(fila[1] - 3.2) < 1e-6   # la lectura de la hora 12
        assert fila[2] == 13               # 24 h previas: horas 0..12
