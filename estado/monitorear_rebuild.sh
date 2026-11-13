#!/bin/bash
# Monitor de rebuild: vigila que no se detenga y lo reinicia si es necesario
LOG="estado/rebuild_20261028_v2.log"
SCRIPT="deploy/rebuild_completo.py"

while true; do
    if ! pgrep -f "$SCRIPT" > /dev/null 2>&1; then
        echo "$(date -u +%FT%TZ) [MONITOR] Rebuild no está corriendo — verificando si terminó..."
        if grep -q "=== REBUILD COMPLETO — fin ===" "$LOG" 2>/dev/null; then
            echo "$(date -u +%FT%TZ) [MONITOR] Rebuild terminó correctamente."
            exit 0
        elif grep -q "FALLO" "$LOG" 2>/dev/null; then
            echo "$(date -u +%FT%TZ) [MONITOR] Rebuild terminó con FALLOS."
            exit 1
        else
            echo "$(date -u +%FT%TZ) [MONITOR] Rebuild se detuvo inesperadamente — reiniciando..."
            nohup .venv/bin/python "$SCRIPT" >> "$LOG" 2>&1 &
            echo "$(date -u +%FT%TZ) [MONITOR] Rebuild relanzado con PID $!"
        fi
    else
        echo "$(date -u +%FT%TZ) [MONITOR] Rebuild activo — esperando..."
    fi
    sleep 60
done
