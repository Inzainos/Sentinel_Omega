"""FASE 2 — 7/D8: el API ya no retiene conexiones SQLite.

Diseño (ver reporte FASE 2): NO HAY caché de conexión. Cada consulta abre
su propia conexión ro y el cursor que la ejecuta ES DUEÑO de ella
(`_CursorRO`): al cerrar el cursor — close(), `with`, o el GC al perder
la última referencia — se cierra la conexión. Un middleware que cerrara
por request NO serviría: los endpoints `def` corren en hilos del
threadpool y el `finally` del middleware en el hilo del event loop, así
que cerraría el thread-local equivocado. La primera versión de este
parche hacía justo eso y se descartó tras la revisión.
"""
import gc
import os
import sqlite3
from pathlib import Path

import pytest


def _fds_de_db(db_path: Path) -> list:
    """FDs de ESTE proceso que apuntan a la DB (o a su -wal/-shm)."""
    objetivo = str(db_path)
    fds = []
    for fd in os.listdir("/proc/self/fd"):
        try:
            destino = os.readlink(f"/proc/self/fd/{fd}")
        except OSError:
            continue
        if destino.startswith(objetivo):
            fds.append(fd)
    return fds


@pytest.fixture(scope="module")
def api_mod(tmp_path_factory):
    """Importa api con SENTINEL_DB apuntando a una DB scratch mínima."""
    db_path = tmp_path_factory.mktemp("d8") / "api_d8.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE TBL_CICLOS (timestamp REAL)")
    conn.execute("CREATE TABLE tbl_eventos_sismicos_fuente (id INTEGER)")
    conn.execute("INSERT INTO TBL_CICLOS VALUES (1700000000.0)")
    conn.commit()
    conn.close()
    os.environ["SENTINEL_DB"] = str(db_path)
    import importlib
    import sentinel_omega.infrastructure.dashboard.api as api
    importlib.reload(api)
    yield api, db_path
    # Restaurar: sin SENTINEL_DB, el módulo vuelve a su DB por defecto, para
    # no contaminar a los tests que importen api después (p. ej.
    # test_precursor.py, que corre después en orden alfabético).
    del os.environ["SENTINEL_DB"]
    importlib.reload(api)


class TestCursorRO:
    def test_fetchone_y_close_cierran_la_conexion(self, api_mod):
        api, db_path = api_mod
        assert _fds_de_db(db_path) == []
        cur = api._repo._ro_execute("SELECT COUNT(*) AS n FROM TBL_CICLOS")
        assert _fds_de_db(db_path) != []  # durante la consulta hay FD
        assert cur.fetchone()[0] == 1
        cur.close()
        assert _fds_de_db(db_path) == []

    def test_perder_la_referencia_cierra_por_gc(self, api_mod):
        api, db_path = api_mod
        cur = api._repo._ro_execute("SELECT COUNT(*) AS n FROM TBL_CICLOS")
        assert _fds_de_db(db_path) != []
        del cur
        gc.collect()
        assert _fds_de_db(db_path) == []

    def test_context_manager_cierra(self, api_mod):
        api, db_path = api_mod
        with api._repo._ro_execute("SELECT COUNT(*) AS n FROM TBL_CICLOS") as cur:
            assert cur.fetchone()[0] == 1
        assert _fds_de_db(db_path) == []

    def test_un_fallo_de_sql_cierra_la_conexion(self, api_mod):
        api, db_path = api_mod
        with pytest.raises(sqlite3.OperationalError):
            api._repo._ro_execute("SELECT * FROM tabla_que_no_existe")
        assert _fds_de_db(db_path) == []

    def test_no_queda_conexion_cacheada(self, api_mod):
        api, _ = api_mod
        assert not hasattr(api._repo, "_tls")
        assert not hasattr(api._repo, "_conn_safe")


class TestHealthNoRetieneFD:
    def test_tres_requests_no_dejan_fd_de_db(self, api_mod):
        from fastapi.testclient import TestClient
        api, db_path = api_mod
        client = TestClient(api.app)
        for _ in range(3):
            r = client.get("/api/health")
            assert r.status_code == 200
            assert r.json()["ciclos"] == 1
        gc.collect()
        assert _fds_de_db(db_path) == []
