"""FASE 2 — D1 escala_version: columna + vistas en DBs nuevas y migración
de DBs ya creadas (schema.py).

Frontera de era medida (DB viva modo ro, 2026-11-12): timestamp <
1790340898 (2026-09-25 12:54:58 UTC) => 'V32', en adelante => 'motor'.
Las filas históricas NO se tocan: escala_version NULL y la vista deriva
la era por timestamp; el nivel escrito se conserva como
nivel_riesgo_escrito.
"""
import sqlite3

from sentinel_omega.infrastructure.database.schema import init_database

FRONTERA = 1790340898


def _columnas(conn, tabla):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({tabla})")]


def test_init_database_crea_columna_y_vistas():
    import tempfile, os
    db = os.path.join(tempfile.mkdtemp(), "nueva.db")
    conn = init_database(db)
    try:
        assert "escala_version" in _columnas(conn, "TBL_PRECURSORES_COSMICOS")
        assert "escala_version" in _columnas(conn, "TBL_CICLOS")
        vistas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'")}
        assert "v_precursores_motor" in vistas
        assert "v_ciclos_motor" in vistas
        # v_resumen_diario_motor NO va en init_database: tbl_resumen_diario
        # la crea mantenimiento.py, no el DDL (ver reporte FASE 2).
        assert "v_resumen_diario_motor" not in vistas
    finally:
        conn.close()


def test_vista_deriva_era_y_respeta_lo_almacenado():
    import tempfile, os
    db = os.path.join(tempfile.mkdtemp(), "nueva.db")
    conn = init_database(db)
    try:
        # Pre-frontera, sin escala_version: era V32, nivel escrito HIGH
        # (15.10) pero motor MODERATE.
        conn.execute(
            "INSERT INTO TBL_PRECURSORES_COSMICOS "
            "(timestamp, fantasma, nivel_riesgo) VALUES (?, 15.10, 'HIGH')",
            (FRONTERA - 1,))
        # Post-frontera, sin escala_version: era motor.
        conn.execute(
            "INSERT INTO TBL_PRECURSORES_COSMICOS "
            "(timestamp, fantasma, nivel_riesgo) VALUES (?, 15.10, 'MODERATE')",
            (FRONTERA,))
        # Escala almacenada manda sobre la era derivada.
        conn.execute(
            "INSERT INTO TBL_PRECURSORES_COSMICOS "
            "(timestamp, fantasma, nivel_riesgo, escala_version) "
            "VALUES (?, 80.0, 'CRITICAL', 'motor')",
            (FRONTERA - 100,))
        conn.commit()
        filas = [tuple(r) for r in conn.execute(
            "SELECT timestamp, nivel_riesgo_escrito, escala_version, "
            "nivel_riesgo_motor FROM v_precursores_motor ORDER BY timestamp")]
        assert filas[0] == (FRONTERA - 100.0, "CRITICAL", "motor", "CRITICAL")
        assert filas[1] == (FRONTERA - 1.0, "HIGH", "V32", "MODERATE")
        assert filas[2] == (FRONTERA + 0.0, "MODERATE", "motor", "MODERATE")
    finally:
        conn.close()


def test_migracion_anade_la_columna_a_db_vieja(tmp_path):
    # DB "vieja": esquema completo SIN escala_version. Se construye con
    # init_database y se le quita la columna (ALTER TABLE DROP COLUMN,
    # SQLite >= 3.35) tras borrar las vistas que la referencian — es el
    # estado exacto de una DB creada antes del parche. init_database debe
    # re-añadirla vía EXPECTED_COLUMNS.
    db = str(tmp_path / "vieja.db")
    conn = init_database(db)
    conn.execute("DROP VIEW v_precursores_motor")
    conn.execute("DROP VIEW v_ciclos_motor")
    conn.execute("ALTER TABLE TBL_PRECURSORES_COSMICOS DROP COLUMN escala_version")
    conn.execute("ALTER TABLE TBL_CICLOS DROP COLUMN escala_version")
    conn.commit()
    assert "escala_version" not in _columnas(conn, "TBL_PRECURSORES_COSMICOS")
    assert "escala_version" not in _columnas(conn, "TBL_CICLOS")
    conn.close()
    conn = init_database(db)
    try:
        assert "escala_version" in _columnas(conn, "TBL_PRECURSORES_COSMICOS")
        assert "escala_version" in _columnas(conn, "TBL_CICLOS")
        vistas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'")}
        assert "v_precursores_motor" in vistas
        assert "v_ciclos_motor" in vistas
        # Re-ejecución idempotente (segunda init_database no falla).
        conn2 = init_database(db)
        conn2.close()
    finally:
        conn.close()


def test_init_no_pisa_una_vista_preexistente(tmp_path):
    # La versión del bundle (paso 6) lleva `en_vivo`; init_database usa
    # CREATE VIEW IF NOT EXISTS y NO debe pisarla.
    db = str(tmp_path / "bundle.db")
    conn = init_database(db)
    try:
        conn.execute("DROP VIEW v_precursores_motor")
        conn.execute(
            "CREATE VIEW v_precursores_motor AS "
            "SELECT 1 AS en_vivo")
        conn.commit()
        conn2 = init_database(db)
        sql = conn2.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE name='v_precursores_motor'").fetchone()[0]
        assert "en_vivo" in sql
        conn2.close()
    finally:
        conn.close()
