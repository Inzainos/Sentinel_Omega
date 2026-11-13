"""FASE 2 — D4 H1/H3: NULL honesto en _patron_omega y cobertura Schumann
en los reportes.

H1: `schumann_mean` None es "sin dato", no 0. El viejo
`f.get("schumann_mean", 0) or 0` convertía la ausencia en una medición de
0. El arreglo es seguro porque el único consumidor
(construir_correlaciones_omega) solo usa la presencia del flag SCHUMANN
en el patrón, no el valor: None y 0.0 dan el mismo patrón.

H3: los reportes muestran cobertura (días con dato vs NULL, último día
con dato, fuente del corte) y son fail-soft si falta la tabla.
"""
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from deploy.generar_reporte import _seccion_cobertura_schumann as _cob_gen  # noqa: E402
from deploy.reporte_ejecutivo import _cobertura_schumann_lineas as _cob_eje  # noqa: E402
from deploy.reporte_periodico import _seccion_cobertura_schumann as _cob_per  # noqa: E402
from sentinel_omega.infrastructure.pipeline.mantenimiento import _patron_omega  # noqa: E402


def _base_sin_schumann():
    # Calma en todo lo demás: ningún otro flag debe aparecer.
    return {"kp_max": 1.0, "kp_max_72h": 1.0, "bz_min": 0.0,
            "proton_max": 0.0, "sismo_count_win": 0, "sismo_max_mag_win": 0.0,
            "so2_kt_win": 0, "erupciones_win": 0, "btc_volatilidad": 0.0,
            "fase_lunar": 0.5}


class TestPatronOmegaH1:
    def test_none_no_dispara_schumann(self):
        f = _base_sin_schumann()
        f["schumann_mean"] = None
        assert "SCHUMANN" not in _patron_omega(f)

    def test_cero_no_dispara_schumann(self):
        f = _base_sin_schumann()
        f["schumann_mean"] = 0.0
        assert "SCHUMANN" not in _patron_omega(f)

    def test_none_y_cero_dan_el_mismo_patron(self):
        a = _base_sin_schumann(); a["schumann_mean"] = None
        b = _base_sin_schumann(); b["schumann_mean"] = 0.0
        assert _patron_omega(a) == _patron_omega(b)

    def test_valor_alto_si_dispara_schumann(self):
        f = _base_sin_schumann()
        f["schumann_mean"] = 9.0
        assert "SCHUMANN" in _patron_omega(f)

    def test_umbral_85_no_dispara(self):
        f = _base_sin_schumann()
        f["schumann_mean"] = 8.5
        assert "SCHUMANN" not in _patron_omega(f)


def _db_cobertura(tmp_path):
    db = str(tmp_path / "cob.db")
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE tbl_schumann_diario ("
        "fecha TEXT, actividad REAL, fuente TEXT)")
    for i in range(10):
        conn.execute(
            "INSERT INTO tbl_schumann_diario VALUES (?, 2.17, 'resonanceone_live')",
            (f"2026-11-{i + 1:02d}",))
    for i in range(10, 20):
        conn.execute(
            "INSERT INTO tbl_schumann_diario VALUES (?, NULL, 'tomsk_fallido')",
            (f"2026-11-{i + 1:02d}",))
    conn.execute(
        "CREATE TABLE TBL_PRECURSORES_COSMICOS (schumann_hz REAL)")
    conn.execute("INSERT INTO TBL_PRECURSORES_COSMICOS VALUES (NULL)")
    conn.execute("INSERT INTO TBL_PRECURSORES_COSMICOS VALUES (NULL)")
    conn.commit()
    return conn


class TestCoberturaSchumannH3:
    def test_periodico_cuenta_dias_con_dato_y_null(self, tmp_path):
        conn = _db_cobertura(tmp_path)
        texto = "\n".join(_cob_per(conn))
        assert "20 días" in texto
        assert "10 con dato" in texto
        assert "10 NULL" in texto
        assert "2026-11-10" in texto  # último día con dato
        assert "resonanceone_live" in texto
        assert "0 no-nulos" in texto  # schumann_hz en PREC: 0 de 2

    def test_ejecutivo_cuenta_dias_con_dato_y_null(self, tmp_path):
        conn = _db_cobertura(tmp_path)
        ahora = datetime(2026, 11, 13, 0, 3, 47, tzinfo=timezone.utc)
        texto = "\n".join(_cob_eje(conn, ahora))
        assert "20 días" in texto
        assert "10 con dato" in texto
        assert "10 NULL" in texto
        assert "2026-11-10" in texto

    def test_generar_cuenta_dias_con_dato_y_null(self, tmp_path):
        conn = _db_cobertura(tmp_path)
        ahora = datetime(2026, 11, 13, 0, 3, 47, tzinfo=timezone.utc)
        texto = "\n".join(_cob_gen(conn, ahora))
        assert "20 días" in texto
        assert "10 con dato" in texto

    def test_fail_soft_sin_tabla(self, tmp_path):
        conn = sqlite3.connect(str(tmp_path / "vacia.db"))
        assert _cob_per(conn) != []
        assert _cob_eje(conn, datetime.now(timezone.utc)) != []
        assert _cob_gen(conn, datetime.now(timezone.utc)) != []
