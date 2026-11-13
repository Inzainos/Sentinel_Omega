#!/bin/bash
LOG="estado/rebuild_completo_final.log"
SCRIPT="deploy/rebuild_completo.py"

while true; do
    if ! pgrep -f "$SCRIPT" > /dev/null 2>&1; then
        if grep -q "=== REBUILD COMPLETO — fin ===" "$LOG" 2>/dev/null; then
            echo "$(date -u +%FT%TZ) [MONITOR] Rebuild COMPLETADO con éxito" >> "$LOG"
            exit 0
        elif grep -q "FALLO" "$LOG" 2>/dev/null; then
            echo "$(date -u +%FT%TZ) [MONITOR] Rebuild terminó con FALLOS" >> "$LOG"
            exit 1
        else
            echo "$(date -u +%FT%TZ) [MONITOR] Rebuild se detuvo inesperadamente — reiniciando..." >> "$LOG"
            nohup .venv/bin/python "$SCRIPT" --no-vacuum >> "$LOG" 2>&1 &
            echo "$(date -u +%FT%TZ) [MONITOR] Rebuild relanzado PID $!" >> "$LOG"
        fi
    fi
    sleep 30
done
