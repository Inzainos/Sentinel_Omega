"""Puebla tbl_cimatica_biblioteca — vísperas etiquetadas comparables.

La biblioteca de figuras del tablero estaba «no construida» desde su diseño
(2026-10-25): el único escritor era `ensure_biblioteca` corriendo en la
conexión READ-ONLY del dashboard, donde siempre falla en silencio. Este
script es el poblador real: deriva una fila por (clave_figura, event_class)
con `n_eventos` = eventos CUYA víspera produjo esa clave, usando la MISMA
extracción de features que el entrenamiento cimático — así vísperas
históricas y figura viva caen en las mismas claves y la comparación del
tablero (/api/cimatica/ahora → consultar) es real.

Sí también correrlo al final de cada entrenamiento (integrado en
entrenar_cimatica); este wrapper es para poblar AHORA sin reentrenar.

Costo medido: ~9 ms/evento × ~193k eventos ≈ 28 min (lote, log cada 10k).

Uso:
    .venv/bin/python deploy/construir_biblioteca_cimatica.py [db_path] [--max N]

ESCRIBE en la DB (la tabla es derivada: DELETE + INSERT completo, idempotente).
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

DB_DEFAULT = "sentinel_omega/data/SENTINEL_OMEGA_PRO.db"


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(raiz))

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    max_eventos = None
    if "--max" in sys.argv:
        max_eventos = int(sys.argv[sys.argv.index("--max") + 1])

    if args:
        db_path = Path(args[0])
    else:
        try:
            from sentinel_omega.infrastructure.database.ruta_db import (
                ruta_db_canonica,
            )
            db_path = Path(ruta_db_canonica())
        except Exception:
            db_path = raiz / DB_DEFAULT

    if not db_path.is_file():
        print(f"DB no encontrada: {db_path}")
        return 2

    from sentinel_omega.core.firmas.biblioteca_cimatica import (
        construir_biblioteca,
    )

    print(f"Poblando tbl_cimatica_biblioteca en {db_path} "
          f"(writable, reconstrucción completa)")
    t0 = time.time()
    conn = sqlite3.connect(str(db_path))
    try:
        stats = construir_biblioteca(conn, max_eventos=max_eventos)
    finally:
        conn.close()
    print(f"Listo en {(time.time() - t0)/60:.1f} min: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
